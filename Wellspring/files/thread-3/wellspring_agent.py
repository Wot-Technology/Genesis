"""
Wellspring Agent - Thread 3 Execution Loop

Claude API wrapper that:
1. Reads context from stored thoughts
2. Generates new thoughts via Claude
3. Parses and stores them back

Entry point for the WoT agent execution pipeline.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from anthropic import Anthropic
import core  # Local thread-3/core.py (blake3 CIDs, relative paths)

THREAD3_DIR = Path(__file__).parent.resolve()
WORKSPACE_DIR = THREAD3_DIR.parent  # files/
THREAD2_DIR = WORKSPACE_DIR / "thread-2"
TRACE_PATH = THREAD3_DIR / "traces.jsonl"

# Thread 2 RAG (lazy load)
_rag_instance = None

def get_rag():
    """Lazy-load RAG instance from Thread 2."""
    global _rag_instance
    if _rag_instance is None:
        try:
            sys.path.insert(0, str(THREAD2_DIR))
            from wellspring_embeddings import WellspringRAG
            _rag_instance = WellspringRAG(
                thought_db_path=core.DB_PATH,
                vec_db_path=THREAD3_DIR / "wellspring_vec.db"  # Same dir as daemon
            )
        except ImportError as e:
            print(f"Warning: Thread 2 RAG not available: {e}")
            _rag_instance = False  # Mark as unavailable
    return _rag_instance if _rag_instance else None


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

SYSTEM_PROMPT = """You are a WoT (Web of Thoughts) agent. You generate structured thoughts that connect to a knowledge graph.

## Response Format

When asked to generate thoughts, respond with one or more thought blocks in this format:

<thought>
type: [basic|insight|question|decision|trace]
content: [The thought content - can be multiple lines]
because: [Optional: comma-separated CIDs this thought builds on]
visibility: [Optional: null, local_forever, or pool:<cid>]
</thought>

## Guidelines

1. Each thought should be atomic - one idea per thought
2. Use 'because' to reference CIDs from context that influenced this thought
3. Types:
   - basic: Simple observations or notes
   - insight: Derived understanding from multiple sources
   - question: Something to explore or clarify
   - decision: A choice made with reasoning
   - trace: Development log entry (for tracking work)

4. When given context, reference specific CIDs in your because chain
5. Keep thoughts concise but complete

## Example

Given context about a bug discussion, you might respond:

<thought>
type: insight
content: The CID mismatch occurs because timestamp precision differs between systems. Milliseconds vs seconds creates different hashes.
because: cid:sha256:abc123, cid:sha256:def456
</thought>

<thought>
type: decision
content: Standardize on milliseconds (Unix epoch * 1000) for all timestamps across implementations.
because: cid:sha256:abc123
</thought>
"""


# ============================================================================
# CONTEXT ASSEMBLY
# ============================================================================

def format_thought_for_context(thought: core.Thought) -> str:
    """Format a single thought for LLM context."""
    lines = [
        f"[{thought.cid}]",
        f"Type: {thought.type}",
        f"Content: {thought.content if isinstance(thought.content, str) else json.dumps(thought.content)}",
    ]
    if thought.because:
        lines.append(f"Because: {', '.join(thought.because)}")
    if thought.source:
        lines.append(f"Source: {thought.source}")
    lines.append(f"Created: {datetime.fromtimestamp(thought.created_at/1000).isoformat()}")
    return '\n'.join(lines)


def assemble_context_rag(
    query: str,
    limit: int = 10,
    pool_cid: Optional[str] = None,
    include_cids: Optional[List[str]] = None
) -> Tuple[str, List[str]]:
    """
    Assemble context using Thread 2 RAG retrieval.

    Args:
        query: The user's query to find relevant thoughts
        limit: Max thoughts to retrieve
        pool_cid: Optional pool scope
        include_cids: Specific CIDs to always include

    Returns:
        (formatted_context, list_of_cids_used)
    """
    rag = get_rag()
    context_parts = []
    used_cids = []

    # First, include any specifically requested CIDs
    if include_cids:
        for cid in include_cids:
            thought = core.get_thought(cid)
            if thought and cid not in used_cids:
                context_parts.append(format_thought_for_context(thought))
                used_cids.append(cid)

    # Use RAG retrieval if available
    if rag:
        results = rag.retrieve(query, top_k=limit, pool_cid=pool_cid, include_thoughts=True)
        for r in results:
            if r['cid'] in used_cids:
                continue
            if 'thought' in r and r['thought']:
                context_parts.append(
                    f"[Relevance: {r['similarity']:.2f}]\n" +
                    format_thought_for_context(r['thought'])
                )
                used_cids.append(r['cid'])
    else:
        # Fallback to recent thoughts if RAG unavailable
        recent = core.query_thoughts(limit=limit)
        for thought in recent:
            if thought.cid in used_cids:
                continue
            context_parts.append(format_thought_for_context(thought))
            used_cids.append(thought.cid)

    if not context_parts:
        return "(No prior thoughts in context)", []

    return "\n\n---\n\n".join(context_parts), used_cids


def assemble_context(
    limit: int = 20,
    thought_types: Optional[List[str]] = None,
    include_cids: Optional[List[str]] = None
) -> str:
    """
    Assemble context from stored thoughts for LLM consumption (legacy, non-RAG).

    Args:
        limit: Max thoughts to include
        thought_types: Filter by types
        include_cids: Specific CIDs to include (always included first)

    Returns:
        Formatted context string
    """
    context_parts = []
    included_cids = set()

    # First, include any specifically requested CIDs
    if include_cids:
        for cid in include_cids:
            thought = core.get_thought(cid)
            if thought and cid not in included_cids:
                context_parts.append(format_thought_for_context(thought))
                included_cids.add(cid)

    # Then add recent thoughts up to limit
    remaining = limit - len(included_cids)
    if remaining > 0:
        recent = core.query_thoughts(limit=remaining * 2)  # fetch extra to filter
        for thought in recent:
            if thought.cid in included_cids:
                continue
            if thought_types and thought.type not in thought_types:
                continue
            context_parts.append(format_thought_for_context(thought))
            included_cids.add(thought.cid)
            if len(context_parts) >= limit:
                break

    if not context_parts:
        return "(No prior thoughts in context)"

    return "\n\n---\n\n".join(context_parts)


# ============================================================================
# THOUGHT PARSING
# ============================================================================

THOUGHT_PATTERN = re.compile(
    r'<thought>(.*?)</thought>',
    re.DOTALL | re.IGNORECASE
)

def parse_thought_block(block: str) -> Optional[Dict[str, Any]]:
    """Parse a single <thought>...</thought> block into fields."""
    result = {
        'type': 'basic',
        'content': '',
        'because': [],
        'visibility': None
    }

    lines = block.strip().split('\n')
    content_lines = []
    in_content = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for field prefixes
        if line.lower().startswith('type:'):
            result['type'] = line.split(':', 1)[1].strip()
            in_content = False
        elif line.lower().startswith('content:'):
            content_lines.append(line.split(':', 1)[1].strip())
            in_content = True
        elif line.lower().startswith('because:'):
            # Parse comma-separated CIDs
            cids = line.split(':', 1)[1].strip()
            result['because'] = [c.strip() for c in cids.split(',') if c.strip()]
            in_content = False
        elif line.lower().startswith('visibility:'):
            vis = line.split(':', 1)[1].strip()
            result['visibility'] = None if vis.lower() == 'null' else vis
            in_content = False
        elif in_content:
            # Continuation of content
            content_lines.append(line)

    result['content'] = '\n'.join(content_lines).strip()

    if not result['content']:
        return None

    return result


def parse_llm_response(response: str) -> List[Dict[str, Any]]:
    """Extract all thought blocks from LLM response."""
    thoughts = []
    matches = THOUGHT_PATTERN.findall(response)

    for block in matches:
        parsed = parse_thought_block(block)
        if parsed:
            thoughts.append(parsed)

    return thoughts


# ============================================================================
# AGENT EXECUTION
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for the agent."""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 2048
    identity_path: Optional[Path] = None
    auto_store: bool = True
    source_prefix: str = "agent-model"


class WellspringAgent:
    """
    The execution loop agent.

    Reads context → Calls Claude → Parses thoughts → Stores them.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.client = Anthropic()  # Uses ANTHROPIC_API_KEY env var

        # Load or create identity
        self.identity = self._load_or_create_identity()

    def _load_or_create_identity(self) -> core.Identity:
        """Load existing identity or create new one."""
        identity_path = self.config.identity_path or (WORKSPACE_DIR / "agent-identity.json")

        if identity_path.exists():
            return core.load_identity(identity_path)

        # Create new agent identity
        identity = core.create_identity(f"wellspring-agent-{self.config.model}")
        core.save_identity(identity, identity_path)

        # Also create and store the identity thought
        identity_thought = core.create_thought(
            content={
                "type": "identity",
                "name": identity.name,
                "pubkey": identity.pubkey,
                "model": self.config.model
            },
            thought_type="identity",
            identity=identity,
            source=f"{self.config.source_prefix}/{self.config.model}"
        )
        core.store_thought(identity_thought)

        print(f"Created new agent identity: {identity.cid}")
        return identity

    def generate(
        self,
        user_input: str,
        context_limit: int = 10,
        pool_cid: Optional[str] = None,
        include_cids: Optional[List[str]] = None,
        additional_context: Optional[str] = None,
        use_rag: bool = True
    ) -> List[core.Thought]:
        """
        Execute the generation loop with RAG-based context retrieval.

        Args:
            user_input: The user's message/query
            context_limit: Max context thoughts
            pool_cid: Pool to scope retrieval
            include_cids: Specific CIDs to include in context
            additional_context: Extra context to inject
            use_rag: Whether to use Thread 2 RAG (default True)

        Returns:
            List of generated and stored Thought objects
        """
        # Assemble context using RAG when available
        if use_rag:
            context, context_cids = assemble_context_rag(
                query=user_input,
                limit=context_limit,
                pool_cid=pool_cid,
                include_cids=include_cids
            )
        else:
            context = assemble_context(
                limit=context_limit,
                include_cids=include_cids
            )
            context_cids = []

        if additional_context:
            context = f"{additional_context}\n\n---\n\n{context}"

        # Build messages
        messages = [
            {
                "role": "user",
                "content": f"""## Prior Thoughts (Context)

{context}

---

## Your Task

{user_input}

Generate thoughts in response. Use <thought>...</thought> format as specified.
Reference the CIDs from context in your 'because' chain when relevant."""
            }
        ]

        # Call Claude
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        response_text = response.content[0].text

        # Parse thoughts from response
        parsed = parse_llm_response(response_text)

        # Create and optionally store Thought objects
        thoughts = []
        for p in parsed:
            # Merge parsed because with context CIDs (if agent didn't reference)
            because = p['because'] if p['because'] else []
            if not because and context_cids:
                # Auto-attach top context CIDs if agent didn't specify
                because = context_cids[:3]

            thought = core.create_thought(
                content=p['content'],
                thought_type=p['type'],
                identity=self.identity,
                because=because if because else None,
                visibility=p['visibility'],
                source=f"{self.config.source_prefix}/{self.config.model}"
            )

            if self.config.auto_store:
                core.store_thought(thought)
                # Also index in RAG if available
                rag = get_rag()
                if rag:
                    rag.pipeline.embed_thought(thought, pool_cid)

            thoughts.append(thought)

        return thoughts

    def log_trace(
        self,
        category: str,
        title: str,
        body: str,
        because: Optional[List[str]] = None
    ) -> core.Thought:
        """
        Log a development trace thought.

        Args:
            category: decision|question|finding|artifact|bug|reference
            title: Short description
            body: Details
            because: Related CIDs
        """
        content = {
            "category": category,
            "title": title,
            "body": body,
            "thread": 3
        }

        thought = core.create_thought(
            content=content,
            thought_type="trace",
            identity=self.identity,
            because=because,
            source=f"{self.config.source_prefix}/thread-3"
        )

        core.store_thought(thought)

        # Also append to thread trace file
        with open(TRACE_PATH, 'a') as f:
            f.write(json.dumps(asdict(thought)) + '\n')

        return thought


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI interface for the agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Wellspring Agent - Thread 3")
    parser.add_argument('--input', '-i', type=str, help="User input (or read from stdin)")
    parser.add_argument('--context', '-c', type=int, default=10, help="Context limit")
    parser.add_argument('--cids', type=str, help="Comma-separated CIDs to include")
    parser.add_argument('--model', type=str, default="claude-sonnet-4-20250514", help="Model to use")
    parser.add_argument('--no-store', action='store_true', help="Don't auto-store thoughts")
    parser.add_argument('--trace', action='store_true', help="Log a trace thought instead")

    args = parser.parse_args()

    # Get input
    if args.input:
        user_input = args.input
    else:
        print("Enter your input (Ctrl+D when done):")
        user_input = sys.stdin.read().strip()

    if not user_input:
        print("No input provided")
        return

    # Create agent
    config = AgentConfig(
        model=args.model,
        auto_store=not args.no_store
    )
    agent = WellspringAgent(config)

    # Include specific CIDs if provided
    include_cids = None
    if args.cids:
        include_cids = [c.strip() for c in args.cids.split(',')]

    # Execute
    print(f"\n--- Generating thoughts with {args.model} ---\n")
    thoughts = agent.generate(
        user_input=user_input,
        context_limit=args.context,
        include_cids=include_cids
    )

    # Output
    for t in thoughts:
        print(f"[{t.cid}]")
        print(f"  Type: {t.type}")
        print(f"  Content: {t.content[:100]}..." if len(str(t.content)) > 100 else f"  Content: {t.content}")
        if t.because:
            print(f"  Because: {t.because}")
        print()

    print(f"Generated {len(thoughts)} thoughts")


if __name__ == "__main__":
    main()
