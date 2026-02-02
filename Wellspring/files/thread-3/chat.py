"""
WoT Chat Interface - Thread 3 Execution Loop

Proxies between user and Claude API:
1. Records user messages as thoughts
2. Queries RAG for relevant context
3. Injects context into prompt
4. Calls Claude API
5. Parses and stores response thoughts
6. Returns response with thought chain
"""

# Suppress tokenizers parallelism warning - must be set before any imports
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import sys
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Import both - use AnthropicFoundry for Azure-hosted Claude
try:
    from anthropic import Anthropic, AnthropicFoundry
except ImportError:
    from anthropic import Anthropic
    AnthropicFoundry = None

# OpenAI for Azure OpenAI endpoints
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import core
import pool as pool_mgmt

# ============================================================================
# ANSI COLORS
# ============================================================================

class C:
    """ANSI color codes for CLI output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    # Colors
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    # Bright variants
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    # Semantic aliases
    CID = CYAN
    TYPE = MAGENTA
    DEBUG = DIM
    SYSTEM = YELLOW
    USER = GREEN
    ASSISTANT = BRIGHT_CYAN
    ERROR = RED


# RAG integration
THREAD2_DIR = Path(__file__).parent.parent / "thread-2"
sys.path.insert(0, str(THREAD2_DIR))

_rag = None

def get_rag():
    global _rag
    if _rag is None:
        try:
            from wellspring_embeddings import WellspringRAG
            _rag = WellspringRAG(
                thought_db_path=core.DB_PATH,
                vec_db_path=Path(__file__).parent / "wellspring_vec.db"
            )
        except ImportError:
            _rag = False
    return _rag if _rag else None


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are a WoT (Web of Thoughts) assistant. You have access to a thought graph - a network of signed, content-addressed thoughts connected by "because" chains that show reasoning provenance.

## Context Format

You'll receive relevant thoughts from the graph as context. Each thought has:
- **CID**: Content identifier (hash of content)
- **Type**: basic, insight, question, decision, trace, message, etc.
- **Content**: The thought content
- **Because**: CIDs this thought builds on (reasoning chain)
- **Relevance**: How relevant to the current query (0-1)

## Your Response

Respond naturally to the user. When your response contains distinct ideas, insights, or decisions, you may optionally structure them as thoughts:

<thought>
type: insight
content: Your insight here
because: cid:blake3:abc123...
</thought>

Guidelines:
- Reference CIDs from context in your `because` when building on prior thoughts
- Use thought blocks for ideas worth remembering/referencing later
- Keep regular conversational responses natural - not everything needs to be a thought
- Types: basic (simple note), insight (derived understanding), question (to explore), decision (choice made), message (conversational)

## Example

User asks about CID computation, and context includes a thought about BLAKE3:

"Based on the earlier decision to use BLAKE3, CIDs are computed by hashing the canonical JSON of the thought content.

<thought>
type: insight
content: CID computation uses BLAKE3 over canonical JSON, making thoughts content-addressed and self-verifying.
because: cid:blake3:abc123def456...
</thought>"
"""


# ============================================================================
# THOUGHT PARSING
# ============================================================================

THOUGHT_PATTERN = re.compile(r'<thought>(.*?)</thought>', re.DOTALL | re.IGNORECASE)

def parse_thoughts(response: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parse response for thought blocks.
    Returns: (clean_response, [parsed_thoughts])
    """
    thoughts = []

    for match in THOUGHT_PATTERN.finditer(response):
        block = match.group(1)
        parsed = parse_thought_block(block)
        if parsed:
            thoughts.append(parsed)

    # Clean response (remove thought tags for display)
    clean = THOUGHT_PATTERN.sub('', response).strip()
    # Clean up extra whitespace
    clean = re.sub(r'\n{3,}', '\n\n', clean)

    return clean, thoughts


def parse_thought_block(block: str) -> Optional[Dict[str, Any]]:
    """Parse a single thought block."""
    result = {
        'type': 'insight',
        'content': '',
        'because': []
    }

    lines = block.strip().split('\n')
    content_lines = []
    in_content = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith('type:'):
            result['type'] = line.split(':', 1)[1].strip()
            in_content = False
        elif line.lower().startswith('content:'):
            content_lines.append(line.split(':', 1)[1].strip())
            in_content = True
        elif line.lower().startswith('because:'):
            cids = line.split(':', 1)[1].strip()
            result['because'] = [c.strip() for c in cids.split(',') if c.strip()]
            in_content = False
        elif in_content:
            content_lines.append(line)

    result['content'] = '\n'.join(content_lines).strip()
    return result if result['content'] else None


# ============================================================================
# CONTEXT ASSEMBLY
# ============================================================================

def format_thought_context(thought: core.Thought, relevance: float = 0.0) -> str:
    """Format a thought for injection into prompt."""
    content = thought.content
    if isinstance(content, dict):
        content = json.dumps(content, indent=2)

    # Handle because chain - may contain dicts or strings
    because_str = None
    if thought.because:
        because_items = [str(b) if not isinstance(b, str) else b for b in thought.because]
        because_str = f"Because: {', '.join(because_items)}"

    lines = [
        f"[{thought.cid}]",
        f"Type: {thought.type}",
        f"Relevance: {relevance:.2f}" if relevance > 0 else None,
        f"Content: {content}",
        because_str,
    ]
    return '\n'.join(l for l in lines if l)


def get_context(query: str, pool_cid: Optional[str] = None, limit: int = 10) -> Tuple[str, List[str]]:
    """
    Get relevant context for a query.
    Returns: (formatted_context, list_of_cids_used)
    """
    rag = get_rag()
    if not rag:
        return "(No context available - RAG not initialized)", []

    # Get pool waterline
    pool = pool_mgmt.get_pool(pool_cid) if pool_cid else None
    waterline = pool.rules.waterline if pool else 0.3

    # Query RAG
    results = rag.retrieve(query, top_k=limit * 2, pool_cid=pool_cid, include_thoughts=True)

    # Filter by waterline
    filtered = [r for r in results if r.get('relevance', 0) >= waterline][:limit]

    if not filtered:
        return "(No relevant thoughts found above waterline)", []

    # Format context
    context_parts = []
    cids_used = []

    for r in filtered:
        if 'thought' in r and r['thought']:
            t = r['thought']
            context_parts.append(format_thought_context(t, r.get('relevance', 0)))
            cids_used.append(t.cid)

    return '\n\n---\n\n'.join(context_parts), cids_used


# ============================================================================
# CHAT SESSION
# ============================================================================

@dataclass
class ChatConfig:
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    context_limit: int = 10
    pool_cid: Optional[str] = None
    auto_store: bool = True
    # Provider: "anthropic" (default), "openai", "azure-anthropic", "azure-openai"
    provider: str = "anthropic"
    # Azure/OpenAI settings
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    deployment_name: Optional[str] = None  # e.g. "gpt-5.2-chat" or "claude-opus-4-5"


class WoTChat:
    """Chat session with WoT context injection."""

    def __init__(self, identity: core.Identity, config: Optional[ChatConfig] = None):
        self.identity = identity
        self.config = config or ChatConfig()
        self.conversation: List[Dict[str, str]] = []
        self.thought_chain: List[str] = []  # CIDs of thoughts in this session
        self._provider_type = self.config.provider  # "anthropic", "openai", "azure-openai", "azure-anthropic"

        # Initialize client based on provider
        if self.config.provider in ("openai", "azure-openai"):
            if OpenAI is None:
                raise ImportError("openai package not installed - pip install openai")
            self.client = OpenAI(
                base_url=self.config.api_endpoint,
                api_key=self.config.api_key
            )
            self._model_name = self.config.deployment_name or self.config.model
        elif self.config.provider == "azure-anthropic":
            if AnthropicFoundry is None:
                raise ImportError("AnthropicFoundry not available - update anthropic package")
            self.client = AnthropicFoundry(
                api_key=self.config.api_key,
                base_url=self.config.api_endpoint
            )
            self._model_name = self.config.deployment_name or self.config.model
        else:
            # Default: direct Anthropic API
            self.client = Anthropic()  # Uses ANTHROPIC_API_KEY env var
            self._model_name = self.config.model

        # Get or create default pool
        self.pool = pool_mgmt.get_default_pool(identity)
        if not self.config.pool_cid:
            self.config.pool_cid = self.pool.cid

    def store_message(
        self,
        content: str,
        role: str,
        because: Optional[List[str]] = None
    ) -> core.Thought:
        """Store a message as a thought."""
        thought = core.create_thought(
            content={
                "role": role,
                "text": content,
                "session": self.thought_chain[0] if self.thought_chain else None
            },
            thought_type="message",
            identity=self.identity,
            because=because or [],
            visibility=f"pool:{self.config.pool_cid}",
            source=f"chat/{role}"
        )

        if self.config.auto_store:
            core.store_thought(thought)
            self.thought_chain.append(thought.cid)

            # Index in RAG
            rag = get_rag()
            if rag:
                rag.pipeline.embed_thought(thought, self.config.pool_cid)

        return thought

    def store_parsed_thoughts(
        self,
        thoughts: List[Dict[str, Any]],
        response_cid: str
    ) -> List[core.Thought]:
        """Store parsed thoughts from AI response."""
        stored = []

        for t in thoughts:
            # Merge because with response CID
            because = t.get('because', [])
            if response_cid not in because:
                because = [response_cid] + because

            thought = core.create_thought(
                content=t['content'],
                thought_type=t['type'],
                identity=self.identity,
                because=because,
                visibility=f"pool:{self.config.pool_cid}",
                source=f"chat/ai-{self.config.model}"
            )

            if self.config.auto_store:
                core.store_thought(thought)
                self.thought_chain.append(thought.cid)

                rag = get_rag()
                if rag:
                    rag.pipeline.embed_thought(thought, self.config.pool_cid)

            stored.append(thought)

        return stored

    def chat(self, user_input: str, stream: bool = False) -> Dict[str, Any]:
        """
        Process a chat message.

        Args:
            user_input: The user's message
            stream: If True, yield tokens as they arrive (prints to stdout)

        Returns: {
            "response": str,  # Clean response text
            "thoughts": [Thought],  # Parsed and stored thoughts
            "context_cids": [str],  # CIDs used as context
            "user_thought": Thought,  # User message thought
            "response_thought": Thought,  # AI response thought
        }
        """
        # Get relevant context
        context, context_cids = get_context(
            user_input,
            pool_cid=self.config.pool_cid,
            limit=self.config.context_limit
        )

        # Store user message (because = context + previous in chain)
        because = context_cids.copy()
        if self.thought_chain:
            because.append(self.thought_chain[-1])

        user_thought = self.store_message(user_input, "user", because)

        # Build messages
        self.conversation.append({"role": "user", "content": user_input})

        # Inject context into first user message or as system context
        messages_with_context = []
        for i, msg in enumerate(self.conversation):
            if i == len(self.conversation) - 1 and msg["role"] == "user":
                # Add context to latest user message
                augmented = f"""## Relevant Thoughts from Graph

{context}

---

## User Message

{msg["content"]}"""
                messages_with_context.append({"role": "user", "content": augmented})
            else:
                messages_with_context.append(msg)

        # Call LLM - different API formats for Anthropic vs OpenAI
        if self._provider_type in ("openai", "azure-openai"):
            response_text = self._call_openai(messages_with_context, stream)
        else:
            response_text = self._call_anthropic(messages_with_context, stream)

        # Parse thoughts from response
        clean_response, parsed_thoughts = parse_thoughts(response_text)

        # Store AI response
        response_thought = self.store_message(
            response_text,
            "assistant",
            [user_thought.cid] + context_cids
        )

        # Store any parsed thoughts
        stored_thoughts = self.store_parsed_thoughts(parsed_thoughts, response_thought.cid)

        # Add to conversation history
        self.conversation.append({"role": "assistant", "content": clean_response})

        return {
            "response": clean_response,
            "thoughts": stored_thoughts,
            "context_cids": context_cids,
            "user_thought": user_thought,
            "response_thought": response_thought,
        }

    def _call_openai(self, messages: List[Dict], stream: bool = False) -> str:
        """Call OpenAI/Azure-OpenAI API."""
        openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        openai_messages.extend(messages)

        if stream:
            response_chunks = []
            stream_resp = self.client.chat.completions.create(
                model=self._model_name,
                max_completion_tokens=self.config.max_tokens,
                messages=openai_messages,
                stream=True
            )
            for chunk in stream_resp:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    print(text, end="", flush=True)
                    response_chunks.append(text)
            print()  # Newline after stream
            return "".join(response_chunks)
        else:
            response = self.client.chat.completions.create(
                model=self._model_name,
                max_completion_tokens=self.config.max_tokens,
                messages=openai_messages
            )
            return response.choices[0].message.content

    def _call_anthropic(self, messages: List[Dict], stream: bool = False) -> str:
        """Call Anthropic API."""
        if stream:
            response_chunks = []
            with self.client.messages.stream(
                model=self._model_name,
                max_tokens=self.config.max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages
            ) as stream_resp:
                for text in stream_resp.text_stream:
                    print(text, end="", flush=True)
                    response_chunks.append(text)
            print()  # Newline after stream
            return "".join(response_chunks)
        else:
            response = self.client.messages.create(
                model=self._model_name,
                max_tokens=self.config.max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages
            )
            return response.content[0].text

    def get_session_chain(self) -> List[core.Thought]:
        """Get all thoughts in this session."""
        return [core.get_thought(cid) for cid in self.thought_chain if core.get_thought(cid)]


# ============================================================================
# CLI
# ============================================================================

def run_chat_repl(identity: core.Identity, config: Optional[ChatConfig] = None):
    """Run interactive chat REPL."""
    chat = WoTChat(identity, config)
    debug_mode = False  # Toggle with /debug

    print(f"{C.SYSTEM}{'=' * 60}")
    print(f"{C.BOLD}WoT Chat{C.RESET}")
    print(f"{C.SYSTEM}{'=' * 60}{C.RESET}")
    print(f"{C.DIM}Model:{C.RESET} {chat._model_name}")
    if chat.config.api_endpoint:
        print(f"{C.DIM}Endpoint:{C.RESET} {chat.config.api_endpoint}")
    print(f"{C.DIM}Pool:{C.RESET} {C.CID}{chat.config.pool_cid[:40]}...{C.RESET}")
    print(f"{C.DIM}Waterline:{C.RESET} {chat.pool.rules.waterline}")
    print()
    print(f"{C.DIM}Commands: /quit /chain /context /waterline /pool /pools /debug /reset{C.RESET}")
    print(f"{C.SYSTEM}{'=' * 60}{C.RESET}")
    print()

    while True:
        try:
            user_input = input(f"{C.USER}{C.BOLD}You:{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.SYSTEM}Goodbye!{C.RESET}")
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith('/'):
            cmd = user_input.split()[0].lower()
            args = user_input[len(cmd):].strip()

            if cmd == '/quit':
                print(f"{C.SYSTEM}Goodbye!{C.RESET}")
                break
            elif cmd == '/chain':
                print(f"\n{C.SYSTEM}Session chain ({len(chat.thought_chain)} thoughts):{C.RESET}")
                for cid in chat.thought_chain[-10:]:
                    t = core.get_thought(cid)
                    if t:
                        content = t.content.get('text', t.content) if isinstance(t.content, dict) else t.content
                        print(f"  {C.TYPE}[{t.type}]{C.RESET} {str(content)[:50]}...")
                print()
                continue
            elif cmd == '/context':
                query = args or "recent thoughts"
                ctx, cids = get_context(query, chat.config.pool_cid)
                print(f"\n{C.SYSTEM}Context for '{query}' ({len(cids)} thoughts):{C.RESET}")
                print(f"{C.DIM}{ctx[:500]}{'...' if len(ctx) > 500 else ''}{C.RESET}")
                print()
                continue
            elif cmd == '/waterline':
                try:
                    wl = float(args)
                    pool_mgmt.update_waterline(chat.config.pool_cid, wl, identity)
                    chat.pool = pool_mgmt.get_pool(chat.config.pool_cid)
                    print(f"{C.SYSTEM}Waterline updated to {wl}{C.RESET}")
                except ValueError:
                    print(f"{C.SYSTEM}Current waterline: {chat.pool.rules.waterline}{C.RESET}")
                continue
            elif cmd == '/debug':
                debug_mode = not debug_mode
                print(f"{C.SYSTEM}Debug mode: {C.BOLD}{'ON' if debug_mode else 'OFF'}{C.RESET}")
                continue
            elif cmd == '/reset':
                chat.conversation = []
                print(f"{C.SYSTEM}Conversation history cleared (pool unchanged){C.RESET}")
                continue
            elif cmd == '/pools':
                pools = pool_mgmt.list_pools()
                print(f"\n{C.SYSTEM}Available pools ({len(pools)}):{C.RESET}")
                for p in pools:
                    marker = f" {C.BOLD}*{C.RESET}" if p.cid == chat.config.pool_cid else ""
                    name = p.name if hasattr(p, 'name') else p.cid[:20]
                    print(f"  {C.CYAN}{name}{C.RESET}{marker}")
                print()
                continue
            elif cmd == '/pool':
                if not args:
                    print(f"{C.SYSTEM}Current pool: {C.CID}{chat.config.pool_cid[:40]}...{C.RESET}")
                    continue
                # Find pool by name or CID prefix
                pools = pool_mgmt.list_pools()
                match = None
                for p in pools:
                    pname = p.name if hasattr(p, 'name') else ""
                    if args.lower() in pname.lower() or p.cid.startswith(args):
                        match = p
                        break
                if match:
                    chat.config.pool_cid = match.cid
                    chat.pool = match
                    print(f"{C.SYSTEM}Switched to pool: {C.BOLD}{match.name if hasattr(match, 'name') else match.cid[:40]}{C.RESET}")
                    print(f"{C.DIM}  (conversation history retained - use /reset to clear){C.RESET}")
                else:
                    print(f"{C.ERROR}Pool not found: {args}{C.RESET}")
                continue
            else:
                print(f"{C.ERROR}Unknown command: {cmd}{C.RESET}")
                continue

        # Chat
        try:
            # Get context for this specific message
            context, context_cids = get_context(
                user_input,
                pool_cid=chat.config.pool_cid,
                limit=chat.config.context_limit
            )

            if debug_mode:
                print(f"\n{C.DEBUG}[DEBUG] Retrieved {len(context_cids)} thoughts:{C.RESET}")
                for cid in context_cids:
                    t = core.get_thought(cid)
                    if t:
                        preview = str(t.content)[:60].replace('\n', ' ')
                        print(f"{C.DEBUG}  {C.CID}{cid[:20]}...{C.RESET} {C.TYPE}[{t.type}]{C.RESET} {C.DIM}{preview}{C.RESET}")
                print()

            # Stream response
            print(f"\n{C.ASSISTANT}{C.BOLD}Assistant:{C.RESET} ", end="", flush=True)
            result = chat.chat(user_input, stream=True)

            if result['thoughts']:
                print(f"\n{C.DIM}[Stored {len(result['thoughts'])} thoughts]{C.RESET}")

            print()
        except Exception as e:
            print(f"\n{C.ERROR}Error: {e}{C.RESET}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="WoT Chat")
    parser.add_argument('--model', '-m', default="claude-sonnet-4-20250514",
                        help="Claude model to use")
    parser.add_argument('--context', '-c', type=int, default=10,
                        help="Number of context thoughts")
    parser.add_argument('--no-store', action='store_true',
                        help="Don't store thoughts")
    # Provider settings
    parser.add_argument('--provider', '-p',
                        choices=['anthropic', 'openai', 'azure-openai', 'azure-anthropic'],
                        default='anthropic',
                        help="LLM provider (default: anthropic)")
    parser.add_argument('--endpoint',
                        help="API endpoint URL (for Azure/custom)")
    parser.add_argument('--api-key',
                        help="API key (or set WOT_API_KEY env var)")
    parser.add_argument('--deployment',
                        help="Deployment/model name for Azure")

    args = parser.parse_args()

    # Load identity
    identity_path = Path(__file__).parent / "daemon-identity.json"
    if identity_path.exists():
        identity = core.load_identity(identity_path)
    else:
        identity = core.create_identity("chat-user")
        core.save_identity(identity, identity_path)

    # Resolve settings from args or env
    api_endpoint = args.endpoint or os.environ.get('WOT_API_ENDPOINT')
    api_key = args.api_key or os.environ.get('WOT_API_KEY')
    deployment = args.deployment or os.environ.get('WOT_DEPLOYMENT')

    config = ChatConfig(
        model=args.model,
        context_limit=args.context,
        auto_store=not args.no_store,
        provider=args.provider,
        api_endpoint=api_endpoint,
        api_key=api_key,
        deployment_name=deployment
    )

    run_chat_repl(identity, config)


if __name__ == "__main__":
    main()
