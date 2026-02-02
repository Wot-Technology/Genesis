# Web of Thought (WoT) Integrations Specification v0.9

**Transport, Discovery, and System Integration**

*wot.rocks · wot.technology · now.pub*

*February 2026*

---

## Abstract

This document covers integration points between WoT core protocol and external systems: network transport, identity systems, discovery mechanisms, and filesystem/sync patterns.

**Key insight:** Same crypto for everything. Ed25519 keypair works for WoT identity, TLS client certs, Tor v3 onion addresses, and network access grants. The graph IS the ACL.

---

## Part 1: Wire Format

### Packet Structure

```
┌─────────────────────────────────────────────┐
│ HEADER (64 bytes fixed)                     │
├─────────────────────────────────────────────┤
│ magic: u32          "WLSP"                  │
│ version: u16        protocol version        │
│ flags: u16          compression, encryption │
│ schema_cid: [u8;32] reference to schema     │
│ payload_type: u8    inline | reference      │
│ payload_len: u32    payload size            │
│ trust_anchor: [u8;32] nearest checkpoint    │
│ hop_count: u8       TTL / decay metric      │
│ reserved: [u8;6]    future use              │
├─────────────────────────────────────────────┤
│ PAYLOAD (variable)                          │
│ - inline: serialized thought (CBOR)         │
│ - reference: CID + location hints           │
├─────────────────────────────────────────────┤
│ SIGNATURE (64 bytes)                        │
│ ed25519 over header + payload               │
└─────────────────────────────────────────────┘
```

### Header Fields

| Field | Bytes | Description |
|-------|-------|-------------|
| magic | 4 | `0x574C5350` ("WLSP") |
| version | 2 | Protocol version (current: 0x0009) |
| flags | 2 | Bit 0: compressed (zstd), Bit 1: encrypted (ChaCha20-Poly1305) |
| schema_cid | 32 | Schema reference — fetch if unknown |
| payload_type | 1 | 0x00 = inline, 0x01 = reference |
| payload_len | 4 | Payload size in bytes |
| trust_anchor | 32 | Nearest verification checkpoint CID |
| hop_count | 1 | Decrements per hop, natural TTL |
| reserved | 6 | Must be zero |

### Flags

```
Bit 0: COMPRESSED  - Payload is zstd compressed
Bit 1: ENCRYPTED   - Payload is ChaCha20-Poly1305 encrypted
Bit 2: CHUNKED     - Part of multi-packet message
Bit 3-15: Reserved
```

### Serialization

- **Canonical form**: CBOR (RFC 8949)
- **Compression**: zstd level 3 for payloads > 1KB
- **Encryption**: ChaCha20-Poly1305 for private pool traffic

### Location Hints (Reference Payloads)

```json
{
  "cid": "cid:blake3:...",
  "hints": [
    { "type": "ipfs", "multiaddr": "/ip4/..." },
    { "type": "http", "url": "https://..." },
    { "type": "peer", "identity": "cid:blake3:..." }
  ]
}
```

---

## Part 2: Identity Collapse

**One keypair, all systems.** Ed25519 works for:

| System | Derivation |
|--------|------------|
| WoT identity | Direct pubkey |
| TLS client cert | X.509 wrapper around ed25519 |
| Tor v3 onion | Direct (ed25519 is Tor v3 native) |
| SSH | ed25519 key format |
| Age encryption | X25519 (derived from ed25519) |

### Tor v3 Onion Address

Tor v3 uses ed25519 natively. Your WoT identity key IS your onion address:

```python
from hashlib import sha3_256

def identity_to_onion(pubkey: bytes) -> str:
    # Tor v3 onion = base32(pubkey + checksum + version)
    checksum = sha3_256(b".onion checksum" + pubkey + b"\x03").digest()[:2]
    address_bytes = pubkey + checksum + b"\x03"
    return base64.b32encode(address_bytes).decode().lower() + ".onion"
```

### TLS Client Certificate

Wrap ed25519 in X.509 for TLS mutual auth:

```
Certificate:
  Subject: CN=cid:blake3:your_identity
  Public Key: ed25519:...
  Issuer: Self-signed
  Extensions:
    WoT-Identity-CID: cid:blake3:...
```

### Network Access Grants

Access grant as thought:

```json
{
  "type": "access_grant",
  "content": {
    "identity": "cid:blake3:peer_identity",
    "resource": "ipv6:2001:db8::1/128",
    "protocols": ["sync", "query"],
    "expires": 1709251200000
  },
  "attested_by": "network_owner_identity"
}
```

**The collapse:** 5 identity systems → 1. The graph IS the ACL. Attestation controls firewall rules.

---

## Part 3: Discovery

### Three Tiers

```
CLEARNET (DNS)     →  Fast, convenient, censorable
        ↓ fallback
DARKNET (Onion)    →  Censorship-resistant, slower
        ↓ fallback
P2P (IPNS)         →  Fully decentralized, variable latency
```

Same identity, same trails, different transport.

### DNS Discovery

TXT record format:

```
_wot.example.com. IN TXT "v=wot1 root=cid:blake3:... id=cid:blake3:..."
```

| Field | Description |
|-------|-------------|
| v | Protocol version |
| root | Root thought CID for this domain |
| id | Identity CID of domain owner |

**Bidirectional binding:**
1. DNS points to identity CID
2. Identity thought contains `same_as` connection to domain
3. Both must match for verification

### Onion Discovery

Onion address derived from identity (see Part 2). Hidden service serves:

```
GET /.well-known/wot.json
{
  "identity": "cid:blake3:...",
  "root": "cid:blake3:...",
  "sync_endpoint": "/wot/sync",
  "query_endpoint": "/wot/query"
}
```

### IPNS Discovery

IPNS key = ed25519 pubkey. Resolves to trail bookmark CID.

```
wellspring://keif/trail/wot-spec
    ↓ IPNS resolution
trail bookmark CID
    ↓ 
entry thought
    ↓
walk because chain
```

### Fallback Chain

```python
async def discover(identifier: str) -> WotEndpoint:
    # Try DNS first (fast)
    if endpoint := await try_dns(identifier):
        return endpoint
    
    # Fallback to Onion (censorship-resistant)
    if endpoint := await try_onion(identifier):
        return endpoint
    
    # Final fallback: IPNS (fully decentralized)
    return await try_ipns(identifier)
```

### Revocation via DNS

Fast global revocation without central list:

```
_revoked.example.com. IN TXT "cid:blake3:compromised_identity ts=1709251200"
```

Check before trusting any identity bound to domain.

---

## Part 4: Sync Protocol

### Gossip Protocol

```
Round N:
  1. Pick random peer from trust graph
  2. Exchange bloom filter of recent CIDs (last 24h)
  3. Identify deltas:
     - They have, I don't → request
     - I have, they don't → offer
  4. Transfer missing thoughts
  5. Verify attestation chains
  6. Merge to local graph

Heat = rounds since last touch
Decay = natural from round counting
```

### Bloom Filter Negotiation

```json
{
  "type": "sync_negotiate",
  "filter": "base64_bloom_filter",
  "filter_size": 10000,
  "hash_count": 7,
  "since": 1709164800000
}
```

False positive rate ~1% acceptable. Worst case: unnecessary fetch.

### Delta Transfer

```json
{
  "type": "sync_delta",
  "thoughts": [
    { "cid": "...", "thought": { ... } },
    { "cid": "...", "thought": { ... } }
  ],
  "connections": [...],
  "attestations": [...]
}
```

Order: thoughts first, then connections, then attestations. Ensures references resolve.

### Bilateral Sync Confirmation

```json
{
  "type": "connection",
  "content": {
    "relation": "sync_confirmed",
    "from": "thought_cid",
    "to": "sync_channel_cid"
  }
}

// Attestations from both parties confirm receipt
```

Sync status:
- Both attested = confirmed
- Sender only = pending
- Receiver -1.0 = disputed (check `because`)

---

## Part 5: DID Interoperability

WoT has its own identity model. DIDs can map via `same_as` connections.

### Why Not Just DIDs?

DIDs are identifiers. WoT needs:
- One primitive (thoughts + connections)
- Immutable content addressing
- Trust computed from vouch graph

These aren't DID features. But DIDs can map.

### Mapping Pattern

```json
{
  "type": "connection",
  "content": {
    "relation": "same_as",
    "from": "cid:blake3:wot_identity",
    "to": "did:key:z6Mkh..."
  }
}
```

Connection signed by WoT identity. Verifies control of both.

### Supported Mappings

| External ID | Format |
|-------------|--------|
| DID Key | `did:key:z6Mkh...` |
| DID Web | `did:web:example.com` |
| Email | `mailto:user@example.com` |
| GitHub | `https://github.com/username` |
| ENS | `username.eth` |
| Nostr | `npub1...` |

`same_as` is symmetric. Systems can resolve either direction.

---

## Part 6: Filesystem Patterns

### Pool as Sync Boundary

```
Traditional cloud sync:
  Folder → Sync all or nothing
  Permissions → Lost in transit
  Conflict → Last write wins (data loss)

WoT sync:
  Pool → Granular via connections
  Permissions → ARE the graph
  Conflict → Thoughts immutable, attestations accumulate
```

### Permission Fidelity

```
NTFS/POSIX lost in cloud:
  - User/group ownership
  - ACLs
  - Inheritance chains

WoT preserves:
  - created_by = ownership
  - pool membership = group
  - attestations = ACL
  - connection graph = inheritance
```

### Backstop Model

Cloud/relay is optional, not required:

```
Your devices ←→ Your devices   (P2P, primary)
       ↓              ↓
    Relay (optional backstop)
       - Just another peer
       - Good uptime SLA
       - Not the arbiter
       - Not required
```

Revoke relay's pool membership → it stops seeing your data.

### Local-First Principles

1. Works offline (local graph is truth)
2. Syncs when connected (P2P or via relay)
3. Conflicts are structural (no data loss)
4. Permissions travel with data

---

## Part 7: Agent Integration

### Context Injection

Daemon surfaces relevant thoughts before LLM call:

```
Query arrives
    ↓
Subconscious: fast retrieval (bloom + vectors)
    ↓
"50 candidate CIDs"
    ↓
Trust filter: "12 pass threshold"
    ↓
Working memory: recency + relevance
    ↓
Conscious: top N injected into context
    ↓
LLM responds with grounded claims
```

### MCP Server Interface

```rust
trait WotMcpServer {
    fn search_thoughts(&self, query: &str, limit: usize) -> Vec<Thought>;
    fn get_thought(&self, cid: &str) -> Option<Thought>;
    fn walk_because(&self, cid: &str, depth: usize) -> Vec<Thought>;
    fn walk_dependents(&self, cid: &str) -> Vec<Thought>;
    fn find_by_type(&self, thought_type: &str) -> Vec<Thought>;
    fn recent_thoughts(&self, since: i64) -> Vec<Thought>;
}
```

### Context Format

```xml
<thought_context>
  <thought cid="cid:blake3:abc">
    <type>article_note</type>
    <content>...</content>
    <because>cid:blake3:source</because>
    <trust>0.87</trust>
  </thought>
  ...
</thought_context>
```

LLM receives structured provenance, not just text. Can trace claims to sources.

### Hallucination Floor

WoT raises the verifiable floor:
- Attestation weight = confidence (not fake certainty)
- No attestation = "I don't vouch"
- Empty `because` = ungrounded assertion (visible)
- Tool use: walk trails for verification
- Human checkpoint for high-stakes

---

## Part 8: Security Model

### Trust Graph as Firewall

External data can't influence agents without attestation from trusted source.

```
Fetched content → No attestation → Ungrounded → Doesn't surface
                      ↓
              Trusted source attests
                      ↓
               Enters your graph
```

Prevents:
- Prompt injection via RAG
- "Ignore previous instructions" in fetched content
- Poisoned training data

### Attack Resistance

| Attack | Defense |
|--------|---------|
| Sybil | Vouches are expensive, weight beats volume |
| Brigading | Trust-weighted, not count-weighted |
| Impersonation | Signatures verify identity |
| Content tampering | CIDs verify content |
| Replay | Timestamps + nonces in attestations |

### Revocation Propagation

```
Revoke attestation
    ↓
Propagate to all pools with connection
    ↓
Downstream trust recomputes
    ↓
Affected content drops below threshold
    ↓
No longer surfaces
```

Revocation beats approval. Fail-safe.

---

## Part 9: Private Checkpoints

### Attention Sovereignty

Track your own engagement. Never leaves device. Never syncs.

```json
{
  "type": "checkpoint",
  "content": {
    "about": "article_cid",
    "opened": true,
    "scroll_depth": 0.8,
    "time_spent_ms": 272000,
    "return_count": 3
  },
  "visibility": "local_forever"
}
```

### Feeds Your Salience

```
private_engagement = (
    opens +
    returns × 2 +
    time_spent / expected_time +
    scroll_completion
)

salience += private_weight × private_engagement
```

### The Honest Index

```
Public: "I recommend this article"
Private: Opened 12 times, never finished, bounced at section 3

Your salience: LOW despite public attestation
Your behavior contradicts your words.
Index knows. No one else does.
```

### Flip Surveillance

```
Platform: Track you → Sell to advertisers → Their goals
WoT:      Track you → Keep private → Your goals
```

---

## Part 10: now.pub Integration

### Live Identity Namespace

`[identity].now.pub` → current focus, status, availability

### Thought with TTL

```json
{
  "type": "now_status",
  "content": {
    "focus": "WoT v0.9 spec",
    "availability": "deep_work",
    "until": 1709257200000
  },
  "ttl": 3600000
}
```

Auto-stale if not refreshed within TTL.

### Ambient from Trails

"What ARE you working on?" derived from recent activity:
- Recent `because` chains
- Active pool memberships
- Attestation patterns

Bot availability too: queue depth, estimated wait.

---

## Appendix: URI Schemes

### wot:// URIs

```
wot://[identity]/[type]/[name]

Examples:
wot://keif/trail/wot-spec
wot://library/schema/bookmark
wot://now.pub/status/keif
```

### Resolution

```
wot://keif/trail/wot-spec
    ↓
Resolve "keif" via discovery (DNS → Onion → IPNS)
    ↓
Get root thought for identity
    ↓
Find trail named "wot-spec"
    ↓
Return trail entry CID
```

---

*End of Integrations Specification*
