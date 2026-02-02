# Wellspring Eternal

**Web of Thoughts (WoT)** — A traversal-based persistent memory system for AI agents.

## Quick Start

```bash
cd files/thread-3

# Start chat with Azure OpenAI
python daemon.py --chat --provider azure-openai

# Or set env vars first
export WOT_API_ENDPOINT="https://your-endpoint.openai.azure.com/openai/v1"
export WOT_API_KEY="your-key"
export WOT_DEPLOYMENT="gpt-5.2-chat"
python daemon.py --chat --provider azure-openai
```

## Core Concepts

- **Thought**: Content-addressed, signed unit of information (CID = blake3 hash)
- **Pool**: Trust boundary + context scope (thoughts belong to pools)
- **Because Chain**: Provenance links showing reasoning derivation
- **Waterline**: Minimum relevance threshold for thought surfacing

## Directory Structure

```
Wellspring Eternal/
├── README.md           # This file
├── CLAUDE.md           # Agent instructions
├── inject.py           # CLI to inject thoughts (shared tool)
├── files/
│   ├── thread-1/       # Core primitives + schemas
│   ├── thread-2/       # RAG/vector indexing
│   └── thread-3/       # Execution loop + daemon
└── external refs/      # Reference implementations
```

## Agent Tools

### inject.py — Add thoughts from any agent

```bash
# Direct text
python inject.py --text "My insight" --type insight --pool wot

# Pipe in
echo '{"trace": "data"}' | python inject.py --type trace --pool wot

# With provenance
python inject.py --text "Builds on X" --because cid:blake3:abc123...

# Quiet mode (just CID)
CID=$(python inject.py --text "something" -q)
```

### daemon.py — Main daemon

```bash
# Chat interface
python files/thread-3/daemon.py --chat --provider azure-openai

# Re-index thoughts into pool
python files/thread-3/daemon.py --reindex wot

# Seed a new pool
python files/thread-3/seed_pool.py --pool mypool --generate
```

## Chat Commands

| Command | Description |
|---------|-------------|
| `/pool <name>` | Switch active pool |
| `/pools` | List all pools |
| `/reset` | Clear conversation history |
| `/debug` | Toggle retrieval visibility |
| `/waterline <n>` | Set relevance threshold |
| `/context <query>` | Preview what would be retrieved |
| `/chain` | Show session thought chain |
| `/quit` | Exit |

## Pools

| Pool | Purpose |
|------|---------|
| `wot` | WoT development traces |
| `stained-glass` | Test pool (craft knowledge) |
| `default` | Legacy name for wot |

## Environment Variables

| Var | Description |
|-----|-------------|
| `WOT_API_ENDPOINT` | Azure/OpenAI endpoint URL |
| `WOT_API_KEY` | API key |
| `WOT_DEPLOYMENT` | Model deployment name |
| `ANTHROPIC_API_KEY` | Direct Anthropic API (if not using Azure) |
