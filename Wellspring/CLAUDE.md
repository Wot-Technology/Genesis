# Agent Instructions — Wellspring Eternal

This file contains instructions for AI agents working in this codebase.

## Identity

You are working within the **Web of Thoughts (WoT)** system — a persistent, content-addressed memory layer for AI agents.

## Key Principles

1. **Thoughts are immutable** — once created, a thought's CID never changes
2. **Provenance matters** — use `because` chains to link derived insights to sources
3. **Pools are boundaries** — don't mix contexts across pools
4. **Content-addressed** — identical content = identical CID (deduplication is automatic)

## Injecting Thoughts

When you have findings, traces, or insights worth persisting:

```bash
# From the Wellspring Eternal root
python inject.py --text "Your insight here" --type TYPE --pool POOL
```

### Thought Types

| Type | When to use |
|------|-------------|
| `trace` | Development logs, debug output, findings |
| `insight` | Derived understanding, conclusions |
| `decision` | Choices made with rationale |
| `question` | Open questions to explore |
| `basic` | Simple notes |
| `message` | Conversational content |

### Examples

```bash
# Log a finding
python inject.py --text "Found race condition in pool sync" --type trace --pool wot

# Record a decision
python inject.py --json '{"decision": "use blake3", "rationale": "IPFS compatible"}' --type decision --pool wot

# Chain to prior thought
python inject.py --text "This confirms the earlier hypothesis" --type insight --because cid:blake3:abc123...

# Pipe output
my_analysis | python inject.py --type trace --source "agent/analyzer" --pool wot
```

## File Locations

| Path | Purpose |
|------|---------|
| `/Wellspring Eternal/inject.py` | Shared injection tool |
| `/Wellspring Eternal/files/thread-3/` | Main daemon code |
| `/Wellspring Eternal/files/thread-2/` | RAG/embeddings |
| `/Wellspring Eternal/files/thread-1/` | Core primitives |

## Working with Pools

- `wot` — Main development pool (WoT traces, decisions, insights)
- `stained-glass` — Example/test pool with craft knowledge
- Create new pools with `seed_pool.py` if needed

## Best Practices

1. **Always specify pool** — Don't rely on defaults
2. **Use `--because`** — Link derived thoughts to sources
3. **Meaningful types** — Choose appropriate thought type
4. **Quiet mode for chaining** — Use `-q` when piping CIDs

```bash
# Chain pattern
CID1=$(python inject.py --text "First thought" -q)
CID2=$(python inject.py --text "Builds on first" --because $CID1 -q)
python inject.py --text "Synthesizes both" --because $CID1 --because $CID2
```

## Don't

- Don't inject trivial/noisy content (wastes context budget)
- Don't mix pool contexts without reason
- Don't forget `--pool` flag
- Don't inject secrets or credentials

## Thread Architecture

| Thread | Responsibility |
|--------|----------------|
| Thread 1 | Core primitives, schemas, signing |
| Thread 2 | Vector indexing, RAG retrieval |
| Thread 3 | Execution loop, daemon, chat interface |
