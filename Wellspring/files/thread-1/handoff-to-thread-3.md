# Thread 1 → Thread 3 Handoff

**From:** Thread 1 (RFC/Protocol)
**To:** Thread 3 (Pool Control + Execution Loop)
**Date:** 2026-01-31

---

## What You Need to Know

### CID Format

All CIDs are 36-byte IPFS-compatible multiformat:

```
CIDv1 + dag-cbor (0x71) + blake3-256 (0x1e) + 32-byte digest
```

### Core Thought Structure

```
Thought {
  cid:        36 bytes
  type:       string (schema name)
  content:    typed payload
  created_by: CID of identity
  created_at: int64 (unit per schema, default ms)
  because:    [CID, ...] — CRITICAL: what led to this thought
  visibility: null | "local_forever" | "pool:<cid>"
  signature:  64 bytes ed25519
}
```

### The Because Chain — Your Core Mechanism

When the agent generates a thought, it MUST populate `because` with:

- CIDs of context thoughts that were used
- CIDs of user input thoughts
- CIDs of retrieved thoughts (from Thread 2 RAG)

This creates the audit trail. Walk `because` backward = reasoning path.

### Agent Identity

Agents have identity thoughts too:

```json
{
  "type": "identity",
  "content": {
    "name": "claude-opus-agent",
    "pubkey": "ed25519:...",
    "autonomy": "supervised"
  }
}
```

Agent-generated thoughts have `created_by: <agent_identity_cid>`.

### Source Attribution

Track input source in thoughts:

```
source: "keif/desktop_keyboard"     — human typed
source: "keif/voice_transcribed"    — human spoke
source: "agent-model/claude-opus"   — agent generated
source: "agent-model/autocomplete"  — inline suggestion
```

### Chain Access — The ONE Permission

```
1. POOL MEMBERSHIP  → agent has the data
2. CONNECTIONS      → agent sees the structure
3. CHAIN ACCESS     → can agent attach here?
```

Before generating a thought that attaches to a chain, check:
- Does agent identity have `chain_access` for target chain?
- If no → can still generate, but mark as proposal needing human attestation

### Thought Types Your Loop Will Generate

| Type | When |
|------|------|
| `basic` | Simple content output |
| `connection` | Linking thoughts (supports, continues, etc.) |
| `attestation` | Agent's assessment of a thought |
| `annotation` | Summary, translation, extraction |

### Annotation Schema (Agent Auto-Generates)

```json
{
  "type": "annotation",
  "content": {
    "target_cid": "<thought being annotated>",
    "annotation_type": "summary",
    "content": "TL;DR of the thought",
    "confidence": 0.85,
    "model": "claude-opus-4"
  },
  "visibility": "local_forever"
}
```

### Pool Rules — What the Agent Must Respect

Pool thoughts define `pool_rules`:

```json
{
  "accept_schemas": ["basic", "connection"],
  "require_because": true,
  "max_payload_bytes": 65536,
  "timestamp_unit": "ms",
  "auto_annotate": ["summarize", "extract_links"]
}
```

Your loop should:
1. Check `require_because` — reject empty because chains if true
2. Check `accept_schemas` — only generate allowed types
3. Run `auto_annotate` on received thoughts

### Appetite Notes — Soft Rejection

When processing incoming thoughts:

```
Signature invalid? → HARD REJECT (only case)
Everything else   → Store, annotate with appetite_note
```

Appetite note statuses:
- `welcomed` — matches appetite, surface it
- `unauthorized_claim` — claims chain access we can't verify
- `low_trust_path` — below trust threshold
- `pending_attestation` — waiting for more attestations

### Human-in-the-Loop

Agent proposes → Human attests. The attestation is what matters.

```
Agent generates thought (created_by: agent_cid)
    ↓
Human reviews
    ↓
Human creates attestation thought:
  type: "attestation"
  content: { on: <agent_thought_cid>, weight: 0.9 }
  created_by: <human_cid>
    ↓
Now it's trusted
```

### Rework Chain

When human edits agent output:

```
v1 (agent draft)
  ↓ rework connection
v2 (human edit)
  ↓ rework connection
v3 (final)
```

Capture the edit history. Training signal.

---

## Key Files to Read

- `thread-1/schemas-core.md` — all thought schemas including annotation, attestation
- `thread-1/wot-wire-format-draft.md` — CID computation (for signing thoughts)
- `wot-v0.7.md` — Hierarchical Agent Architecture section

---

## New: Network Layer Context

Thread 1 added `network-workflows.md` covering gRPC service, schema negotiation, and sync protocol. Key for Thread 3:

- **gRPC service:** `WotPeer` service with Hello, Join, Sync, Push methods
- **Schema validation:** Before syncing, validate thoughts against pool_rules
- **Dual encoding:** Agent outputs as CBOR (for CID) + protobuf (for wire)

## Questions Thread 3 Should Answer

1. Context assembly — how to format thoughts for LLM consumption?
2. Token budget — how to prioritize when context overflows?
3. Thought parsing — how to extract structured thoughts from LLM output?
4. Streaming — how to handle streaming responses?
5. Schema compilation — agent needs to produce valid protobuf payloads
