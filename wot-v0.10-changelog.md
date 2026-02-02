# Web of Thought (WoT) v0.10 Release Notes

**Protocol for Distributed Knowledge with Computable Trust**

*wot.rocks · wot.technology · now.pub*

*February 2026*

---

## Summary

v0.10 is a schema-layer release. **No primitive changes.** Everything new slots in on top of the existing one-primitive model: thoughts, connections, attestations, aspects, pools, schemas.

The core thesis remains: memory is traversal, trust is computed, access is structural.

---

## What's New in v0.10

### Three Attestation-Driven Patterns (Core)

Formalized the insight that attestation drives three distinct protocol behaviors through different `via` aspects:

| Pattern | Via Aspect | Triggers |
|---------|-----------|----------|
| Trust signal | `agreement` | Trust computation |
| Content delivery | `ready_to_consume` | Streaming/sync |
| Attention request | `request_attention` | Surfacing/caching |

Same primitive. Same structure. Different aspect = different behavior. Attestation does triple duty: trust signal, pull request, and attention broker.

### Attestation-Triggered Content Delivery (Implementation Part 11)

Pull-based content delivery via attestation. Browse metadata freely, attest interest to trigger streaming. Schema-driven delivery modes: eager, lazy, stream, reference.

Weight semantics for consumption: 1.0 = stream now, 0.5 = queue, 0.0 = cancel, -1.0 = remove from graph. Economic layer: `because` chain on attestation carries payment commitment. Creator verifies before streaming. No platform cut.

### Attention Requests (Implementation Part 12)

Directed request for identity to engage with thought. Trust-weighted @-mention with protocol semantics. Weight as urgency (0.1 = pre-cache, 1.0 = interrupt). Effective urgency = weight × requester trust. No trust = no attention = spam is structurally impossible.

### Response Schemas (Core + Implementation Part 12)

Protocol-level response vocabulary. Six bootstrap schemas: universal, attention, review, governance, delivery, invitation. Schema inheritance via `extends` field. Universal responses (seen/acted/denied/ignored) always available. Domain schemas add vocabulary on top. Custom schemas can extend core.

### Encrypted Storage — Timed Access (Implementation Part 13)

Ephemeral keys with compound expiry: time, event, access count. After expiry, key destroyed, content becomes cryptographic noise. Not DRM — can't prevent copying during access window. Guarantees: blob at rest is noise, storage provider can't recover, late arrivals can't decrypt.

### Per-Identity Content Key Wrapping (Implementation Part 13, new in v0.10)

Content key encrypted directly to recipient's Ed25519→X25519 public key. Leaked blob + different identity = noise. Leaked blob + same identity = forensic trail. Combine with timed access for cryptographic proof of who had access when. Not logs. Maths.

### Structural Retrieval / PageIndex Pattern (Implementation Part 14)

Two-tier retrieval: structural (graph reasoning) first, vector (embedding similarity) as fallback. WoT thought graph maps directly to PageIndex tree — with richer signal from typed connections, attestations, and because chains.

### Product Applications (Implementation Part 15, new in v0.10)

**Dead Data Investigator:** Filesystem adapter + MCP server + attention requests. Agent indexes drive as thought graph, creates attention requests for findings, daemon trust-gates and surfaces, human attests. Same daemon, different corpus.

**Model Provenance:** Every AI response signed with model identity. Provider attests model identity via vouch chain. Consumer verifies. Solves: invisible model swaps, unverifiable claims, absent response provenance.

### Model Provenance Integration (Integrations Part 11, new in v0.10)

Trust chain from provider → model identity → response thought. Signature verification against known model keys. Demonstrated live: model routing failures during spec development showed the exact absence of provenance WoT addresses.

### DNS as Thought Transport (Integrations Part 3)

DNS TXT records carry WoT thoughts directly. Self-signed by identity key; DNSSEC redundant for integrity. Tiered risk model for key reuse: same key for public meta-layer, derived key for private graph.

### Live Protocol Demonstrations (Implementation Appendices)

**Three Seashells (Appendix A):** Agent proposes Stallone, human corrects to Snipes. Full correction chain with rework, attestation, because. Demonstrates: corrections are first-class, confidence ≠ truth, pool context matters.

**Anthropocene Correction (Appendix B, new in v0.10):** Agent assumes shared knowledge, human's autocorrect produces "Anthropocene" instead of "Anthropic." Demonstrates: source attribution via `uses_input` schema, ungrounded assumptions, cost/benefit attestation of corrections.

---

## Document Set

| Document | Lines | Scope |
|----------|-------|-------|
| `wot-v0.10-core.md` | 949 | Primitives, types, access, trust, sync, schemas, identity |
| `wot-v0.10-integrations.md` | 787 | Wire format, discovery, transport, DID, filesystem, agent, model provenance |
| `wot-v0.10-implementation.md` | 2,595 | Storage, indexers, prototype roadmap, content delivery, attention, encryption, structural retrieval, product applications, live demos |
| **Total** | **4,331** | |

---

## What Didn't Change

- **Thought structure**: Unchanged since v0.8
- **CID computation**: BLAKE3, canonical JSON
- **Connection model**: Typed `from`/`to` with relations
- **Attestation model**: `on`/`via`/`weight`
- **Pool governance**: Solo/bilateral/threshold/delegated
- **Identity**: Ed25519, self-referential bootstrap
- **Because chains**: ContentRef with segment/anchor/path/temporal
- **Rework chains**: Connection-based edit history
- **Access model**: Structural via pool membership

The one primitive holds. Every v0.10 addition is a schema, an aspect, or a usage pattern on top of what's already there.

---

## Prototype Status

Rust WASM nodes peering and exchanging thoughts (separate development context). Core proven: identity, thoughts, CIDs, peering, git indexer. All v0.10 additions are schema layer — slot in without bending model.

---

## What's Next

- Reconcile spec against running Rust prototype
- Filesystem adapter (third indexer after git, wiki)
- MCP server for attention request daemon
- Response schema validation in core
- Economic layer formalization (payment channels via `because`)

---

*Git blame for all media. Receipts all the way down.*

*Ergo cognito sum.*
