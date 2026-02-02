# Thread 3: Pool Control + Context Surfacing

The execution loop — query pool, assemble context, execute LLM, parse thoughts back.

## Files

| File | Purpose |
|------|---------|
| `core.py` | Local copy of wellspring_core with fixed paths |
| `wellspring_agent.py` | Main agent module - Claude API wrapper |
| `test_agent.py` | Test script for dry-run and full loop |
| `traces.jsonl` | Development trace thoughts for this thread |

## Quick Start

```bash
# Dry run (no API key needed)
cd thread-3
python test_agent.py --dry-run

# Full loop with Claude
export ANTHROPIC_API_KEY=sk-ant-...
python test_agent.py
```

## Usage

### Basic Generation

```python
from wellspring_agent import WellspringAgent, AgentConfig

# Create agent with defaults
agent = WellspringAgent()

# Generate thoughts from user input
thoughts = agent.generate(
    user_input="What are the key design decisions for CID computation?",
    context_limit=20  # Include up to 20 prior thoughts as context
)

for t in thoughts:
    print(f"[{t.type}] {t.content}")
```

### Custom Configuration

```python
config = AgentConfig(
    model="claude-sonnet-4-20250514",  # or claude-3-haiku-20240307
    max_tokens=2048,
    auto_store=True,  # Automatically store generated thoughts
    source_prefix="my-agent"  # Source attribution
)
agent = WellspringAgent(config)
```

### Including Specific Context

```python
# Include specific CIDs in context (e.g., from RAG retrieval)
thoughts = agent.generate(
    user_input="Summarize these related findings",
    include_cids=[
        "cid:sha256:abc123...",
        "cid:sha256:def456..."
    ]
)
```

### Logging Trace Thoughts

```python
# Log development progress as thoughts
agent.log_trace(
    category="decision",
    title="Use Claude Sonnet for initial testing",
    body="Lower cost, faster iteration. Will switch to Opus for production.",
    because=["cid:sha256:related_thought..."]
)
```

## LLM Response Format

The agent expects Claude to generate thoughts in this format:

```
<thought>
type: [basic|insight|question|decision|trace]
content: The thought content here.
Can span multiple lines.
because: cid:sha256:abc123, cid:sha256:def456
visibility: null
</thought>
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Input                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Context Assembly                            │
│  - Query recent thoughts from DB                        │
│  - Include specific CIDs (from RAG)                     │
│  - Format for LLM consumption                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Claude API Call                             │
│  - System prompt defines thought format                 │
│  - Context + user input as message                      │
│  - Returns structured <thought> blocks                  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Response Parsing                            │
│  - Extract <thought>...</thought> blocks                │
│  - Parse type, content, because, visibility             │
│  - Create Thought objects with signatures               │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Storage                                     │
│  - Store to SQLite (for querying)                       │
│  - Append to JSONL (for export)                         │
│  - Return list of Thought objects                       │
└─────────────────────────────────────────────────────────┘
```

## Next Steps (from workstreams.md)

1. **Thread 2 Integration**: Replace hardcoded context with RAG-based retrieval
2. **Token Budget**: Manage context size based on model limits
3. **OpenWebUI Wrapper**: `/chat/completions` compatible endpoint
4. **Pool Control Thoughts**: Meta-thoughts that configure agent behavior
5. **Feedback Loop**: Human accepts/rejects AI-generated thoughts

## Trace Format

Development traces use this content structure:

```json
{
  "category": "decision|question|finding|artifact|bug|reference",
  "title": "Short description",
  "body": "Details...",
  "thread": 3
}
```
