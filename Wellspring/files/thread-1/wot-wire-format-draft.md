# WoT Wire Format Specification

**Status:** Draft
**Thread:** 1 (RFC)
**Version:** 0.1
**Date:** 2026-01-31

---

## 1. Overview

This document specifies the wire format for WoT (Web of Thought) protocol messages. It covers:

1. CID (Content Identifier) computation
2. Thought serialization (canonical form)
3. Signature format
4. Packet header format

The goal is unambiguous interoperability: any conforming implementation MUST produce identical CIDs for identical content.

---

## 2. CID Computation

### 2.1 Hash Algorithm

**MUST** use BLAKE3 with a 32-byte (256-bit) output.

Rationale:
- Faster than SHA-256 on modern CPUs
- Verified security proofs
- Single algorithm (no length-extension attacks)
- Rust ecosystem has excellent support (`blake3` crate)

### 2.2 CID Format (Multiformat)

WoT uses IPFS-compatible CIDv1 for all content identifiers:

```
CID = <version><codec><multihash>
    = 0x01 (CIDv1) + 0x71 (dag-cbor) + 0x1e (blake3) + 0x20 (32 bytes) + <digest>

Total: 36 bytes
```

| Byte(s) | Value | Meaning |
|---------|-------|---------|
| 0 | `0x01` | CID version 1 |
| 1 | `0x71` | dag-cbor codec |
| 2 | `0x1e` | blake3 hash function |
| 3 | `0x20` | hash length (32 bytes) |
| 4-35 | varies | 32-byte BLAKE3 digest |

**Rationale:**
- Direct IPFS interop — thought CIDs and file CIDs share the same namespace
- A thought can `because: [ipfs_file_cid]` with no translation layer
- dag-cbor codec enables IPFS tooling to traverse links in content
- Local-first: daemon fetches from IPFS → indexes locally → fast queries

**Display encoding:**
- Base32lower (IPFS default): `bafyrei...`
- Base58btc (compact): `z...`
- Wire format: raw 36 bytes, no base encoding

### 2.3 Canonical Serialization

CID is computed over the canonical CBOR serialization of the **CID-relevant fields**:

```
CID = blake3(canonical_cbor(cid_input))
```

Where `cid_input` contains exactly these fields, in this order:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | YES | Thought type (e.g., "basic", "identity", "connection") |
| `content` | any | YES | Typed payload (structure depends on type) |
| `created_by` | bytes(36) | YES | CID of creator identity (or SELF_MARKER for identity thoughts) |
| `because` | array[bytes(36)] | YES | Array of CIDs (may be empty) |

**Excluded from CID computation:**
- `created_at` — mutable metadata, not content
- `signature` — computed over CID, can't be in CID
- `visibility` — local policy, not content identity

### 2.4 Canonical CBOR Rules

Following RFC 8949 (CBOR) deterministic encoding:

1. **Map keys**: Sorted lexicographically by UTF-8 bytes
2. **Integers**: Shortest form (no padding)
3. **Floats**: Prefer integer if exact (1.0 → 1)
4. **Strings**: UTF-8, NFC normalized
5. **Arrays**: Preserve order
6. **No indefinite-length**: All lengths explicit
7. **No tags**: Unless semantically required

### 2.5 Self-Referential Identity

For identity thoughts, `created_by` points to the thought itself (circular reference). Use the SELF_MARKER:

```
SELF_MARKER = bytes(36): 0x01 0x71 0x1e 0x20 + (0x00 * 32)
              (valid CID structure with zero digest)
```

During CID computation:
1. Set `created_by = SELF_MARKER`
2. Compute CID
3. Replace SELF_MARKER with computed CID in final thought

---

## 3. Test Vectors

### 3.1 Basic Thought

**Input (JSON representation):**

```json
{
  "type": "basic",
  "content": "Hello, WoT!",
  "created_by": "bafy...abc123",
  "because": []
}
```

**Canonical CBOR (hex):**

```
a4                                      # map(4)
   67                                   # text(7)
      626563617573                      # "because"
   80                                   # array(0)
   67                                   # text(7)
      636f6e74656e74                    # "content"
   6b                                   # text(11)
      48656c6c6f2c20576f5421            # "Hello, WoT!"
   6a                                   # text(10)
      637265617465645f6279              # "created_by"
   5820                                 # bytes(32)
      [32 bytes of creator CID]
   64                                   # text(4)
      74797065                          # "type"
   65                                   # text(5)
      6261736963                        # "basic"
```

**Expected CID (assuming creator CID is all 0x01):**

```
blake3 input (hex): a467626563617573658067636f6e74656e746b48656c6c6f2c20576f54216a637265617465645f62795820010101010101010101010101010101010101010101010101010101010101010164747970656562617369632

blake3 output: [TO BE COMPUTED BY REFERENCE IMPLEMENTATION]
```

### 3.2 Identity Thought (Self-Referential)

**Input:**

```json
{
  "type": "identity",
  "content": {
    "name": "Keif",
    "pubkey": "ed25519:abc123..."
  },
  "created_by": "SELF",
  "because": []
}
```

**Computation steps:**

1. Replace `created_by` with SELF_MARKER (32 zero bytes)
2. Canonicalize content map: `{"name": "Keif", "pubkey": "ed25519:abc123..."}`
3. Serialize to CBOR
4. Compute blake3 → CID
5. Store thought with `created_by = CID`

### 3.3 Connection Thought

**Input:**

```json
{
  "type": "connection",
  "content": {
    "from": "bafy...thought_a",
    "to": "bafy...thought_b",
    "relation": "supports"
  },
  "created_by": "bafy...keif_identity",
  "because": ["bafy...thought_a", "bafy...thought_b"]
}
```

**Note:** `content.from` and `content.to` are CID references stored as bytes(32).

### 3.4 Unicode Normalization

**Critical:** All strings MUST be NFC normalized before CBOR encoding.

**Input:**

```json
{
  "type": "basic",
  "content": "café",
  "created_by": "...",
  "because": []
}
```

Two representations of "café":
- Composed (NFC): `U+0063 U+0061 U+0066 U+00E9` (4 code points)
- Decomposed (NFD): `U+0063 U+0061 U+0066 U+0065 U+0301` (5 code points)

**MUST** use NFC form. Implementations receiving NFD MUST normalize to NFC before CID computation.

### 3.5 Empty Because Chain

**Input:**

```json
{
  "type": "basic",
  "content": "Ungrounded assertion",
  "created_by": "bafy...",
  "because": []
}
```

Empty array is valid. Represents a terminal node / ungrounded assertion.

### 3.6 Structured Content

**Input:**

```json
{
  "type": "attestation",
  "content": {
    "on": "bafy...target_thought",
    "weight": 0.8,
    "aspect": "bafy...aspect_cid"
  },
  "created_by": "bafy...",
  "because": ["bafy...target_thought"]
}
```

**Canonicalization of nested maps:** Keys sorted at each level.

---

## 4. Signature Format

### 4.1 Algorithm

**MUST** use Ed25519 (RFC 8032).

### 4.2 Sign What

Signature covers:
```
signature = ed25519_sign(private_key, CID)
```

Just the 32-byte CID. Not the content. The CID cryptographically commits to the content via the hash.

### 4.3 Encoding

Signature is 64 bytes: 32-byte R point + 32-byte S scalar.

Store as raw bytes. No additional framing in the thought structure.

---

## 5. Packet Format

### 5.1 Header (96 bytes fixed)

```
Offset  Size  Field              Alignment
------  ----  -----              ---------
0       4     Magic ("WLSP")     4-byte ✓
4       2     Version            2-byte ✓
6       2     Flags              2-byte ✓
8       40    Schema CID         8-byte ✓ (36 CID + 4 padding)
48      4     Payload Len        4-byte ✓
52      40    Trust Anchor       8-byte ✓ (36 CID + 4 padding)
92      1     Payload Type
93      1     Hop Count
94      2     Reserved

Total: 96 bytes (1.5 cache lines)
```

**Alignment rationale:**
- All multi-byte fields on natural boundaries
- CIDs padded to 40 bytes (next 8-byte multiple)
- Payload Len promoted to full u32 (no awkward 3-byte reads)
- 96 bytes leaves headroom for future fields in padding
- MTU impact: 1452 - 96 = 1356 bytes payload (plenty)

### 5.2 Field Definitions

| Field | Size | Description |
|-------|------|-------------|
| Magic | 4 bytes | `0x574C5350` ("WLSP" in ASCII) |
| Version | 2 bytes | Protocol version, network byte order. Current: `0x0001` |
| Flags | 2 bytes | Bit flags (see below) |
| Schema CID | 40 bytes | Multiformat CID (36) + 4 padding. Schema thought describing payload. |
| Payload Len | 4 bytes | Length of payload in bytes (u32, max 4 GiB) |
| Trust Anchor | 40 bytes | Multiformat CID (36) + 4 padding. Nearest repeater/checkpoint. |
| Payload Type | 1 byte | 0x00 = inline thought, 0x01 = CID reference |
| Hop Count | 1 byte | TTL counter, decremented at each relay |
| Reserved | 2 bytes | Future use, MUST be 0x0000 |

**Padding bytes:** The 4 padding bytes after each CID are reserved. Current implementations MUST write zeros. Future versions may use for per-CID flags.

### 5.3 Flags

```
Bits 0-1: Compression
  00 = none (uncompressed)
  01 = lz4  (handshake, control messages — latency-optimized)
  10 = zstd (thought payloads — ratio-optimized)
  11 = reserved

Bit 2: Encrypted (0 = plaintext, 1 = encrypted)
Bits 3-15: Reserved (MUST be 0)
```

**Compression guidance:**
- Handshake packets (identity proof, peering, bloom filters): lz4 for minimal latency
- Thought transfers: zstd for better compression, decode cost amortized locally

### 5.4 Payload

If `Payload Type = 0x00` (inline):
- Payload is canonical CBOR of full thought (including `created_at`, `visibility`, `signature`)

If `Payload Type = 0x01` (reference):
- Payload is 32-byte CID + optional location hints

### 5.5 Signature Trailer

After payload: 64-byte Ed25519 signature over (header + payload).

---

## 6. Identity and Discovery

### 6.1 Identity Keypair Collapse

A single ed25519 keypair encodes to multiple identity systems:

| System | Derivation | Example |
|--------|------------|---------|
| WoT Identity | CID of identity thought | `bafyrei...` |
| IPNS | Peer ID from pubkey | `/ipns/12D3Koo...` |
| Tor .onion | Pubkey → onion v3 address | `abc...xyz.onion` |
| TLS Client Cert | X.509 with ed25519 key | `CN=<pubkey-hash>` |
| IPv6 Client | Pubkey in address | `2001:db8::<pubkey-suffix>` |

One key. Five namespaces. No translation tables.

### 6.2 IPNS Publishing

Identities publish to IPNS for mutable, stable addressing:

```
/ipns/<peer-id>/identity  → current identity thought CID
/ipns/<peer-id>/trails    → index of published trails
/ipns/<peer-id>/pools     → pool membership list
```

Subscribers watch IPNS path for updates. No polling the full network.

### 6.3 DNSSEC Bootstrap (now.pub)

For human-readable discovery, WoT uses DNSSEC-signed DNS records:

```
keif.now.pub  TXT  "wot=bafyrei...abc123"
              TXT  "ipns=12D3KooW...xyz789"
              TXT  "onion=abc...xyz.onion"
```

**Flow:**
1. User claims `<name>.now.pub` subdomain
2. now.pub verifies identity signature
3. DNS records published with DNSSEC
4. Anyone can resolve `keif.now.pub` → WoT identity CID

**Properties:**
- Censorable (DNS can be blocked)
- But easily located (memorable names)
- Fallback: .onion and IPNS paths are uncensorable
- DNSSEC proves now.pub signed the records

**now.pub as WoT Peer:**
- Runs WoT daemon
- Accepts identity publication requests
- Issues subdomain attestations
- Bootstrap node for new clients

### 6.4 Discovery Priority

When resolving a human name to identity:

1. **Local cache** — already known?
2. **DNSSEC lookup** — `<name>.now.pub` TXT records
3. **IPNS resolve** — if IPNS path known
4. **Tor .onion** — if onion address known
5. **Gossip query** — ask trusted peers

Each path independently verifies: the identity thought is self-signed, CID matches content.

### 6.5 FIDO2/Passkey Support (Future)

WoT identities can use hardware-bound FIDO2 keys for signing:

```
IDENTITY THOUGHT (passkey-backed)
  type: "identity"
  content: {
    name: "Keif"
    pubkey: "ecdsa-p256:..."      // FIDO2 uses P-256
    signing_method: "fido2"        // Indicates hardware-bound
    authenticator_aaguid: "..."    // Optional: device type
  }
```

**Key differences from standard ed25519:**

| Aspect | Ed25519 | FIDO2/Passkey |
|--------|---------|---------------|
| Curve | Ed25519 | ECDSA P-256 |
| Key storage | Software (exportable) | Hardware (unextractable) |
| Auth UX | Signature only | Biometric + touch |
| Backup | Export/import | Device-bound or synced passkey |

**Verification events as thoughts:**

Each hardware authentication creates a verification thought:

```json
{
  "type": "verification",
  "content": {
    "identity_cid": "<my identity>",
    "method": "fido2",
    "authenticator": "yubikey-5",
    "timestamp": 1738351200000,
    "challenge_hash": "<hash of what was signed>"
  },
  "created_by": "<my identity>",
  "because": ["<thought requiring verification>"],
  "visibility": "local_forever"
}
```

**Use cases:**
- Audit trail: "I proved I had the hardware key at this time"
- High-value actions: Require fresh verification thought before signing
- Compliance: Log all hardware auth events
- Recovery: Prove device possession history

**Hybrid mode:**

An identity can support both:
```json
{
  "type": "identity",
  "content": {
    "name": "Keif",
    "primary_key": "ed25519:...",           // Software key for routine signing
    "hardware_key": "ecdsa-p256:...",       // FIDO2 for high-value ops
    "require_hardware_for": ["chain_access_revoke", "identity_update"]
  }
}
```

**Compatibility with SSH.id pattern:**
- Handle discovery: `keif.now.pub` (like `keif.sshid.io`)
- Hardware verification: FIDO2/WebAuthn
- But WoT adds: attestation graph, trust chains, because trails

---

## 7. Key Lifecycle

### 7.1 Primary Protection: Device Pools

Most users will never need key recovery because their private device pool provides automatic key sync:

```
DEVICE POOL: "keif-devices"
  members: [laptop, phone, tablet, desktop]
  purpose: sync identity across devices
  visibility: local_forever (never leaves devices)

  key_sync_strategy:
    - New device added via existing device attestation
    - Key material encrypted to new device pubkey
    - All devices hold same signing key
    - Any device can sign thoughts
```

**Protection level:** Losing ALL devices simultaneously (house fire + phone in pocket) is the failure mode. Rare enough that explicit backup is optional for most users.

### 7.2 Backup Options

#### BIP39-Style Mnemonic

Standard 12/24 word seed phrase:

```
abandon ability able about above absent absorb abstract absurd abuse access accident
```

**Properties:**
- Deterministic: seed → keypair is repeatable
- Offline: write on paper, stamp in metal
- Standard: compatible with existing hardware wallets
- User responsibility: if you lose the paper, you lose the key

#### Pre-Signed Delegation

Sign a "break glass" thought in advance:

```json
{
  "type": "key_delegation",
  "content": {
    "new_pubkey": "ed25519:...",  // Generate now, store offline
    "valid_after": "2026-01-01",  // Future date
    "reason": "emergency_recovery"
  },
  "visibility": "local_forever"  // Don't publish until needed
}
```

**Usage:** If primary key compromised, publish pre-signed delegation. Proves you had original key when you created it.

### 7.3 Key Rotation Ceremony

Planned key upgrade (security hygiene, algorithm migration):

```
KEY ROTATION FLOW:

1. Create new keypair (K2)

2. Create key_rotation thought signed by OLD key (K1):
   {
     "type": "key_rotation",
     "content": {
       "old_key": "ed25519:K1...",
       "new_key": "ed25519:K2...",
       "reason": "scheduled_rotation",
       "effective_at": timestamp
     },
     "created_by": identity_cid,
     "signature": sign(K1, cid)
   }

3. Publish to pools

4. New thoughts signed by K2

5. Old thoughts still valid (signature verifies with K1)
```

**Smooth transition:** Both keys work during overlap period. Peers update their view of your identity.

### 7.4 Vouch Decay and Refresh

Vouches created at first peering. Pool config defines lifetime:

```yaml
pool_config:
  vouch_lifetime: "365d"     # Pool-specific setting
  vouch_decay: "linear"      # linear | exponential | step
  refresh_prompt_at: "30d"   # Days before expiry to prompt
  zero_at: "730d"            # When trust reaches 0 (optional)
```

**Decay behavior:**

```
Day 0:   Vouch created, weight = 1.0
Day 335: Daemon surfaces "Vouch for Alice expires in 30 days"
Day 365: Vouch expires unless refreshed
Day 730: Trust weight = 0 (if zero_at configured)

Refresh:
  - Out-of-band challenge (share code via Signal, email, in-person)
  - New vouch thought referencing original
  - Resets decay clock
```

**Content vs relationship trust:** Old thoughts remain valid forever (signature proves creation). Vouch freshness only affects current trust weight for new evaluations.

### 7.5 Identity Migration (Key Truly Lost)

When key is lost with no backup:

```
MIGRATION FLOW:

1. Create new identity (K2, new CID)

2. K2 creates SAME_AS claim (proves nothing alone):
   {
     "type": "same_as",
     "content": {
       "old_identity": "cid:...",
       "new_identity": "cid:...",
       "reason": "key_loss_no_backup"
     }
   }

3. People who vouched for K1 must re-vouch for K2:
   - "I verified K2 is the same person as K1"
   - Verification method recorded: "video_call", "in_person", "shared_secret"

4. Trust rebuilds through re-attestation
   - Old content stays with old key
   - New identity starts fresh-ish (vouches help bootstrap)
   - Not automatic — earns back trust
```

**This is supposed to be painful.** It incentivizes backup hygiene.

### 7.6 now.pub Key Custody (Optional Service)

For users who want insurance:

```
KEY CUSTODY FLOW:

1. User generates keypair locally

2. User encrypts key to now.pub custody pubkey

3. User submits encrypted blob (now.pub can't read without user auth)

4. Recovery:
   - User contacts now.pub
   - Identity verification (video call, government ID, security questions)
   - now.pub decrypts and returns key
   - OR: now.pub signs SAME_AS to user's new key on their behalf
```

**Tradeoffs:**

| Aspect | Self-Custody | now.pub Custody |
|--------|--------------|-----------------|
| Sovereignty | Full | Delegated to now.pub |
| Recovery | Your problem | now.pub verifies, returns |
| Trust model | Trust yourself | Trust Anthropic won't rug |
| Cost | Free | Paid tier |

**Not for everyone.** Power users self-custody. Convenience users pay for insurance.

### 7.7 Identity Hierarchy

Root identity never touches pools. It only vouches for scoped sub-identities:

```
ROOT IDENTITY (local_forever — device pool only)
  │
  ├── vouches → alice@work       (visibility: pool:work)
  ├── vouches → alice@social     (visibility: pool:social)
  ├── vouches → alice-bot@agents (visibility: pool:agents)
  └── vouches → alice@now.pub    (visibility: public)
```

**Sub-identity thought:**

```json
{
  "type": "identity",
  "content": {
    "name": "alice@work",
    "pubkey": "ed25519:...",
    "parent": "cid:root_identity",
    "scope": "pool:work",
    "delegated_permissions": ["attest", "connect", "publish"]
  },
  "created_by": "cid:root_identity",
  "visibility": "pool:work"
}
```

**Why this matters:**

| Concern | Root-in-pool | Root-never-in-pool |
|---------|--------------|---------------------|
| Attack surface | Your identity | A scoped delegate |
| Compromise impact | Existential | Revoke + replace |
| Recovery | Social attestation | Root issues new sub |
| Complexity | High (2-of-3 attacks) | Low (just revoke) |

**Protection spectrum:**

| User type | Root key storage | Sub-identity usage |
|-----------|------------------|-------------------|
| Paranoid | Paper in safe, hardware wallet | All pool activity |
| Security-conscious | Hardware key (YubiKey) | Daily operations |
| Normal | Device pool (auto-sync) | May not even know |
| Casual | Device pool | "It just works" |

**Pool verification:**

Pools can require proof of root backing:

```yaml
pool_rules:
  require_root_attestation: true   # Sub-identity must have vouch from root
  max_delegation_depth: 2          # No sub-sub-sub-identities
  accepted_scopes: ["work", "bot"] # Only these scope claims accepted
```

### 7.8 Key Lifecycle Summary

| Scenario | Primary Protection | Fallback |
|----------|-------------------|----------|
| Normal use | Device pool sync | N/A |
| Single device loss | Other devices still work | Re-add device |
| All devices lost | BIP39 backup | now.pub custody |
| Key compromised | Immediate rotation + revocation | Pre-signed delegation |
| Key truly gone, no backup | Identity migration | Rebuild trust manually |

---

## 8. Conformance Requirements

### 8.1 MUST

- Use BLAKE3-256 for CID computation
- Use canonical CBOR encoding (deterministic)
- NFC normalize all strings before encoding
- Use Ed25519 for signatures
- Include all required fields in CID computation
- Verify signature before processing payload

### 8.2 SHOULD

- Cache parsed schemas by CID
- Validate payload against schema before processing
- Preserve hop count semantics during relay

### 8.3 MAY

- Use compression (zstd) for payloads > 256 bytes
- Use encryption for private pool traffic
- Support alternative hash functions in future versions

---

## 9. Reference Implementation

See `wellspring_core.py` for Python reference:

```python
import cbor2
import hashlib
from blake3 import blake3
import unicodedata

def normalize_string(s: str) -> str:
    """NFC normalize a string."""
    return unicodedata.normalize('NFC', s)

def canonical_cbor(obj) -> bytes:
    """Produce deterministic CBOR."""
    # cbor2 with canonical=True handles key sorting
    return cbor2.dumps(obj, canonical=True)

def compute_cid(thought: dict) -> bytes:
    """Compute CID for a thought."""
    # Extract CID-relevant fields only
    cid_input = {
        "type": thought["type"],
        "content": thought["content"],
        "created_by": thought["created_by"],  # bytes(32) or SELF_MARKER
        "because": thought["because"],  # list of bytes(32)
    }

    # Normalize any strings in content
    cid_input = normalize_content(cid_input)

    # Canonical CBOR
    cbor_bytes = canonical_cbor(cid_input)

    # BLAKE3 hash
    return blake3(cbor_bytes).digest()

def normalize_content(obj):
    """Recursively NFC normalize strings."""
    if isinstance(obj, str):
        return normalize_string(obj)
    elif isinstance(obj, dict):
        return {k: normalize_content(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_content(v) for v in obj]
    return obj
```

---

## 10. Open Questions

1. ~~**CID format prefix**~~: RESOLVED — using full multiformat CID (36 bytes)

2. ~~**Schema CID**~~: RESOLVED — 36 bytes is core value, not overhead. Enables self-describing thoughts, schema versioning, reader selection. Schemas are attestable thoughts.

3. ~~**Compression algorithm**~~: RESOLVED — lz4 for handshake/control (latency), zstd for thoughts (ratio). Decode cost is negligible on modern hardware, even phones.

4. ~~**Timestamp precision**~~: RESOLVED — `created_at` is int64 (8 bytes). Unit defined by schema field `timestamp_unit`: `s` | `ms` | `us` | `ns`. Default `ms` if unspecified.

---

## 11. Next Steps

1. Implement reference CID computation in Python
2. Generate test vectors with known inputs/outputs
3. Implement in Rust for `libwellspring`
4. Cross-validate Python ↔ Rust outputs
5. Document edge cases discovered during implementation

---

## Appendix A: CBOR Type Mappings

| WoT Type | CBOR Major Type |
|----------|-----------------|
| string | 3 (text string) |
| bytes (CID, signature) | 2 (byte string) |
| integer | 0 or 1 (unsigned/negative) |
| float | 7 (special: float32/64) |
| array | 4 (array) |
| map | 5 (map) |
| null | 7.22 (simple: null) |
| boolean | 7.20/7.21 (simple: false/true) |

---

## Appendix B: Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-01-31 | Initial draft |
