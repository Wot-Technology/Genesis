# Web of Thought (WoT) Integrations Specification v0.10

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
| version | 2 | Protocol version (current: 0x000A) |
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

### DNS as Thought Transport

DNS can carry WoT thoughts directly — schemas, identity bindings, governance. The thought is self-signed; DNSSEC is redundant for integrity.

```
DNS TXT record:
  - Contains WoT thought (signed by identity key)
  
Verifier:
  - Fetches from DNS
  - Ignores DNSSEC (or treats as bonus layer)
  - Verifies WoT signature directly
  - Trusts thought, not DNS infrastructure
```

**Simple case — small thoughts inline:**

```
_schema.example.com TXT '{"type":"schema","content":{...},"sig":"ed25519:..."}'
```

**Chunked for larger payloads:**

```
_wot.example.com TXT "cid:blake3:abc123 chunks=3"
abc123.0._chunks.example.com TXT "base64chunk0..."
abc123.1._chunks.example.com TXT "base64chunk1..."
abc123.2._chunks.example.com TXT "base64chunk2..."
```

**Same-key elegance:**

When your WoT identity key = your DNSSEC signing key:

```
One key proves:
  - This WoT identity controls this domain
  - This domain publishes these thoughts
  - No ambiguity about authority

Domain = Identity = Key
```

**Tiered risk model for key reuse:**

| Content Type | Exposure | Key Reuse OK? |
|--------------|----------|---------------|
| Public schemas | Public | ✓ Yes |
| Identity bindings | Public assertions | ✓ Yes |
| Pool governance | Semi-public | ✓ Probably |
| Meta/discovery thoughts | Public | ✓ Yes |
| Personal thoughts | Private | ✗ No — derive separate key |

**Recommendation:** Same key for public meta-layer (schemas, bindings, discovery). Derived key for your actual thought graph.

```python
# Same entropy, separated by purpose
master = your_root_seed

public_meta_key = derive_key(master, "wot-public-meta-v1")  # DNS + DNSSEC
private_graph_key = derive_key(master, "wot-private-v1")    # Personal thoughts
```

This gives you the elegance of unified identity for public infrastructure, without risking your private graph if DNS provider is compromised.

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

### Revocation via DNS (Optional)

For identities bound to domains — fast global revocation. Not required; useful for disposable keys or lower-security contexts where convenience beats ceremony.

Lookup is deterministic per identity:

```
{cid_prefix}._revoked.example.com TXT "ts=1709251200 reason=compromised"
```

Where `cid_prefix` is first 16 chars of the identity CID (collision-resistant, DNS-safe).

**Example:**

Identity: `cid:blake3:5cecc66b61e356cef45f35f5e3da679e8d335d7e224c08cddd2f3b7c680e4393`

Revocation record:
```
5cecc66b61e356ce._revoked.example.com TXT "ts=1709251200 reason=key_compromised"
```

**Verification flow:**

```python
def check_revocation(identity_cid: str, domain: str) -> bool:
    prefix = identity_cid.split(':')[2][:16]  # First 16 hex chars
    record = f"{prefix}._revoked.{domain}"
    
    try:
        txt = dns_lookup_txt(record)
        if txt:
            return True  # Revoked
    except NXDOMAIN:
        pass  # No revocation record
    
    return False  # Not revoked
```

**When to use:**
- Disposable identities with short lifespans
- High-churn environments (CI bots, temp workers)
- When instant global revocation matters more than sovereignty

**When to skip:**
- High-security sovereign identities
- Identities not bound to DNS
- When you don't trust DNS infrastructure

Nested and neat — there if you want it, invisible if you don't.

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

## Part 11: Model Provenance

### The Problem

Current AI outputs have no verifiable attribution. The model claims "I'm Opus 4.5" with no cryptographic proof. Routing decisions, model swaps, and capability downgrades are invisible to the consumer.

### WoT Solution

Model identity as thought. Every response signed.

```
Response thought
  created_by: cid:blake3:model_identity
  source: cid:blake3:connection → uses_input → model/opus-4.5
  signature: ed25519 signed by model key

Verification:
  1. Check signature against known model identity pubkey
  2. Provider attests model identity (vouch chain)
  3. Mismatch = caught, auditable
```

### Trust Chain

```
Provider (e.g. Anthropic)
  → vouches → model_identity (opus-4.5)
    → signs → response_thought
      → because: [user_prompt, context]
      
User verifies:
  - Signature on response valid?
  - Model identity vouched by trusted provider?
  - Source matches claimed model?
```

### What This Enables

| Current | With WoT |
|---------|----------|
| "Trust me, I'm Opus" | Signed response, verifiable identity |
| Invisible model swaps | Mismatch detected cryptographically |
| No response provenance | Full because chain to prompt + context |
| Platform word is truth | Signature is truth |

The protocol designed to solve trust was stress-tested by the trust problem it solves: during spec development, model routing failures demonstrated the exact absence of provenance that WoT addresses.

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

*End of Integrations Specification v0.10*
