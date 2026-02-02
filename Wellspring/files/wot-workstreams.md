# WoT Development Workstreams

Three parallel tracks to bootstrap WoT development with WoT.

---

## Thread 1: RFC Draft (Protocol Spec)

**Goal:** IETF-style spec that tells implementers exactly what to build.

### Todo List

1. **Define wire format**
   - Thought serialization (CBOR vs JSON vs custom)
   - CID computation (hash algorithm, canonicalization)
   - Signature format (ed25519 envelope)
   - Packet header (64-byte format from traces)

2. **Specify handshake protocol**
   - Hello card format
   - Identity verification flow
   - Pool membership negotiation
   - Bilateral attestation ceremony

3. **Document sync semantics**
   - Bloom filter hotpath
   - Visibility filtering rules
   - Peering agreement format
   - Conflict resolution (CRDT properties)

4. **Define MUST/SHOULD/MAY requirements**
   - Minimum viable client
   - Optional extensions
   - Versioning/upgrade path

5. **Write conformance tests**
   - Test vectors for CID computation
   - Signature verification cases
   - Sync scenarios

**Entry point:** Read wot-v0.7.md sections: The Primitive, Sync, Implementation Notes

---

## Thread 2: RAG/Vector Indexing (Subconscious Layer)

**Goal:** Thoughts → embeddings → retrieval. Pool membership gates what gets indexed.

### Todo List

1. **Design thought→embedding pipeline**
   - Which fields to embed (content, because summaries, connection context)
   - Chunking strategy for large thoughts
   - Embedding model choice (local: all-MiniLM, API: text-embedding-3-small)

2. **Implement pool-scoped indexing**
   - Index per pool (separate vector stores)
   - Visibility filtering at index time
   - Trust-weighted retrieval (boost by attestation weight)

3. **Build retrieval API**
   - Query: natural language → relevant thought CIDs
   - Filters: pool, time range, creator, aspect
   - Return: ranked CIDs with scores + snippets

4. **Add connection-aware ranking**
   - Because chain proximity boost
   - Attestation weight multiplier
   - Recency decay

5. **Storage backend**
   - SQLite + sqlite-vss for local
   - Optional: Qdrant/Chroma for scale
   - Index metadata alongside vectors

**Entry point:** Start with SQLite + sqlite-vss, single pool, basic embed→store→retrieve

---

## Thread 3: Pool Control + Context Surfacing (Execution Loop)

**Goal:** The agent loop — query pool, assemble context, execute LLM, parse thoughts back.

### Todo List

1. **Define thought generation protocol**
   - Input format to LLM (system prompt + context + user input)
   - Output format from LLM (structured thought proposals)
   - Parsing rules (extract CID references, attestations, connections)

2. **Build context assembly**
   - Query relevant thoughts (via Thread 2 RAG)
   - Format for LLM consumption
   - Token budget management
   - Priority: high-trust, high-salience first

3. **Implement thought writer**
   - LLM response → thought objects
   - Automatic because chain (what context was used)
   - Source attribution: `agent-model/claude-3-opus`
   - Visibility: inherit from pool or explicit

4. **Create execution wrapper**
   - OpenWebUI-compatible `/chat/completions` endpoint
   - Intercept: inject pool context before LLM call
   - Intercept: parse response, write thoughts after
   - Pass-through: streaming, tool calls

5. **Pool control thoughts**
   - Thoughts that modify pool behavior
   - Example: "Set waterline to 0.7 for this session"
   - Example: "Include thoughts from pool:research in context"
   - Meta-thoughts that configure the agent

6. **Feedback loop**
   - Human accepts/rejects AI-generated thoughts
   - Correction chain when edited
   - Training signal: what was useful?

**Entry point:** Minimal loop — hardcoded context → Claude API → parse single thought → store

---

## Bootstrap Sequence

```
Day 1: Thread 3 MVP (manual context, Claude API, thought storage)
        Thread 2 basic (embed thoughts, simple retrieval)

Day 2: Thread 3 + Thread 2 integration (RAG-based context)
        Thread 1 draft (wire format, CID computation)

Day 3: Thread 1 test vectors
        Thread 3 OpenWebUI wrapper
        Thread 2 pool-scoped indexing

Day 4: Self-hosting — use WoT to track WoT development
```

---

## Shared Infrastructure

All threads need:

- **Thought storage:** JSONL export (graph commits wait for Thread 2)
- **Identity:** Single ed25519 keypair for dev
- **Pool:** `pool:wot-development` for dogfooding

File: `wellspring_core.py`
- `create_thought(content, type, because, visibility)`
- `sign_thought(thought, privkey)`
- `compute_cid(thought)`
- `store_thought(thought)`
- `get_thought(cid)`

This is the shared foundation all three threads build on.

---

## Development Traces as Thoughts

**Key principle:** Each thread logs its work as prototype thoughts to JSONL. Don't commit to graph until Thread 2 is working — but generate the corpus now.

Each thread outputs to its own trace file:
- `thread-1/traces.jsonl`
- `thread-2/traces.jsonl`
- `thread-3/traces.jsonl`

**What to capture as thoughts:**

| Event | Thought Type | Example |
|-------|--------------|---------|
| Decision made | `decision` | "Using CBOR over JSON for wire format" |
| Question raised | `question` | "Should CID include timestamp?" |
| Finding/discovery | `finding` | "sqlite-vss requires specific build flags" |
| Code written | `artifact` | "Created embedding pipeline v1" |
| Bug found | `bug` | "CID mismatch when content has unicode" |
| Reference used | `reference` | Link to external doc with because chain |

**Trace thought format:**

```json
{
  "type": "trace",
  "content": {
    "category": "decision|question|finding|artifact|bug|reference",
    "title": "Short description",
    "body": "Details...",
    "thread": 1
  },
  "source": "cowork/thread-1",
  "because": ["<cid of related prior thought if any>"],
  "created_at": 1738339200000
}
```

**When Thread 2 comes online:**
1. Merge all thread traces into single corpus
2. Index with embeddings
3. Start surfacing relevant context
4. Bootstrap complete — WoT tracking WoT development

---

## Instance Assignment

**Cowork 1 (this instance):** Coordination, v0.7 spec, architecture decisions

**Cowork 2:** Thread 1 — RFC Draft
- Start with: wire format, CID computation
- Reference: wot-v0.7.md, Implementation Notes section

**Cowork 3:** Thread 2 — RAG/Vector Indexing
- Start with: SQLite + sqlite-vss setup, basic embedding
- Reference: wot-v0.7.md, Salience and Waterline section

**Cowork 4:** Thread 3 — Pool Control + Execution Loop
- Start with: Claude API wrapper, thought generation
- Reference: wot-v0.7.md, Hierarchical Agent Architecture section

Each instance should write to `/files/thread-N/` subdirectory.
