# Thread 1 → Thread 2 Handoff

**From:** Thread 1 (RFC/Protocol)
**To:** Thread 2 (RAG/Vector Indexing)
**Date:** 2026-01-31

---

## What You Need to Know

### CID Format

All CIDs are 36-byte IPFS-compatible multiformat:

```
CIDv1 + dag-cbor (0x71) + blake3-256 (0x1e) + 32-byte digest
```

Use this for all thought references, indexing keys, and IPFS interop.

### Core Thought Structure

```
Thought {
  cid:        36 bytes (computed from below)
  type:       string (schema name)
  content:    typed payload
  created_by: CID of identity
  created_at: int64 (unit per schema: s/ms/us/ns, default ms)
  because:    [CID, ...] — what led to this thought
  visibility: null | "local_forever" | "pool:<cid>"
  signature:  64 bytes ed25519
}
```

**CID computed from:** `{type, content, created_by, because}` only.

### The Three Layers (Critical for RAG)

```
1. POOL MEMBERSHIP  → you have the thoughts (sync)
2. CONNECTIONS      → logical structure (surfacing)
3. CHAIN ACCESS     → can you attach? (the ONE permission)
```

**Reading is implicit.** If you're in the pool, you have the data.

**Surfacing is connection-based.** Index everything, but surface based on connections and chain_access.

### What to Embed

For RAG retrieval, embed:

| Field | Embed? | Notes |
|-------|--------|-------|
| `content` | YES | Primary semantic content |
| `type` | YES | Schema context matters |
| `because` chain | CONSIDER | Context of what led here |
| `created_by` | NO | Filter, don't embed |
| `created_at` | NO | Filter, don't embed |

### Trust-Weighted Retrieval

When retrieving, weight by:

1. **Chain access** — does observer have access to this chain?
2. **Attestation weight** — how strongly attested?
3. **Because chain proximity** — how close to query context?
4. **Recency** — heat decay

### Appetite Notes

Your indexer should respect `appetite_note` thoughts:

| Status | Index behavior |
|--------|----------------|
| `welcomed` | Full index, high priority |
| `unauthorized_claim` | Index but flag |
| `low_trust_path` | Index but lower weight |
| `pending_attestation` | Buffer, don't surface yet |

### Pool-Scoped Indexing

Each pool gets its own index. Thoughts have `visibility: "pool:<cid>"` that scopes them.

```
Index structure:
  /pool_a/
    vectors.db
    metadata.db
  /pool_b/
    vectors.db
    metadata.db
```

### Schema CIDs

Thoughts are self-describing. Schema CID in packet header tells you what you're looking at. Cache schemas by CID.

---

## Key Files to Read

- `thread-1/schemas-core.md` — all thought schemas
- `thread-1/wot-wire-format-draft.md` — CID computation, packet format
- `thread-1/test_vectors.json` — CID test vectors for validation

---

## New: Network Layer Context

Thread 1 added `network-workflows.md` covering gRPC service, schema negotiation, and sync protocol. Key for Thread 2:

- **Schema compilation:** WoT schemas (thoughts) compile to protobuf for wire efficiency
- **Dual encoding:** CBOR for CID verification, protobuf for fast parse
- **Bloom filters:** ~12KB for 10k thoughts at 1% false positive — you'll need to maintain these

## Questions Thread 2 Should Answer

1. Chunking strategy for large thoughts?
2. Embedding model choice (local vs API)?
3. How to embed structured content (attestations, connections)?
4. Index update strategy when new attestations arrive?
5. Bloom filter maintenance — rebuild frequency, incremental updates?
