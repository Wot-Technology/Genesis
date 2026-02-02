# WoT Core Schemas

**Status:** Draft
**Thread:** 1 (RFC)
**Version:** 0.1

---

## Schema Hierarchy

```
                          ┌──────────┐
                          │  schema  │ (meta: schema for schemas)
                          └────┬─────┘
                               │
       ┌───────────┬───────────┼───────────┬───────────┐
       ▼           ▼           ▼           ▼           ▼
   ┌───────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │ basic │  │identity│  │  pool  │  │connect-│  │attest- │
   │       │  │        │  │        │  │  ion   │  │ ation  │
   └───────┘  └────────┘  └────┬───┘  └────────┘  └────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
         ┌─────────┐     ┌──────────┐     ┌──────────┐
         │  intro  │     │pool_rules│     │membership│
         └─────────┘     └──────────┘     └────┬─────┘
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                              ┌──────────┐ ┌───────┐ ┌────────┐
                              │expectation│ │member│ │peering │
                              └──────────┘ └───────┘ └────────┘
```

---

## 1. Pool Schema

Defines a pool — a scoped collaboration space.

```json
{
  "schema": "pool",
  "version": "1.0.0",
  "fields": {
    "name": {
      "type": "string",
      "required": true,
      "description": "Human-readable pool name"
    },
    "description": {
      "type": "string",
      "required": false
    },
    "join_policy": {
      "type": "enum",
      "values": ["open", "expected_only", "invite_only", "attested"],
      "required": true,
      "description": "Who can join without pre-authorization"
    },
    "sync_policy": {
      "type": "enum",
      "values": ["full", "filtered", "intro_only"],
      "required": true,
      "description": "Default sync behavior for new peers"
    },
    "rules_cid": {
      "type": "cid",
      "required": false,
      "description": "CID of pool_rules thought (if any)"
    },
    "intro_cid": {
      "type": "cid",
      "required": false,
      "description": "CID of intro thought (public-facing)"
    }
  }
}
```

**Join policies:**

| Policy | Behavior |
|--------|----------|
| `open` | Anyone can join, no expectation required |
| `expected_only` | Must have expectation thought pre-created |
| `invite_only` | Must have invite signed by existing member |
| `attested` | Must have attestation from N existing members |

---

## 2. Intro Schema

Public-facing pool introduction. Discoverable, leads to pool details.

```json
{
  "schema": "intro",
  "version": "1.0.0",
  "fields": {
    "pool_cid": {
      "type": "cid",
      "required": true,
      "description": "The pool this introduces"
    },
    "title": {
      "type": "string",
      "required": true,
      "description": "One-line description"
    },
    "summary": {
      "type": "string",
      "required": false,
      "description": "Longer description for discovery"
    },
    "topics": {
      "type": "array[string]",
      "required": false,
      "description": "Searchable topic tags"
    },
    "contact": {
      "type": "cid",
      "required": false,
      "description": "Identity CID for inquiries"
    }
  }
}
```

**Visibility:** Typically `null` (public) so it can propagate for discovery.

---

## 3. Pool Rules Schema

Defines what the pool accepts. Daemons use this to filter incoming thoughts.

```json
{
  "schema": "pool_rules",
  "version": "1.0.0",
  "fields": {
    "pool_cid": {
      "type": "cid",
      "required": true
    },
    "accept_schemas": {
      "type": "array[cid]",
      "required": false,
      "description": "Whitelist of accepted schema CIDs (null = any)"
    },
    "reject_schemas": {
      "type": "array[cid]",
      "required": false,
      "description": "Blacklist of rejected schema CIDs"
    },
    "max_payload_bytes": {
      "type": "integer",
      "required": false,
      "description": "Maximum thought payload size"
    },
    "require_because": {
      "type": "boolean",
      "required": false,
      "default": false,
      "description": "Reject ungrounded thoughts (empty because)"
    },
    "attestation_threshold": {
      "type": "float",
      "range": [0, 1],
      "required": false,
      "description": "Minimum trust weight to accept thought"
    },
    "rate_limit": {
      "type": "object",
      "fields": {
        "thoughts_per_hour": "integer",
        "bytes_per_hour": "integer"
      },
      "required": false
    },
    "timestamp_unit": {
      "type": "enum",
      "values": ["s", "ms", "us", "ns"],
      "default": "ms",
      "description": "Precision for created_at in this pool"
    },
    "auto_annotate": {
      "type": "array[string]",
      "values": ["summarize", "extract_links", "detect_language"],
      "required": false,
      "description": "Daemon annotations to auto-generate on receipt"
    }
  }
}
```

---

## 4. Expectation Schema

Pre-authorizes a future connection. "We expect to hear from this identity."

```json
{
  "schema": "expectation",
  "version": "1.0.0",
  "fields": {
    "pool_cid": {
      "type": "cid",
      "required": true,
      "description": "Pool this expectation applies to"
    },
    "expected_identity": {
      "type": "cid",
      "required": false,
      "description": "Specific identity CID (null = any)"
    },
    "expected_referrer": {
      "type": "cid",
      "required": false,
      "description": "Must reference this thought in because chain"
    },
    "expires_at": {
      "type": "integer",
      "required": false,
      "description": "Timestamp after which expectation invalid"
    },
    "max_uses": {
      "type": "integer",
      "required": false,
      "default": 1,
      "description": "How many times this expectation can be consumed"
    },
    "grant_chain_access": {
      "type": "array[cid]",
      "required": false,
      "description": "Chain roots to grant access to on join (null = pool-wide)"
    }
  }
}
```

**Use cases:**
- Share pool with specific person: `expected_identity = their CID`
- Publish invite link: `expected_referrer = invite_thought_cid`
- Open window: `expires_at = now + 1 hour, max_uses = 10`

---

## 5. Member Schema

Attested pool membership. Grants sync access, not surfacing.

```json
{
  "schema": "member",
  "version": "1.0.0",
  "fields": {
    "pool_cid": {
      "type": "cid",
      "required": true
    },
    "identity_cid": {
      "type": "cid",
      "required": true
    },
    "joined_at": {
      "type": "integer",
      "required": true
    },
    "invited_by": {
      "type": "cid",
      "required": false,
      "description": "Identity who sponsored membership"
    }
  }
}
```

**Note:** No role field. Roles are aspects, granted separately via aspect_grant thoughts.

**Membership grants sync, not surfacing:** You receive raw thoughts, but visibility is controlled by connections and aspects.

---

## 5a. Chain Access Schema

The one control primitive: can this identity attach to this chain?

```json
{
  "schema": "chain_access",
  "version": "1.0.0",
  "fields": {
    "chain_root": {
      "type": "cid",
      "required": true,
      "description": "Root thought of the chain"
    },
    "identity_cid": {
      "type": "cid",
      "required": true,
      "description": "Who can attach"
    },
    "pool_cid": {
      "type": "cid",
      "required": true,
      "description": "Pool context"
    },
    "expires_at": {
      "type": "integer",
      "required": false
    }
  },
  "because": ["chain_root", "identity_cid"]
}
```

**The simple model:**

```
POOL MEMBERSHIP    → you have the thoughts (sync)
CONNECTIONS        → organize into logical structures (surfacing)
CHAIN ACCESS       → can you add to this chain? (the ONE permission)
```

**Reading is implicit:** If you're in the pool, you have the data. No separate "read" permission.

**Attaching rule:**
```
can_attach(new_thought, identity, target_chain):
  1. Is identity a pool member? (has the data)
  2. Is there a chain_access thought granting identity access to target_chain?
  3. If yes → allow. If no → reject.
```

**Chain access can be granted by:**
- Pool admin (pool-wide grant authority)
- Chain owner (creator of chain_root)
- Anyone with existing chain_access (delegation from their grant point forward)

---

## 5b. Chain Access Revoke Schema

Revokes a previous chain_access grant. On chain, timestamped.

```json
{
  "schema": "chain_access_revoke",
  "version": "1.0.0",
  "fields": {
    "revokes": {
      "type": "cid",
      "required": true,
      "description": "CID of the chain_access thought being revoked"
    },
    "reason": {
      "type": "string",
      "required": false
    },
    "effective_at": {
      "type": "integer",
      "required": true,
      "description": "Timestamp when revocation takes effect"
    }
  },
  "because": ["revokes"]
}
```

**Revocation semantics:**
- Must be signed by someone who could have granted the original access
- Creates auditable record: when, why, by whom
- Downstream grants from revoked identity also invalidated
- Thoughts already synced remain in storage; surfacing stops

---

## 6. Peering Schema

Active peer relationship for sync.

```json
{
  "schema": "peering",
  "version": "1.0.0",
  "fields": {
    "local_identity": {
      "type": "cid",
      "required": true
    },
    "remote_identity": {
      "type": "cid",
      "required": true
    },
    "shared_pools": {
      "type": "array[cid]",
      "required": true,
      "description": "Pools we agree to sync"
    },
    "transfer_config": {
      "type": "object",
      "fields": {
        "inbound_rate": "integer",
        "outbound_rate": "integer",
        "priority": { "type": "enum", "values": ["low", "medium", "high"] },
        "trust_relay": "boolean"
      }
    },
    "established_at": {
      "type": "integer",
      "required": true
    }
  }
}
```

**Bilateral:** Both sides create a peering thought. Sync happens when both attest.

---

## 7. Sync Filter Schema (Optional)

Fine-grained sync filtering. By default, pool membership syncs all pool thoughts. Use sync_filter to restrict.

```json
{
  "schema": "sync_filter",
  "version": "1.0.0",
  "fields": {
    "pool_cid": {
      "type": "cid",
      "required": true
    },
    "identity_cid": {
      "type": "cid",
      "required": true,
      "description": "Member whose sync is filtered"
    },
    "include_chains": {
      "type": "array[cid]",
      "required": false,
      "description": "Only sync these chains (whitelist)"
    },
    "exclude_chains": {
      "type": "array[cid]",
      "required": false,
      "description": "Don't sync these chains (blacklist)"
    },
    "include_schemas": {
      "type": "array[cid]",
      "required": false
    },
    "exclude_schemas": {
      "type": "array[cid]",
      "required": false
    }
  }
}
```

**Note:** Sync filter controls data transfer. Surfacing is controlled by aspect_grant.

**Typical use:** Low-bandwidth peer wants only certain chains. Or sensitive chain excluded from general sync.

---

## 8. Join Request Schema

Handshake initiation. "I want to join this pool."

```json
{
  "schema": "join_request",
  "version": "1.0.0",
  "fields": {
    "pool_cid": {
      "type": "cid",
      "required": true
    },
    "requester_identity": {
      "type": "cid",
      "required": true
    },
    "referrer": {
      "type": "cid",
      "required": false,
      "description": "Thought CID that led here (for expectation matching)"
    },
    "requested_chains": {
      "type": "array[cid]",
      "required": false,
      "description": "Specific chains requesting access to (null = general membership)"
    },
    "introduction": {
      "type": "string",
      "required": false,
      "description": "Why I want to join"
    }
  }
}
```

---

## 9. Annotation Schema

Daemon-generated metadata attached to received thoughts.

```json
{
  "schema": "annotation",
  "version": "1.0.0",
  "fields": {
    "target_cid": {
      "type": "cid",
      "required": true,
      "description": "Thought being annotated"
    },
    "annotation_type": {
      "type": "enum",
      "values": [
        "summary",
        "warning",
        "quarantine",
        "translation",
        "extract_links",
        "detect_language",
        "sentiment",
        "verified",
        "rejected"
      ],
      "required": true
    },
    "content": {
      "type": "any",
      "required": true,
      "description": "Annotation payload (structure depends on type)"
    },
    "confidence": {
      "type": "float",
      "range": [0, 1],
      "required": false,
      "description": "For AI-generated annotations"
    },
    "model": {
      "type": "string",
      "required": false,
      "description": "Model that generated this (e.g., 'claude-3-opus')"
    }
  }
}
```

**Visibility:** Usually `local_forever` — your daemon's notes, not synced.

**Annotation types:**

| Type | Content | Use |
|------|---------|-----|
| `summary` | string | AI-generated TL;DR |
| `warning` | { level, reason } | Content flags |
| `quarantine` | { reason, until } | Pending verification |
| `translation` | { lang, text } | Auto-translate |
| `extract_links` | array[cid] | CIDs referenced in content |
| `verified` | { method, result } | Signature/content verification passed |
| `rejected` | { reason } | Failed pool rules, logged why |
| `appetite_note` | { status, details } | Your appetite/trust disposition |

---

## 9a. Appetite Note Schema

Local-only notes about your disposition toward received thoughts. Not rejection — just your private assessment.

```json
{
  "schema": "appetite_note",
  "version": "1.0.0",
  "fields": {
    "target_cid": {
      "type": "cid",
      "required": true,
      "description": "Thought this note is about"
    },
    "status": {
      "type": "enum",
      "values": [
        "unauthorized_claim",
        "unverified_source",
        "low_trust_path",
        "pending_attestation",
        "welcomed",
        "flagged"
      ],
      "required": true
    },
    "details": {
      "type": "object",
      "required": false,
      "description": "Status-specific context"
    }
  },
  "visibility": "local_forever"
}
```

**Status meanings:**

| Status | Meaning |
|--------|---------|
| `unauthorized_claim` | Claims to attach to chain but no chain_access found |
| `unverified_source` | Identity signature valid but unknown to us |
| `low_trust_path` | Trust score below our threshold |
| `pending_attestation` | Waiting for more attestations before surfacing |
| `welcomed` | Matches our appetite, actively surfaced |
| `flagged` | Manual flag by user for review |

**Key principle:** We don't reject thoughts — we annotate our appetite privately. Someone else's view might be different if they have chain_access grants we don't see.

---

## 9b. Verification Schema

Records hardware/biometric authentication events. Audit trail for high-security actions.

```json
{
  "schema": "verification",
  "version": "1.0.0",
  "fields": {
    "identity_cid": {
      "type": "cid",
      "required": true,
      "description": "Identity that was verified"
    },
    "method": {
      "type": "enum",
      "values": ["fido2", "passkey", "totp", "sms", "email", "biometric"],
      "required": true
    },
    "authenticator": {
      "type": "string",
      "required": false,
      "description": "Device/method identifier (e.g., 'yubikey-5', 'face-id')"
    },
    "challenge_hash": {
      "type": "bytes",
      "required": false,
      "description": "Hash of the challenge that was signed"
    },
    "action_context": {
      "type": "cid",
      "required": false,
      "description": "Thought CID that triggered verification requirement"
    }
  },
  "visibility": "local_forever"
}
```

**Use cases:**
- Audit trail: "I proved hardware possession at this time"
- High-value gating: Require fresh verification before signing certain thoughts
- Compliance: Log all hardware auth events
- Recovery proof: Demonstrate device possession history

**Hybrid identity support:**

```json
{
  "type": "identity",
  "content": {
    "name": "Keif",
    "primary_key": "ed25519:...",
    "hardware_key": "ecdsa-p256:...",
    "require_hardware_for": ["chain_access_revoke", "identity_update", "high_value_attestation"]
  }
}
```

Routine signing uses ed25519 (fast, software). High-value ops require fresh FIDO2 verification thought.

---

## Handshake Protocol

### Sequence

```
INITIATOR                              RECEIVER
─────────                              ────────
1. Create join_request thought
   (pool_cid, my identity, referrer)
                    ────────────────►
                                       2. Receive join_request

                                       3. Check:
                                          - Is pool_cid valid?
                                          - Do we have expectation for this identity?
                                          - Or is join_policy open?
                                          - Does referrer match any expectation?

                                       4. If accepted:
                                          - Create member thought
                                          - Create peering thought
                                          - Create access_grant thought
                    ◄────────────────
5. Receive member + peering + access_grant

6. Create our peering thought
   (bilateral confirmation)
                    ────────────────►
                                       7. Receive peering confirmation

                                       8. Bilateral attestation complete
                                          Sync can begin

9. Exchange bloom filters
   (filtered by access_grant)
                    ◄──────────────►
                                       10. Delta sync
```

### Packet Types for Handshake

| Type | Compression | Purpose |
|------|-------------|---------|
| `HELLO` | lz4 | Initial contact, identity proof |
| `JOIN_REQ` | lz4 | Join request thought |
| `JOIN_ACK` | lz4 | Acceptance + member/peering/access thoughts |
| `JOIN_NAK` | lz4 | Rejection + reason |
| `PEER_CONFIRM` | lz4 | Bilateral peering confirmation |
| `BLOOM` | lz4 | Bloom filter exchange |
| `WANT` | lz4 | Request specific CIDs |
| `THOUGHT` | zstd | Actual thought payload |

---

## Daemon Decision Flow

```
INCOMING THOUGHT
      │
      ├─► 1. Signature valid?
      │      No  → HARD REJECT (only case we refuse to store)
      │      Yes → continue
      │
      ├─► 2. Store thought (we have the data now)
      │
      ├─► 3. Schema known?
      │      No  → fetch schema, queue annotation for retry
      │      Yes → continue
      │
      ├─► 4. Check chain_access (if thought claims to attach)
      │      Has access → appetite_note: welcomed
      │      No access  → appetite_note: unauthorized_claim
      │      Unknown    → appetite_note: pending_attestation
      │
      ├─► 5. Pool rules check
      │      Pass → continue
      │      Fail → appetite_note: flagged (but still stored)
      │
      ├─► 6. Trust threshold check
      │      Above → surface normally
      │      Below → appetite_note: low_trust_path (buffered)
      │
      ├─► 7. Auto-annotate (per pool_rules)
      │      - Generate summary
      │      - Extract links
      │      - Detect language
      │
      └─► 8. Index for queries
             Surfacing filtered by appetite_notes
```

**Key principle:** Only invalid signatures cause hard rejection. Everything else is stored but annotated. Your local view filters based on your appetite notes. Other pool members may see it differently.

---

## The Three Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  1. POOL MEMBERSHIP                                             │
│     You have the thoughts (sync)                                │
│     Raw data transfer between pool members                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. CONNECTIONS                                                 │
│     Organize into logical structures (surfacing)                │
│     How thoughts relate, what trails you follow                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. CHAIN ACCESS                                                │
│     Can you add to this chain? (the ONE permission)             │
│     chain_access thought grants attach rights                   │
└─────────────────────────────────────────────────────────────────┘
```

**Reading is implicit.** Pool membership = you have the data. No separate read permission.

**The only permission question:** Can I attach to this chain?

**Connections surface thoughts.** They organize the graph into navigable structures. The data is already there (synced). Connections make it visible and meaningful.

---

## Resolved Questions

1. ~~**Role hierarchy**~~: Simplified to one primitive: chain_access.

2. ~~**Expectation consumption**~~: No special handling. If someone claims to attach, we inspect the claim and can attest "not in our context." Everything is thoughts attached to thoughts.

3. ~~**Annotation attestation**~~: Yes, critical. This IS the core mechanism — people/agents propose thoughts, entities attest their aspects. Enables private chains within same pool, side-channel discussions about same items.

4. ~~**Revocation**~~: Another thought with reversed access. On chain, timestamped record of when revoked from surfacing/peering.

5. ~~**Delegation**~~: Yes, scoped to grant point. Once you have chain_access from point X, you can attest others from X forward (not earlier). May spawn downstream pool. Upstream gets threads; downstream only syncs CIDs in because chains they have access to.

---

## Delegation Model

```
UPSTREAM POOL (full access)
     │
     ├── thought_A ─── because ──→ ...
     │      │
     │      └── chain_access granted to Alice at thought_A
     │             │
     │             └── Alice can attest Bob from thought_A forward
     │                    │
     │                    └── Bob's access starts at thought_A
     │                           (no retroactive access to earlier chain)
     │
     └── thought_B ─── because ──→ thought_A ──→ ...
            │
            └── Bob can see thought_B (references thought_A in because)
                Bob cannot see sibling chains from before thought_A
```

**Downstream pool spawning:**
- Alice creates new pool for her delegates
- Upstream members get threads (sync continues)
- Downstream only syncs CIDs mentioned in because chains they can access
- Not "read everything down" — scoped by reference graph

---

## Next Steps

1. Define wire format for handshake packets (HELLO, JOIN_REQ, etc.)
2. Specify bloom filter parameters (size, hash count, false positive rate)
3. Define trust computation for attestation_threshold checks
4. Test vectors for handshake sequence
