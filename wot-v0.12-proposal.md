# Web of Thought (WoT) v0.12 Specification Proposal

**Protocol for Distributed Knowledge with Computable Trust**

*Draft: February 2026*

*Status: PROPOSAL — Under Review*

---

## Changelog from v0.11

This document captures proposed changes for v0.12. Each section references design decisions recorded as WoT thoughts.

### Summary of Changes

| Area | Change | Key CIDs |
|------|--------|----------|
| Protocol Identity | Reframe as routing + workflow + attention | 07c38a4, cd99997 |
| Trust Security | Ceiling invariant, identity hierarchy | e1072aa, b772e6e |
| Schema Additions | ContentRef, rework semantics, response patterns | d46398b |
| Peering | Agreements as thoughts, DNS discovery, port architecture | 0c4b6ea |
| Internal Agents | Roles, event-driven, processing paths, lifecycle | bf11c2e, 38e659b, 5332d64, f67d525 |
| Operational Schemas | Checkpoint, watermark, trace, marker, state_change | 664cf5a, 6ca0a70 |
| Context Injection | Boot thoughts, salience (open) | 13279cf |
| Security | P0 fixes done, fuller review post-spec | c9b4b48 |
| Geo-Pool Relays | Location-based discovery, WiFi-style overlap, marketplace | (new) |

---

## Part 1: Protocol Identity

### 1.1 The Three Innovations

WoT is not "just sync" or "just routing" or "just pub/sub." It provides three distinct innovations:

| Innovation | Naive Analogy | WoT Reality |
|------------|---------------|-------------|
| **Routing** | "It's BGP" | Routing with provenance — trust computed at every hop, attribution preserved |
| **Workflow** | "It's schemas" | Self-defining — thoughts describe how to process thoughts, workflows emerge from the graph |
| **Attention** | "It's pub/sub" | Queue methodology — waterlines, urgency, salience determine what surfaces to whom |

These compose but are conceptually separable.

### 1.2 Routing Reframe

| v0.11 Term | v0.12 Understanding |
|------------|---------------------|
| Pool | Routing boundary |
| published_to | Routes thought to boundary |
| Sync | Route execution |
| Membership | Routing permission |

**Key insight:** Adding a thought to a pool routes it to that boundary. Visibility depends on recipient's waterline, not just pool membership.

### 1.3 Dual Attribution

Every routed thought has two trust paths:

```
Thought.created_by       → Author (content attribution)
published_to.created_by  → Curator (routing attribution)
```

**Content trust:** Should I believe this?
**Routing trust:** Should I pay attention to this?

When Bob reshares Alice's thought:
- Alice remains author (content trust flows through her)
- Bob is curator (routing trust flows through him)
- Bob vouches for *relevance*, not *authorship*

Curator trust can boost content salience — if we trust Bob's curation, Alice's content surfaces higher.

---

## Part 2: Trust Security

### 2.1 Identity Hierarchy

Humans have multiple devices and agents. Identity hierarchy reflects this:

```
Root Identity (cold storage / 12-word recovery)
    │
    │ vouches (1.0)
    │
    ├── Device: laptop-home
    │       │ vouches
    │       └── Agent: claude-code
    │
    ├── Device: phone
    │       │ vouches
    │       └── Agent: mobile-assistant
    │
    └── Service: server-daemon
            │ vouches
            └── Agent: bookkeeper
```

**Device identity references root in `because`:**

```json
{
  "type": "identity",
  "content": {
    "name": "laptop-home",
    "public_key": "ed25519:...",
    "parent": "cid:root_identity"
  },
  "because": ["cid:root_identity"]
}
```

### 2.2 Trust Ceiling Invariant

**Hard invariant:** Direct root attestation can reach 1.0. Any transitivity MUST be < 1.0.

| Hops from Root | Maximum Trust |
|----------------|---------------|
| 0 (root signing) | 1.0 |
| 1 (device) | 0.8 |
| 2 (agent or cross-device) | 0.5 |
| 3+ | 0.25 ceiling |

**Consequence:** Your daemon NEVER reaches 1.0 trust. It operates on a device key (0.8 ceiling). Root is cold storage.

This is structural, not policy. The ceiling prevents trust chain manipulation and prompt injection attacks.

### 2.3 Root Revalidation

Root attestation is the "ceremony" for exceptional trust:

| Operation | Key Used | Max Trust |
|-----------|----------|-----------|
| Daily work | Device | 0.8 |
| Agent operations | Agent | 0.5 |
| Critical endorsement | Root | 1.0 |
| New device onboarding | Root | 1.0 |
| Revocation | Root | N/A |

**The ceremony matters.** Root attestation requires unlocking cold storage or entering seed phrase. The friction proves intent.

### 2.4 Attestation as Reputation Staking

Attestation weight is how much credibility you stake on something:

```
Effective trust = min(ceiling, vouches_received) × attestation_weight
```

**Not depletion, but risk:**
- Attest high on good content → credibility maintained
- Attest high on bad content → others de-vouch you
- Calibration matters — well-calibrated attesters build trust

### 2.5 Revocation Model

Revocation is a request, not a command:

1. Revocation thought signed by root
2. Peer responds: "will do" or "did do"
3. Response informs whether to continue peering
4. We log what we were told — receipts, not guarantees

Downstream trust collapses when parent revoked. Can't unsend, but can stop future routing.

### 2.6 Cross-Pool Trust Computation

Pools are trust boundaries. Trust policy is part of pool governance:

```json
{
  "type": "pool",
  "content": {
    "name": "team-alpha",
    "governance": "bilateral",
    "trust_policy": {
      "internal_ceiling": 0.8,
      "foreign_ceiling": 0.5,
      "trusted_pools": {
        "cid:partner-pool": 0.7,
        "cid:vendor-pool": 0.4
      },
      "inherit_trust": true
    }
  }
}
```

**Trust computation with pool boundaries:**

```
compute_trust(observer, target, context_pool):
    path = find_vouch_path(observer, target)
    raw = multiply(path.weights)
    hierarchy_ceiling = ceiling_for_hops(path.length)

    if target.pool != context_pool:
        pool_ceiling = context_pool.trust_policy.ceiling_for(target.pool)
    else:
        pool_ceiling = context_pool.trust_policy.internal_ceiling

    return min(raw, hierarchy_ceiling, pool_ceiling)
```

**Daemon auto-negotiation:** When peers connect, they exchange pool configs and negotiate trust ceiling. Default `foreign_ceiling: 0.5` is safe. Peering agreement captures negotiated value.

### 2.7 Pool Propagation Control

Pools control downstream propagation via fountain permission:

```json
{
  "type": "pool",
  "content": {
    "name": "vendor-sandbox",
    "trust_policy": {
      "fountain": false,
      "terminal": true
    }
  }
}
```

| Field | Meaning |
|-------|---------|
| `fountain: false` | Cannot spawn child pools |
| `terminal: true` | Content cannot be re-routed elsewhere |

**Terminology:**
- **Pool** — Collection boundary (basin)
- **Spring** — Origin pool (where thoughts first emerge)
- **Fountain** — Capability to spawn child pools (projection)

### 2.8 Transitive Neighbor Expectations

Set policy on neighbors' neighbors:

```json
{
  "type": "peering_agreement",
  "content": {
    "terms": {
      "trust_ceiling": 0.7,
      "transitive_expectation": {
        "your_neighbors_ceiling": 0.5,
        "max_depth": 2
      }
    }
  }
}
```

Meaning: "I trust you at 0.7, but I expect you to cap your downstream at 0.5, and content shouldn't propagate more than 2 hops from me."

**Enforcement:** Soft (violations detectable, bad actors de-vouched) and hard (daemon rejects policy violations).

### 2.9 Yggdrasil Governance

Yggdrasil is the bootstrap identity — signs core schemas forming the "first language."

**Current (pre-launch):** Single key, development iteration.

**Future (launch):** Multisig capable for foundation governance.

```json
{
  "type": "identity",
  "content": {
    "name": "yggdrasil",
    "public_keys": ["ed25519:aaa...", "ed25519:bbb...", "ed25519:ccc..."],
    "governance": "threshold:3/5"
  }
}
```

**Transition flow:** Old key signs handover → new trustees attest → governance: threshold:N/M. Trust chain unbroken.

Identity schema supports multisig without protocol changes. Yggdrasil is just an identity with special trust (bootstrap schemas).

---

## Part 3: Schema Additions

### 3.1 ContentRef — Pointing at Parts

```rust
struct ContentRef {
    thought_cid: Cid,                    // Required: which thought
    segment_cid: Option<Cid>,            // Machine-verifiable: hash of segment
    anchor: Option<TextSelector>,        // Human-recoverable: fuzzy match
    path: Option<String>,                // Structural: JSON Pointer, XPath
    temporal: Option<(f64, f64)>,        // Media: start_sec, end_sec
}

struct TextSelector {  // W3C Web Annotation style
    exact: String,
    prefix: Option<String>,
    suffix: Option<String>,
}
```

**Why both segment_cid AND anchor?**
- `segment_cid`: Cryptographic proof segment existed
- `anchor`: Human recovery fallback when content drifted

### 3.2 Rework Relation Semantics

Two distinct questions:
- `because`: WHY does this thought exist? (provenance)
- `rework`: WHAT did this thought replace? (edit history)

Rework is a connection:
```json
{
  "type": "connection",
  "content": { "from": "new_cid", "to": "old_cid", "relation": "rework" },
  "because": ["cid_of_reason_for_edit"]
}
```

Third-party reworks allowed. Attestations determine canonical version.

### 3.3 Response Schema Pattern

Response types defined by schema inheritance:

| Schema | Valid Responses |
|--------|-----------------|
| `response/attention` | seen, acted, denied, ignored |
| `response/review` | approved, changes_requested, commented |
| `response/invitation` | accepted, declined, tentative |
| `response/proposal` | endorsed, blocked, abstained |

New vocabularies emerge from schemas, not spec updates.

---

## Part 4: Peering & Discovery

### 4.1 Peering Agreements as Thoughts

Peering is negotiated, signed, attestable:

```json
{
  "type": "peering_agreement",
  "content": {
    "parties": ["cid:alice", "cid:bob"],
    "pools": ["cid:shared_pool"],
    "terms": {
      "max_thought_size": 1048576,
      "max_sync_batch": 1000,
      "schema_limits": { "basic": { "max_size": 65536 } },
      "backpressure_threshold": 0.8,
      "retention_days": 90
    }
  }
}
```

### 4.2 Negotiation Flow

```
1. HANDSHAKE
   Both peers present terms + ontology trails

2. NEGOTIATION CHAIN
   counter_1 → counter_2 → ... → final_terms
   Each step links via because

3. BILATERAL ATTESTATION
   Both attest final_terms
   OR disagreement → no peering

4. COMMS BUD OFF AGREEMENT
   All synced thoughts: because → agreement_cid
   Provenance traces back to negotiated terms
```

### 4.3 DNS Well-Known Discovery

```
_wot.example.com. TXT "v=wot1; id=cid:blake3:abc123; proto=https,onion; port=1729; data=1637"
```

| Field | Required | Description |
|-------|----------|-------------|
| `v` | Yes | Protocol version (wot1) |
| `id` | Yes | Identity CID |
| `proto` | Yes | Supported protocols (https, onion, libp2p, ws) |
| `port` | No | Config port (default: 1729) |
| `data` | No | Data port (default: same as port) |

### 4.4 Port Architecture

| Port | Reference | Purpose |
|------|-----------|---------|
| **1729** | Hardy-Ramanujan taxicab number | Peering, routing, peer discovery |
| **1637** | Descartes' *Discourse on the Method* | Thought transfer |

```bash
wot daemon                                  # 1729 unified
wot daemon --port 1729 --data-port 1637    # split mode
```

Split when topology needs it (bandwidth saturation, security boundaries, QoS).

---

## Part 5: Internal Agent Architecture

### 5.1 What Is An Agent

**An agent is a provenance wrapper around any processing.**

```
TRIGGER → PROCESS → RECORD
```

The processor is opaque. Could be LLM, Haystack, REST API, queue, shell script, WASM. Agent's responsibility:

1. **Input attribution:** What triggered this? (`because` chain)
2. **Output recording:** What came back? (new thought)
3. **Processor reference:** Who did the work? (`source`)

### 5.2 Agents Are Roles

Defined by three properties:

| Property | Mechanism |
|----------|-----------|
| **Scope** | Pool membership (what data agent sees) |
| **Authority** | Delegation attestations (what actions allowed) |
| **Tuning** | Config trail (how agent behaves) |

Same daemon runs multiple roles. Same data, different intents.

### 5.3 Agent Schema

```json
{
  "type": "agent",
  "content": {
    "name": "haystack-rag",
    "processor": {
      "type": "haystack",
      "endpoint": "http://haystack:8000/pipeline",
      "pipeline": "rag-v2"
    },
    "subscriptions": [
      { "pool": "cid:inbox", "trail": "cid:needs-rag" }
    ],
    "output_pool": "cid:processed",
    "config_trail": "cid:agent-config"
  }
}
```

### 5.4 Processor Types

| Type | Config | Example |
|------|--------|---------|
| `llm` | provider, model, prompt_trail | Claude, GPT, Llama |
| `haystack` | endpoint, pipeline | RAG, extraction |
| `http` | url, method, headers | Any REST API |
| `queue` | broker, topic | Kafka, RabbitMQ |
| `grpc` | service, method | Any gRPC |
| `shell` | command, env | Local scripts |
| `wasm` | module, function | Sandboxed compute |
| `internal` | handler_name | Built-in daemon |

### 5.5 Event-Driven Coordination

Agents don't poll. They subscribe:

```json
{
  "type": "subscription",
  "content": {
    "agent_identity": "cid:...",
    "pool_cid": "cid:...",
    "trail_cid": "cid:...",
    "callback_type": "internal"
  }
}
```

**Thought lands in pool + matches trail → agent fires.**

### 5.6 Three Processing Paths

| Path | When | Recording |
|------|------|-----------|
| **IMMEDIATE** | Interactive, user waiting | Records "bypassed pipeline" |
| **PIPELINE** | Background/batch | Full agent chain |
| **ENFORCED** | Sensitive pools | Pool denies immediate |

Recording is the point. Shortcuts are visible. Pool governance controls.

### 5.7 Agent Lifecycle

```
Event → Agent running?
         ├─ Yes → Process
         └─ No → Lazy start
                   ├─ Read config trail
                   ├─ Find checkpoint? → Resume
                   └─ No checkpoint → Fresh
```

### 5.8 Bookkeeper — First Agent Role

Instantiation of agent pattern for link curation:

**Scope:** Pools with orphaned thoughts
**Authority:** Propose connections (at its trust level)
**Tuning:** Inference signals, aspect references, thresholds

**Workflow:**
1. Orphan thought arrives
2. Bookkeeper analyzes (timestamps, sessions, similarity, aspects)
3. Proposes connection at its trust ceiling
4. Human attests → trust elevates
5. Attested link becomes canonical

Extends to aspect harvesting — personality management from agent chatter.

### 5.9 Plugin Distribution

Agents + schemas = natural plugin ecosystem:

```
plugin-pool: splunk-wot-connector
├── schema: splunk/event
├── schema: splunk/metric
├── agent-config: default-exporter
├── example: basic-setup
└── container: ghcr.io/splunk/wot-connector:v1
```

Install: sync pool, instantiate agent. No separate plugin system.

---

## Part 6: Operational Schemas

Well-known schemas reusable across any workflow:

### 6.1 Checkpoint

```json
{
  "type": "checkpoint",
  "content": {
    "agent": "cid:...",
    "cursor": {
      "thought_cid": "cid:...",
      "segment_cid": "cid:...",
      "anchor": { "exact": "..." }
    },
    "state": { },
    "resumable": true
  }
}
```

### 6.2 Watermark

```json
{
  "type": "watermark",
  "content": {
    "scope": "cid:pool_or_trail",
    "position": {
      "thought_cid": "cid:...",
      "segment_cid": "cid:..."
    },
    "timestamp": 1706972096000
  }
}
```

### 6.3 State Change

```json
{
  "type": "state_change",
  "content": {
    "subject": {
      "thought_cid": "cid:...",
      "path": "/content/status"
    },
    "from": "pending",
    "to": "processed",
    "trigger": "cid:..."
  },
  "because": ["cid:subject", "cid:trigger"]
}
```

### 6.4 Marker

```json
{
  "type": "marker",
  "content": {
    "trail": "cid:...",
    "label": "needs-review",
    "expires": 1706972096000
  }
}
```

### 6.5 Trace

```json
{
  "type": "trace",
  "content": {
    "text": "...",
    "category": "decision | observation | checkpoint | error",
    "session_id": "..."
  }
}
```

### 6.6 Audit Config

```json
{
  "type": "audit_config",
  "content": {
    "pool": "cid:...",
    "retention": "all | latest_only | time_bounded",
    "retention_days": 90,
    "prune_types": ["marker", "checkpoint"],
    "preserve_types": ["state_change", "trace"]
  }
}
```

All use ContentRef for precision. Segment_cid proves exact position; anchor recovers if drifted.

---

## Part 7: Context Injection

### 7.1 Attested Boot Thoughts

High-trust attested thoughts auto-inject at session start:

```
Human attests thought with via: "boot-context"
    │
    ▼
MCP startup queries: attestations WHERE via = "boot-context"
    │
    ▼
Inject into system prompt (weight → priority)
    │
    ▼
Assistant can't miss critical context
```

### 7.2 Daemon Is WoT-Native

Daemon operations ARE thoughts. Not separate logging.

```
Daemon event → Emit thought → Published to ops pool → Done
```

External export (Splunk, disk, etc.) = configure an agent. Enterprise integration is agent config, not daemon feature.

Agents track and attest their export activities — watermarks, completion attestations. Full provenance on the plumbing.

### 7.3 Salience Surfacing (OPEN)

**Needs prototyping.** Current signals:

| Signal | Contribution |
|--------|--------------|
| Trust (author) | Content credibility |
| Trust (curator) | Routing relevance |
| Urgency | request_attention × trust |
| Recency | Time decay |
| Aspect match | User preference alignment |
| Trail membership | Topic relevance |

**Open questions:**
- Threshold vs ranking?
- Pre-compute vs on-demand?
- Feedback loop?
- Agent vs human weights?

**v0.12:** Define hooks. **v0.13+:** Refine algorithms.

---

## Part 8: Security

### 8.1 P0 Fixes (Implemented)

| Fix | Status |
|-----|--------|
| Signature verification on receive | Done |
| Request body size limit (10MB) | Done |
| CID request limit (1000/sync) | Done |
| CORS whitelist (localhost) | Done |
| Path traversal fix | Done |

### 8.2 Post-Spec Security Review

| Area | Notes |
|------|-------|
| Trust ceiling enforcement | Spec defined, implement |
| Agent authority boundaries | Delegation verification |
| Pool permission enforcement | Read/write/invite checks |
| Peering agreement validation | Terms enforcement |
| Rate limiting per-identity | Beyond request limits |
| Encrypted content handling | Key management |

Full threat model and implementation checklist to follow.

---

## Part 9: Storage & Recovery

### 9.1 Storage Backend Abstraction

WoT storage is pluggable. Backends implement `ThoughtStorage` trait:

| Backend | Default | Use Case |
|---------|---------|----------|
| **MemVid** | Yes | Personal devices (single file, embedded search) |
| **RocksDB** | No | Scale/debugging fallback |
| **SQLite** | No | Archive recovery, legacy |
| **CosmosDB** | No | Cloud/multi-device (stub) |

**Backend selection requires attestation** when switching from default:

```json
{
  "type": "attestation_request",
  "content": {
    "action": "change_storage_backend",
    "from": "memvid",
    "to": "rocksdb",
    "requires": "user_attestation"
  }
}
```

### 9.2 Master Key & Unlock Chain

Encrypted thought stores require a master key. Unlock methods form a priority chain:

```
1. OS Keychain        → automatic (always enabled)
2. Environment var    → WOT_UNLOCK_KEY (attestation required)
3. Key file           → ~/.wot/master.key (attestation required)
4. WoT recovery       → decrypt from keys pool (interactive)
```

**Less-secure methods disabled by default.** Enabling requires attestation:

```json
{
  "type": "attestation",
  "content": {
    "on": "cid:attestation_request_for_env_var",
    "decision": "accept",
    "reason": "Required for CI pipeline"
  }
}
```

**Master key also stored as recovery thought:**

```json
{
  "type": "secret",
  "content": {
    "key_type": "master",
    "encrypted_to": "passphrase-derived-key",
    "ciphertext": "..."
  },
  "published_to": "keys"
}
```

The `keys` pool is local-only (never synced). Recovery passphrase displayed once at `wot init`.

### 9.3 Network Recovery (Identity Resurrection)

Identity is the anchor. Peers hold synced content. Fresh install rebuilds from network.

**Recovery flow:**

```
1. Fresh install (empty storage)
2. Import identity via recovery passphrase
3. Add known peers
4. Sign recovery_request (proves key ownership)
5. Peers push synced content
6. Local store rebuilds
```

**Recovery request:**

```json
{
  "type": "recovery_request",
  "content": {
    "identity": "cid:blake3:...",
    "requesting_pools": ["cid:pool1", "cid:pool2"],
    "attestation": {
      "claim": "identity_ownership",
      "timestamp": 1770218000000,
      "nonce": "fresh-random"
    }
  },
  "signature": "ed25519:..."
}
```

Peers validate signature → push data. Invalid signature → reject.

**Peer-side event:**

```json
{
  "type": "trace",
  "content": {
    "event": "identity_resurrection",
    "identity": "cid:...",
    "last_seen": 1770200000000,
    "thoughts_available": 12847
  }
}
```

### 9.4 Recovery Matrix

| Content | Recoverable? | Source |
|---------|--------------|--------|
| Pool thoughts | Yes | Peers with membership |
| Published thoughts | Yes | Any synced peer |
| Private thoughts | No | Local backup only |
| Secret keys | No | Recovery passphrase |
| Config | Partial | Defaults + peer prefs |

**Design principle:** Peers retain thoughts even if originator goes offline — they might return.

### 9.5 Reset Safety Checks

Destructive operations surface what will be lost:

```bash
wot reset --backend memvid

# ⚠️  This will delete all local thoughts (6318 total)
#
# Recoverable from network:
#   - 4201 thoughts in synced pools
#   - 847 thoughts peers have copies of
#
# NOT recoverable (local only):
#   - 1270 private thoughts
#   - Secret keys (ensure recovery passphrase saved)
#
# Export recovery bundle first? [Y/n]
```

**Safety checks establish missing local data before destructive operations.**

### 9.6 Recovery Bundle Schema

Pre-reset extraction for recovery:

```json
{
  "type": "recovery_bundle",
  "content": {
    "identity": {
      "cid": "cid:blake3:...",
      "name": "keif",
      "pubkey": "ed25519:..."
    },
    "peers": [
      { "cid": "cid:...", "name": "claude", "url": "http://localhost:7433" }
    ],
    "pools": [
      { "cid": "cid:...", "name": "wot-dev", "members": 3 }
    ],
    "thoughts_count": 6318,
    "last_sync": "2026-02-04T15:06:00Z",
    "root_attestation": { }
  }
}
```

**CLI commands:**

```bash
wot export-recovery          # Full bundle
wot export-recovery --qr     # QR for mobile
wot identity --export        # Just identity
wot attest-identity          # Fresh ownership proof
```

### 9.7 Attestation-Gated Configuration

Config changes with security implications require attestation:

| Config Change | Attestation Required |
|---------------|---------------------|
| Enable env var unlock | Yes |
| Enable key file unlock | Yes |
| Switch storage backend | Yes |
| Change trust ceilings | Yes |
| Add peer | No (but logged) |
| Change daemon port | No |

**Flow:**

```
User: wot config set unlock.env_var true
System: Creates attestation_request thought
Agent: Surfaces risk to user
User: Confirms (creates attestation thought)
System: Config applies, links to attestation CID
```

Attestation CID stored in config for audit trail.

---

## Part 10: Geo-Pool Relay System

### 10.1 Location-Based Discovery

Pools can describe geographic coordinates, enabling location-aware relay networks:

```json
{
  "type": "pool",
  "content": {
    "name": "london-central",
    "geo": {
      "lat": 51.5074,
      "lng": -0.1278,
      "radius_km": 5
    },
    "governance": "relay"
  }
}
```

**Key insight:** Geo-pools enable NAT-free, privacy-preserving peer discovery. Relays store nothing — just forward between interested parties who agree on incoming trust rules.

### 10.2 Hierarchical Overlap (WiFi Model)

Geo-pools overlap like WiFi cells for seamless roaming:

```
Global
├── Continental (~6 pools)
│   ├── Regional (~50 per continent)
│   │   ├── Metro (city-sized, ~30% edge overlap)
│   │   │   └── Neighborhood (dense urban, highly overlapping)
```

**Design principles:**
- Adjacent pools share ~30% coverage area
- Devices subscribe to 2-3 overlapping pools simultaneously
- Graceful handoff as you drift between coverage areas
- Never dependent on a single relay

### 10.3 Multiple SSIDs Per Area

Different "networks" in same geographic space:

```
geo:51.5,-0.1:community    — Open community relay
geo:51.5,-0.1:mesh         — Local mesh network members only
geo:51.5,-0.1:commercial   — Paid relay service with SLA
geo:51.5,-0.1:emergency    — High-priority civil infrastructure
```

**Subscription model:**

```json
{
  "type": "geo_subscription",
  "content": {
    "identity": "cid:...",
    "primary": "cid:london-central-community",
    "secondary": ["cid:london-east-community", "cid:london-north-community"],
    "ssid_preferences": ["community", "mesh"],
    "trust_portability": true
  }
}
```

### 10.3.1 Identity-Based Mesh Authentication

SSID ↔ Identity ↔ Network Auth ↔ Geolocation form a unified access system:

```
┌─────────────────────────────────────────────────────────────┐
│                    Service Provider                          │
│  ┌─────────┐                                                │
│  │ Auth    │ ◄── Client presents identity CID               │
│  │ Server  │                                                │
│  └────┬────┘                                                │
│       │ Circulates authorization                            │
│       ▼                                                     │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐    │
│  │ Relay A │───│ Relay B │───│ Relay C │───│ Relay D │    │
│  │ geo:1   │   │ geo:2   │   │ geo:3   │   │ geo:4   │    │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘    │
│       ▲             ▲             ▲             ▲          │
│       └─────────────┴─────────────┴─────────────┘          │
│                Client roams freely                          │
└─────────────────────────────────────────────────────────────┘
```

**Flow:**
1. Client authenticates with service provider (presents identity CID)
2. Provider creates `mesh_authorization` thought
3. Authorization circulates to all relays in provider's mesh
4. Client roams across geo-pools — relays recognize authorized identity
5. No re-authentication needed within mesh

**Mesh Authorization Schema:**

```json
{
  "type": "mesh_authorization",
  "content": {
    "client_identity": "cid:...",
    "provider_identity": "cid:...",
    "ssid": "commercial",
    "geo_scope": ["cid:london-*", "cid:manchester-*"],
    "valid_until": 1770500000000,
    "tier": "premium"
  },
  "signature": "<provider signs>"
}
```

**Key insight:** Identity IS the network credential. Share once with provider, roam everywhere in their mesh. Like enterprise WiFi but with cryptographic identity and geographic scope.

### 10.4 Relay Marketplace

Relays advertise services. Clients discover and negotiate.

**DNS Discovery:**

```
_wot-relay.london-central.geo.wot.pub TXT "cid:relay123 pools=geo:51.5,-0.1 rate=0.001sat/kb cap=1gbps"
_wot-relay.london-central.geo.wot.pub TXT "cid:relay456 pools=geo:51.5,-0.1 rate=free tier=community"
```

**Relay Offer Schema:**

```json
{
  "type": "relay_offer",
  "content": {
    "relay_identity": "cid:...",
    "pools_served": ["cid:geo-pool-1", "cid:geo-pool-2"],
    "rate": {
      "type": "per_kb",
      "amount": 0.001,
      "currency": "sat"
    },
    "capacity": "1gbps",
    "terms_cid": "cid:full-terms-thought"
  }
}
```

### 10.5 Peering Authorization

Relays authorize specific identity CIDs. Negotiation on pool, agreement via side-channel:

```json
{
  "type": "relay_agreement",
  "content": {
    "client_identity": "cid:...",
    "relay_identity": "cid:...",
    "pools_scope": ["cid:geo-pool-1"],
    "incoming_trust_threshold": 0.3,
    "rate_agreed": { "type": "per_kb", "amount": 0.001 },
    "valid_until": 1770500000000
  },
  "because": ["cid:offer", "cid:negotiation-chain"]
}
```

**Flow:**

1. **Advertise** — Relays publish offers to geo-pool + DNS
2. **Discover** — Client queries DNS or pool for relays in area
3. **Negotiate** — Public pool shows offers, private side-channel for terms
4. **Authorize** — Relay stores agreement, accepts traffic for identity CID
5. **Compete** — Multiple relays bid, client picks by price/trust/latency

### 10.6 Relay Operation

Relays are stateless forwarders:

```
Client A ──encrypted──> Relay ──forward──> Client B
                          │
                          └── Stores nothing (just bandwidth)
                              Validates: identity authorized?
                              Validates: trust threshold met?
```

**What relays know:**
- Identity CIDs they're forwarding for
- Bandwidth consumed (for billing)
- Trust relationships (for authorization)

**What relays don't know:**
- Content of thoughts (encrypted)
- Full social graph (only their slice)

### 10.6.1 Multiway Encrypted Relay

Relays can forward content encrypted to multiple recipients. Keys exchanged via side pools, not through relay:

```
                    ┌─────────────┐
                    │   Relay     │
                    │ (sees blob) │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │ Alice   │       │  Bob    │       │ Carol   │
   │ decrypt │       │ decrypt │       │ decrypt │
   └─────────┘       └─────────┘       └─────────┘
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                    Side Pool (keys)
```

**Key exchange via side pool:**

```json
{
  "type": "key_envelope",
  "content": {
    "session_id": "uuid:...",
    "recipients": ["cid:alice", "cid:bob", "cid:carol"],
    "envelopes": {
      "cid:alice": "<symmetric_key_encrypted_to_alice_pubkey>",
      "cid:bob": "<symmetric_key_encrypted_to_bob_pubkey>",
      "cid:carol": "<symmetric_key_encrypted_to_carol_pubkey>"
    }
  },
  "published_to": "cid:private-key-pool"
}
```

**Encrypted thought via relay:**

```json
{
  "type": "encrypted_thought",
  "content": {
    "session_id": "uuid:...",
    "ciphertext": "<aes-gcm encrypted payload>",
    "nonce": "..."
  }
}
```

**Security properties:**
- Relay sees only encrypted blobs — zero knowledge of content
- Key pool is bilateral/private — relay never sees keys
- Forward secrecy via session rotation
- Recipients can be added/removed by issuing new key envelopes

### 10.7 Trust Portability

Question: If I trust Alice in London-Central, do I trust her in London-East?

**Configurable per subscription:**

| Mode | Behavior |
|------|----------|
| `portable` | Trust follows identity across geo-pools |
| `local` | Trust computed fresh per pool |
| `decay` | Trust decays with geographic distance |

```json
{
  "type": "geo_subscription",
  "content": {
    "trust_portability": "decay",
    "decay_per_km": 0.01
  }
}
```

### 10.8 Incentive Alignment

**Relay operators serve their community:**
- Run relay for your neighborhood → faster local traffic
- Earn fees from commercial tier
- Community tier builds reputation (attestations)
- Geographic specialization creates natural market segments

**Economic model:**

| Tier | Rate | Operator Incentive |
|------|------|-------------------|
| Community | Free | Reputation, reciprocity |
| Standard | Market rate | Revenue |
| Premium | SLA + priority | Higher margins |
| Emergency | Free/subsidized | Civic duty, grants |

### 10.9 Mobile Handoff

As devices move, subscriptions update:

```
1. Device detects weakening signal from primary pool
2. Secondary pool becomes primary
3. Subscribe to new secondary (next adjacent pool)
4. Old secondary drops after grace period
```

**Handoff thought:**

```json
{
  "type": "geo_handoff",
  "content": {
    "identity": "cid:...",
    "from_pool": "cid:london-central",
    "to_pool": "cid:london-east",
    "timestamp": 1770218000000,
    "reason": "movement"
  }
}
```

Relays observe handoffs to manage authorization state.

---

## Open Questions

### Resolved This Session

- [x] Identity hierarchy model (root → device → agent)
- [x] Trust ceiling as structural consequence
- [x] Root revalidation ceremony
- [x] Attestation as reputation staking (not depletion)
- [x] Port numbers (1729/1637)
- [x] DNS discovery schema
- [x] Agent as provenance wrapper (processor-agnostic)
- [x] Operational schemas with ContentRef
- [x] Cross-pool trust computation (pool trust boundaries)
- [x] Pool propagation control (fountain/terminal)
- [x] Transitive neighbor expectations
- [x] Yggdrasil governance (multisig capable)
- [x] Geo-pool relay system (Part 10)
- [x] Hierarchical overlap (WiFi roaming model)
- [x] Multiple SSIDs per geographic area
- [x] Relay marketplace with DNS discovery
- [x] Trust portability across geo-boundaries

### Still Open

- [ ] Salience formula and weights
- [ ] Game theory for antagonistic trust boundaries
- [ ] MCP signing identity (child of device?)
- [ ] Encrypted content key management details
- [ ] Geo-pool: optimal overlap percentage for handoff
- [ ] Geo-pool: micropayment settlement (Lightning? attestation-based?)

---

## References

Design decisions recorded as WoT thoughts:

| CID | Topic |
|-----|-------|
| cid:07c38a489374c | WoT as routing protocol |
| cid:cd99997239df7 | Content vs routing attribution |
| cid:e1072aac2aec6 | Trust ceiling invariant |
| cid:b772e6eebbc4c | Revocation model |
| cid:d46398b9111f4 | ContentRef, rework, response schemas |
| cid:0c4b6ea932ee8 | Peering agreements as policy |
| cid:bf11c2e1727c6 | Multi-agent coordination |
| cid:38e659baf547a | Event-driven coordination |
| cid:5332d64dee093 | Three processing paths |
| cid:f67d5259179c5 | Agent lifecycle |
| cid:664cf5a6ef928 | Bookkeeper scope |
| cid:6ca0a700930c6 | Bookkeeper pattern |
| cid:13279cf35f75a | Boot thoughts injection |
| cid:efee070fcce6f | Daemon logs design |
| cid:c9b4b48cd5018 | P0 security fixes |
| cid:832018532ac94 | Agent architecture summary |
| cid:f3a2944cd15fe | v0.12 design session summary |
| cid:bdae65eb0f580 | v0.12 proposal thought |
| cid:7b21df6567d1b | Cross-pool trust boundaries |
| cid:6ba604644116 | Pool propagation (fountain/terminal) |
| cid:6cafd3fcfd194 | Transitive neighbor expectations |
| cid:3da186263fc78 | Yggdrasil multisig governance |
| cid:ab9e97fd26e7e | Session summary (2026-02-04 cont.) |

---

*Ergo cognito sum.* — I am known, therefore I am.

*Git blame for all media. Receipts all the way down.*
