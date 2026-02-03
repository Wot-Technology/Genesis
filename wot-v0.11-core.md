# Web of Thought (WoT) Core Specification v0.11

**Protocol for Distributed Knowledge with Computable Trust**

*February 2026*

---

## Part A: Hello World

### Install

```bash
# From source
git clone https://github.com/wot-technology/wot-core
cd wot-core && cargo build --release
export PATH="$PATH:$(pwd)/target/release"

# Binary name is 'wot'
alias wot="$(pwd)/target/release/wot"
```

### Initialize Your Identity

```bash
wot init --name alice
```

This creates:
- An Ed25519 keypair (your cryptographic identity)
- A default pool (`alice-default`) for your thoughts
- An aspects pool (`alice-aspects`) for preferences/observations
- Local storage at `~/.wot/`

Output:
```
Generated identity: alice
  CID: cid:blake3:7f3a8b2c...
  Public key: ed25519:d784...

Created default pool: alice-default
Created aspects pool: alice-aspects

WoT initialized!
```

### Create Your First Thought

```bash
wot create --text "Hello WoT"
```

Output:
```
Created thought: cid:blake3:9e4f7a1b...
  Type: basic
  Text: Hello WoT
  Published to: cid:blake3:5c2d...
```

That CID is permanent. The content is signed by your identity. Anyone who gets this thought can verify you wrote it.

### View a Thought

```bash
wot show 9e4f7a1b
```

Output:
```
Thought: cid:blake3:9e4f7a1b2c3d4e5f...
  Type: basic
  Content: {"text": "Hello WoT"}
  Created by: alice (cid:blake3:7f3a8b2c...)
  Created at: 2026-02-03 12:34:56 UTC
  Signature: valid
```

### Connect Thoughts (Provenance)

```bash
wot create --text "Building on my first thought" --because 9e4f7a1b
```

The `--because` flag creates a provenance chain. This thought exists *because* of the first one.

### Sync With a Peer

```bash
# Add a peer
wot peer add https://bob.example.com:7432

# Sync
wot sync
```

Now you have Bob's thoughts (that he's shared with you), and he has yours. No central server. Just peers exchanging signed, attributed content.

### What You Now Have

- **Immutable records**: Thoughts never change. Edits create new thoughts linked via `rework`.
- **Cryptographic attribution**: Every thought signed by its creator.
- **Provenance chains**: `because` links show where ideas came from.
- **Distributed sync**: Peer-to-peer, no central authority.
- **Computable trust**: Vouch for peers, trust propagates through the network.

---

## Part B: Core Concepts

### B.1 The Thought Primitive

Everything in WoT is a Thought. There are no special database tables, no separate user records, no metadata stores. Just Thoughts with typed content.

```
┌─────────────────────────────────────────────────────┐
│ Thought                                             │
├─────────────────────────────────────────────────────┤
│ cid: "cid:blake3:9e4f7a1b..."     // content hash   │
│ type: "basic"                      // schema name   │
│ content: {"text": "Hello"}         // payload       │
│ created_by: "cid:blake3:7f3a..."   // identity CID  │
│ created_at: 1706972096000          // unix ms       │
│ because: ["cid:blake3:..."]        // provenance    │
│ signature: "ed25519:..."           // proof         │
└─────────────────────────────────────────────────────┘
```

**Properties:**
- **Immutable**: Once created, never changes
- **Content-addressed**: CID = hash of canonical content
- **Signed**: Creator's Ed25519 signature proves authenticity
- **Attributed**: `created_by` always present, never null
- **Grounded**: `because` links to provenance (why this exists)

### B.2 Connections & Relations

Connections are Thoughts that link other Thoughts. They have `from`, `to`, and `relation` fields.

```
┌─────────────────────────────────┐
│ Connection                      │
├─────────────────────────────────┤
│ type: "connection"              │
│ content: {                      │
│   from: "cid:blake3:aaa...",    │
│   to: "cid:blake3:bbb...",      │
│   relation: "supports"          │
│ }                               │
│ because: [from_cid, to_cid]     │
└─────────────────────────────────┘
```

The `because` chain includes both endpoints, enabling graph traversal from either direction.

**Core Relations:**

| Relation | Meaning | Example |
|----------|---------|---------|
| `published_to` | Thought visible in pool | thought → pool |
| `member_of` | Identity belongs to pool | identity → pool |
| `vouches` | Trust endorsement | alice → bob |
| `supports` | Evidence for claim | evidence → claim |
| `contradicts` | Tension with | rebuttal → claim |
| `rework` | Edit/revision of | new_version → old_version |
| `instance_of` | Typed by schema | thought → schema |
| `about` | Concerns identity | aspect → identity |
| `request_attention` | Urgency signal | thought → identity |

### B.3 Trust Computation

Trust is never stored. It's computed by walking vouch chains from observer to target.

```
alice ──vouches(0.9)──► bob ──vouches(0.8)──► carol
```

**Formula:**
```
trust(alice → carol) = 0.9 × 0.8 × decay^distance
                     = 0.72 × 0.5^2
                     = 0.18
```

Default decay = 0.5. After 3 hops, trust approaches zero.

**CLI:**
```bash
wot trust score <carol_cid>    # Your trust in carol
wot trust vouchers <bob_cid>   # Who vouches for bob
wot vouch <carol_cid> -w 0.8   # Vouch for carol
```

### B.4 Pools & Sync

Pools are sync boundaries. Thoughts published to a pool sync with pool members.

```
┌─────────────────────────────────────┐
│ Pool: "project-alpha"               │
├─────────────────────────────────────┤
│ Members: [alice, bob, carol]        │
│ Thoughts: [synced within boundary]  │
└─────────────────────────────────────┘
```

**Sync Protocol:**
1. Peers exchange bloom filters of what they have
2. Identify delta (what's missing)
3. Transfer missing thoughts
4. Verify signatures on receipt

**CLI:**
```bash
wot pool create project-alpha
wot pool invite project-alpha <bob_cid>
wot sync
```

### B.5 Attention System

The attention system controls what breaks through to your awareness.

**Components:**

1. **Waterline** - Per-pool threshold
   - `urgency_threshold`: Minimum urgency to surface (0.0-1.0)
   - `trust_threshold`: Minimum trust to surface (0.0-1.0)
   - `agent_config`: What types agents see vs humans

2. **Subscriptions** - Push notifications
   - Subscribe to pools or trails
   - Webhook or internal channel callbacks
   - Filtered by your waterline

3. **Urgency** - Via `request_attention` connections
   - Attestation weight = urgency level
   - Effective urgency = weight × requester's trust
   - Levels: interrupt (0.9+), notify (0.7+), surface (0.4+), pre-cache (<0.4)

**Flow:**
```
thought created
    ↓
published_to pool
    ↓
dispatcher checks subscriptions
    ↓
for each subscriber:
    compute urgency (weight × trust)
    check waterline threshold
    if passes → notify
```

**CLI:**
```bash
wot waterline set -u 0.7 -t 0.3
wot subscribe add project-alpha --webhook https://...
wot escalate <cid> --to <bob_cid> -w 0.9
wot done <cid>  # mark as acted upon
```

---

## Part C: Design Philosophy & FAQ

### C.1 The First Language Problem

**Q: You claim thoughts are "self-describing" but isn't that philosophically impossible?**

Correct. True self-description requires infinite regress. WoT handles this pragmatically:

```
Thought → instance_of → Schema → instance_of → meta-schema → ... → bootstrap
```

The regress terminates at **bootstrap** - a set of canonical schemas signed by the "yggdrasil" identity (held secret, like a certificate authority). These bootstrap schemas are:
- Hardcoded CIDs in implementations
- Human-readable definitions alongside
- The "first language" is these ~30 core types

LLMs don't replace structural typing - they **bridge** when schemas diverge. The `content` field is typed JSON, `instance_of` connections provide machine-readable schema references. LLMs help when you encounter an unknown schema and need to reason about it semantically.

**The bootstrap contains:**
- Primitive types: `basic`, `identity`, `connection`, `attestation`
- Governance types: `pool`, `member`, `permission`
- Knowledge types: `schema`, `trail`, `aspect`
- Attention types: `waterline`, `subscription`

New types derive from these via `instance_of` chains. The bootstrap is the shared vocabulary; everything else is negotiated.

### C.2 External References & Data Portability

**Q: What happens when WoT needs to reference data outside the system?**

This is handled via the `source` field and input schemas. Consider an invoice that exists in two bookkeeping systems:

```
┌─────────────────────────────────────────────────┐
│ Thought: Invoice imported from QuickBooks       │
├─────────────────────────────────────────────────┤
│ type: "invoice"                                 │
│ content: {                                      │
│   amount: 1500.00,                              │
│   external_ids: {                               │
│     quickbooks: "INV-2024-0042",                │
│     ubl: "urn:oasis:names:...:12345"            │
│   }                                             │
│ }                                               │
│ source: cid:blake3:abc...  ←── connection to    │
│                                input schema     │
│ created_by: alice (who imported it)             │
│ created_at: 2026-02-03T...                      │
└─────────────────────────────────────────────────┘
```

The `source` field points to a connection:
```
from: alice_identity
to: input/quickbooks_api schema
relation: uses_input
```

This captures: WHO imported it, FROM WHERE, and WHEN. The external identifiers live in `content` - WoT wraps them with attribution and provenance.

**Reconciliation example** (matching payer's outgoing to payee's incoming bank transaction):

```
┌──────────────────┐         ┌──────────────────┐
│ Alice's outgoing │         │ Bob's incoming   │
│ bank_transaction │         │ bank_transaction │
│ (from Alice's    │         │ (from Bob's      │
│  bank export)    │         │  bank export)    │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
         └──────────┬─────────────────┘
                    ▼
         ┌──────────────────┐
         │ Connection       │
         │ relation: same_as│
         │ created_by: carol│
         │ because: [...]   │
         └──────────────────┘
```

The `same_as` connection is a **claim** that these represent the same real-world event. It has:
- `created_by`: who made the claim (human accountant? automated matcher?)
- `because`: evidence (timestamp proximity, amount match, reference codes)
- Attestations from others can vouch for or dispute this link

**WoT doesn't solve the matching problem - it provides accountability for matching decisions.** When reconciliation is wrong, you can trace: who claimed these matched, what evidence they cited, who attested to it.

### C.3 Name & Prior Art

**Q: Isn't "WoT" confusing with PGP's "Web of Trust"?**

Acknowledged lineage. WoT (Web of Thought) shares the transitive trust model:

| Aspect | PGP Web of Trust | WoT (Web of Thought) |
|--------|------------------|----------------------|
| Trust propagation | Vouching chains | Vouching chains |
| Central authority | None | None |
| Scope | Identity verification | Knowledge attribution |
| Content | Just keys | Arbitrary typed content |
| Provenance | None | `because` chains |

The name reflects the core idea: thoughts connected in a web, trust computed across the connections.

**Q: What similar systems exist?**

| System | Similarity | Difference |
|--------|------------|------------|
| **IPFS** | Content addressing | No identity, no trust |
| **Git** | Content addressing + signatures | No trust computation, repo-centric |
| **ActivityPub** | Federated, social | Mutable, no provenance chains |
| **Ceramic** | Mutable docs on IPFS | Different trust model, stream-based |
| **Solid** | Decentralized data pods | ACL-based access, not structural |
| **LLM Observability tools** | Audit trails | Centralized, LLM-only, no trust |

WoT combines:
- **IPFS**: Content addressing (CID = hash)
- **Git**: Cryptographic signatures on commits
- **PGP**: Transitive trust via vouching
- **Provenance**: `because` chains (like academic citations)
- **Attention**: Waterlines, urgency, salience (novel)

### C.4 Data Format Migration

**Q: What happens when data formats change? How do you migrate?**

Thoughts are immutable - you never modify them. Format evolution uses `rework` chains:

```
old_thought (format v1)
    ↑
    │ rework
    │
new_thought (format v2)
    because: [old_thought, migration_script]
```

The new thought:
- Links to the old via `rework` relation
- Cites the migration logic in `because`
- Both versions remain accessible
- Queries can follow `rework` chains to find latest

For breaking changes, schema versioning:
```
schema/invoice/v1 → schema/invoice/v2
                    because: [v1, changelog_thought]
```

Implementations can:
1. Understand both versions
2. Auto-migrate on read
3. Reject unknown versions and request translation

The `because` chain always explains WHY the format changed and HOW to interpret old data.

### C.5 LLM Role

**Q: Are you relying on LLMs for data portability?**

No. LLMs are **assistants**, not **authorities**.

**Structural layer (no LLM needed):**
- CID computation
- Signature verification
- Schema validation via `instance_of`
- Trust computation via vouch graph
- Sync protocol

**LLM-assisted layer (optional):**
- Semantic search across content
- Bridging unknown schemas
- Generating human summaries
- Navigation suggestions (PageIndex)

If LLMs disappeared tomorrow, WoT still works - you just lose semantic search and natural language queries. The structural integrity is cryptographic, not probabilistic.

---

## Part D: Complete Ontology Reference

This section documents every thought type in WoT, organized by domain. Each type includes its exact content schema and semantic meaning.

### D.1 Bootstrap Types (Primitive Layer)

These types are signed by the `yggdrasil` identity and hardcoded in implementations. They cannot be extended—only referenced.

#### `basic`

The simplest thought. Just text.

```json
{
  "type": "basic",
  "content": {
    "text": "Any textual content"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes | The content |

#### `identity`

An actor who can sign thoughts. Every thought has a `created_by` pointing to an identity.

```json
{
  "type": "identity",
  "content": {
    "name": "alice",
    "public_key": "ed25519:d784a3b2c1..."
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable name |
| `public_key` | string | yes | Ed25519 public key for signature verification |

**Note:** The identity's CID is computed from its content, not the key. Name changes create new identities linked via `rework`.

#### `connection`

A typed relation between two thoughts. The fundamental edge in the thought graph.

```json
{
  "type": "connection",
  "content": {
    "from": "cid:blake3:aaa...",
    "to": "cid:blake3:bbb...",
    "relation": "supports"
  },
  "because": ["cid:blake3:aaa...", "cid:blake3:bbb..."]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | CID | yes | Source thought |
| `to` | CID | yes | Target thought |
| `relation` | string | yes | Relation type (see Part E) |

**Convention:** `because` includes both endpoints for bidirectional traversal.

#### `attestation`

A signed belief about another thought. Weight indicates strength of endorsement.

```json
{
  "type": "attestation",
  "content": {
    "on": "cid:blake3:target...",
    "weight": 0.85,
    "via": "agreement"
  },
  "because": ["cid:blake3:target..."]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `on` | CID | yes | Thought being attested |
| `weight` | float | yes | -1.0 to 1.0 (negative = dispute) |
| `via` | string | no | Aspect/channel (default: `agreement`) |

**Via Aspects:**
- `agreement` — Trust computation uses this
- `ready_to_consume` — Content delivery / streaming
- `request_attention` — Urgency signal to observer

### D.2 Governance Types

#### `pool`

A sync boundary. Thoughts published to a pool sync with pool members.

```json
{
  "type": "pool",
  "content": {
    "name": "project-alpha",
    "description": "Collaboration space for project alpha",
    "governance": "bilateral"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable identifier |
| `description` | string | no | Purpose of the pool |
| `governance` | string | no | `bilateral` (default), `unilateral`, `consensus` |

**Governance modes:**
- `bilateral` — Membership requires mutual attestation
- `unilateral` — Owner approves members
- `consensus` — Majority vote for changes

#### `member`

Membership claim. Requires attestation from pool owner for `bilateral` governance.

```json
{
  "type": "connection",
  "content": {
    "from": "cid:blake3:identity...",
    "to": "cid:blake3:pool...",
    "relation": "member_of"
  }
}
```

This is a connection with `relation: member_of`. Active membership requires:
1. This connection from identity to pool
2. Attestation on this connection from pool owner (for bilateral)

#### `permission`

Access control for pool operations.

```json
{
  "type": "permission",
  "content": {
    "pool": "cid:blake3:pool...",
    "identity": "cid:blake3:identity...",
    "grants": ["read", "write", "invite"]
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pool` | CID | yes | Pool this applies to |
| `identity` | CID | yes | Identity receiving permission |
| `grants` | array | yes | Permission types granted |

**Grant types:**
- `read` — Can see thoughts in pool
- `write` — Can publish thoughts to pool
- `invite` — Can add new members
- `admin` — Full control including governance changes

#### `waterline`

Per-identity attention thresholds for a pool.

```json
{
  "type": "waterline",
  "content": {
    "pool": "cid:blake3:pool...",
    "urgency_threshold": 0.4,
    "trust_threshold": 0.2,
    "agent_config": {
      "types_visible": ["basic", "trace"],
      "types_hidden": ["internal"]
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pool` | CID | yes | Pool this waterline applies to |
| `urgency_threshold` | float | no | Minimum effective urgency (0.0-1.0) |
| `trust_threshold` | float | no | Minimum creator trust (0.0-1.0) |
| `agent_config` | object | no | Type filtering for agent vs human |

**Effective urgency formula:**
```
effective_urgency = request_attention_weight × requester_trust
```

#### `subscription`

Push notification configuration.

```json
{
  "type": "subscription",
  "content": {
    "pool_cid": "cid:blake3:pool...",
    "trail_cid": "cid:blake3:trail...",
    "callback_type": "webhook",
    "callback_url": "https://example.com/notify"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pool_cid` | CID | yes | Pool to watch |
| `trail_cid` | CID | no | Specific trail to filter (thoughts must extend) |
| `callback_type` | string | yes | `webhook`, `sse`, `internal` |
| `callback_url` | string | conditional | Required for webhook/sse |

### D.3 Knowledge Types

#### `schema`

Self-describing type definition. Enables structural validation.

```json
{
  "type": "schema",
  "content": {
    "name": "invoice",
    "version": "1.0",
    "fields": {
      "amount": {"type": "number", "required": true},
      "currency": {"type": "string", "required": true},
      "due_date": {"type": "timestamp", "required": false}
    },
    "extends": "cid:blake3:base_document..."
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Type name |
| `version` | string | no | Semantic version |
| `fields` | object | yes | Field definitions |
| `extends` | CID | no | Parent schema (inheritance) |

#### `trail`

Named entry point into a path through the thought graph. Trails enable navigation and subscription scoping.

```json
{
  "type": "trail",
  "content": {
    "name": "authentication-flow",
    "description": "All thoughts related to auth implementation",
    "entry_point": "cid:blake3:first_thought..."
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable trail name |
| `description` | string | no | What this trail covers |
| `entry_point` | CID | no | First thought in trail |

**Trail extension:** A thought extends a trail if the trail CID appears in its `because` chain.

#### `aspect`

Observable property of an identity: values, preferences, needs, constraints.

```json
{
  "type": "aspect",
  "content": {
    "about": "cid:blake3:identity...",
    "category": "preference",
    "key": "notification_frequency",
    "value": "daily"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `about` | CID | yes | Identity this aspect describes |
| `category` | string | yes | `value`, `preference`, `need`, `constraint`, `observation` |
| `key` | string | yes | Aspect identifier |
| `value` | any | yes | Current value |

**Categories:**
- `value` — Core beliefs/principles
- `preference` — Desired but flexible
- `need` — Non-negotiable requirements
- `constraint` — External limitations
- `observation` — Third-party noted characteristic

#### `instruction`

Directive from identity to agents acting on their behalf.

```json
{
  "type": "instruction",
  "content": {
    "for_agent": "cid:blake3:agent_identity...",
    "directive": "Always summarize long documents before presenting",
    "scope": "cid:blake3:pool...",
    "priority": 0.8
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `for_agent` | CID | no | Specific agent (null = all) |
| `directive` | string | yes | The instruction text |
| `scope` | CID | no | Pool/trail scope |
| `priority` | float | no | Relative importance (0.0-1.0) |

### D.4 Trace Types

#### `trace`

Development/debug record. Captures decisions, observations, session state.

```json
{
  "type": "trace",
  "content": {
    "text": "Decided to use BLAKE3 for hashing",
    "category": "decision",
    "session_id": "2026-02-03-morning"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | yes | Trace content |
| `category` | string | no | `decision`, `observation`, `checkpoint`, `error` |
| `session_id` | string | no | Session grouping |

#### `checkpoint`

Browser/context capture for provenance.

```json
{
  "type": "checkpoint",
  "content": {
    "url": "https://example.com/article",
    "title": "Interesting Article",
    "selection": "The key insight was...",
    "duration_seconds": 180
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | Page URL |
| `title` | string | no | Page title |
| `selection` | string | no | Selected text |
| `duration_seconds` | number | no | Time spent |

### D.5 Application Types

Application-specific types follow the namespace convention: `namespace/type`.

#### `anthropic/conversation`

Claude conversation container.

```json
{
  "type": "anthropic/conversation",
  "content": {
    "model": "claude-opus-4-5-20251101",
    "session_id": "abc123",
    "message_count": 15,
    "token_usage": {
      "input": 12500,
      "output": 8200
    }
  }
}
```

#### `anthropic/message`

Individual message in a conversation.

```json
{
  "type": "anthropic/message",
  "content": {
    "role": "assistant",
    "text": "Here's my analysis...",
    "thinking": "Let me consider the implications..."
  },
  "because": ["cid:blake3:conversation...", "cid:blake3:previous_message..."]
}
```

#### `anthropic/tool_use`

Tool invocation record.

```json
{
  "type": "anthropic/tool_use",
  "content": {
    "tool_name": "Read",
    "input": {"file_path": "/path/to/file"},
    "id": "tool_use_123"
  },
  "because": ["cid:blake3:message_that_triggered..."]
}
```

#### `anthropic/tool_result`

Tool execution result.

```json
{
  "type": "anthropic/tool_result",
  "content": {
    "tool_use_id": "tool_use_123",
    "result": "File contents here...",
    "is_error": false
  },
  "because": ["cid:blake3:tool_use..."]
}
```

#### `gaia/resource`

Physical resource in the GAIA geospatial system.

```json
{
  "type": "gaia/resource",
  "content": {
    "name": "Community Solar Array",
    "resource_type": "energy",
    "geohash": "9q8yy",
    "capacity": {"value": 50, "unit": "kW"},
    "availability": "shared"
  }
}
```

#### `gaia/claim`

Territorial/resource claim.

```json
{
  "type": "gaia/claim",
  "content": {
    "resource": "cid:blake3:resource...",
    "claimant": "cid:blake3:identity...",
    "claim_type": "stewardship",
    "bounds": {"geohash_prefix": "9q8yy"}
  }
}
```

#### `pong/match`

Adversarial game match (Go variants, etc.).

```json
{
  "type": "pong/match",
  "content": {
    "game_type": "go_san",
    "players": {
      "black": "cid:blake3:alice...",
      "white": "cid:blake3:bob..."
    },
    "board_size": 19,
    "rules_version": "1.0"
  }
}
```

#### `pong/move`

Game move record.

```json
{
  "type": "pong/move",
  "content": {
    "match": "cid:blake3:match...",
    "player": "black",
    "position": {"x": 3, "y": 4},
    "move_number": 42
  },
  "because": ["cid:blake3:match...", "cid:blake3:previous_move..."]
}
```

### D.6 Response Types

Universal response vocabulary for acknowledging actions.

#### `response`

Base response type. Extended by domain-specific responses.

```json
{
  "type": "response",
  "content": {
    "to": "cid:blake3:thought_being_responded_to...",
    "response_type": "acted",
    "note": "Completed the requested review"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | CID | yes | Thought being responded to |
| `response_type` | string | yes | Response category |
| `note` | string | no | Additional context |

**Universal response types:**
- `seen` — Acknowledged without action
- `acted` — Action taken
- `denied` — Explicitly refused
- `ignored` — Consciously deprioritized

**Domain extensions:** Response schemas can extend this with additional `response_type` values via the `extends` field in their schema definition.

---

## Part E: Relations Reference

Relations are the `relation` field in connection thoughts. They define the semantic meaning of edges in the thought graph.

### E.1 Trust Relations

| Relation | From | To | Semantics |
|----------|------|-----|-----------|
| `vouches` | identity | identity | Trust endorsement. Weight in attestation = trust level. Used for transitive trust computation. |
| `delegates_to` | identity | identity | Authorization to act on behalf. Enables agent relationships. |
| `revokes` | identity | vouch/delegation | Withdraws previous trust. Creates immutable audit trail. |

**Trust computation uses `vouches` relations:**
```
trust(A→C) = Π(vouch_weights) × decay^hops
```

### E.2 Provenance Relations

| Relation | From | To | Semantics |
|----------|------|-----|-----------|
| `supports` | evidence | claim | Evidence supporting a claim. Strengthens claim credibility. |
| `contradicts` | rebuttal | claim | Tension or disagreement. May weaken claim. |
| `derives_from` | thought | thought | Intellectual derivation. Looser than `because` chain. |
| `quotes` | thought | thought | Direct quotation/embedding. |
| `same_as` | thought | thought | Claim that two thoughts represent same real-world entity. |

### E.3 Structural Relations

| Relation | From | To | Semantics |
|----------|------|-----|-----------|
| `published_to` | thought | pool | Visibility in pool. Triggers sync to pool members. |
| `member_of` | identity | pool | Pool membership claim. Requires attestation for activation. |
| `instance_of` | thought | schema | Type declaration. Enables structural validation. |
| `extends` | schema | schema | Schema inheritance. Child inherits parent fields. |
| `rework` | new_thought | old_thought | Edit/revision chain. New replaces old semantically. |

### E.4 Attention Relations

| Relation | From | To | Semantics |
|----------|------|-----|-----------|
| `request_attention` | thought | identity | Urgency signal. Attestation weight = urgency level. |
| `about` | aspect | identity | Aspect concerns this identity. |
| `responds_to` | response | thought | Response to a thought (seen/acted/denied/ignored). |
| `supersedes` | thought | thought | Makes target obsolete. Stronger than `rework`. |

### E.5 Spatial Relations (GAIA Domain)

| Relation | From | To | Semantics |
|----------|------|-----|-----------|
| `located_at` | resource | geohash_pool | Physical location binding. |
| `claims` | identity | resource | Stewardship/ownership claim. |
| `borders` | geohash_pool | geohash_pool | Adjacent territory. |
| `contains` | geohash_pool | geohash_pool | Hierarchical containment. |

### E.6 Game Relations (Pong Domain)

| Relation | From | To | Semantics |
|----------|------|-----|-----------|
| `plays_in` | identity | match | Player in game. |
| `follows` | move | move | Sequential move order. |
| `captures` | move | position | Stone capture event. |
| `concedes` | identity | match | Resignation. |

### E.7 Relation Semantics

**Directionality:** All relations are directed (from → to). Bidirectional semantics require two connections.

**Attestation interaction:** Relations often require attestation to activate:
- `member_of` needs pool owner attestation
- `vouches` weight comes from attestation
- `request_attention` urgency modulated by trust

**Traversal:** The `because` chain in connections includes both endpoints:
```json
{
  "type": "connection",
  "content": {"from": "A", "to": "B", "relation": "supports"},
  "because": ["A", "B"]
}
```

This enables queries from either direction:
- "What supports B?" → Find connections where `to=B` and `relation=supports`
- "What does A support?" → Find connections where `from=A` and `relation=supports`

---

## Part F: Wire Formats & CID Computation

### F.1 Canonical JSON

For CID computation, content is serialized to canonical JSON:

1. **Object keys sorted alphabetically**
2. **No whitespace** (compact form)
3. **Numbers without trailing zeros** (1.0 → 1)
4. **Unicode normalized** (NFC)
5. **No undefined/null fields** (omit rather than include)

Example:
```json
{"created_at":1706972096000,"created_by":"cid:blake3:7f3a...","content":{"text":"Hello"},"type":"basic"}
```

### F.2 CID Format

```
cid:blake3:<64-char-hex>
```

Components:
- `cid:` — Prefix identifying content-addressed identifier
- `blake3:` — Hash algorithm
- `<hex>` — 256-bit hash as lowercase hex

### F.3 CID Computation

```python
import blake3
import json

def compute_cid(thought_dict):
    # Exclude cid and signature from hash input
    hashable = {k: v for k, v in thought_dict.items()
                if k not in ('cid', 'signature')}

    # Canonical JSON
    canonical = json.dumps(hashable,
                          sort_keys=True,
                          separators=(',', ':'),
                          ensure_ascii=False)

    # BLAKE3 hash
    digest = blake3.blake3(canonical.encode('utf-8')).hexdigest()

    return f"cid:blake3:{digest}"
```

### F.4 Signature Format

```
ed25519:<128-char-hex>
```

Signature covers the CID bytes (the hash, not the full `cid:blake3:` string):

```python
from nacl.signing import SigningKey

def sign_thought(thought_dict, private_key_bytes):
    cid = compute_cid(thought_dict)

    # Sign the hash bytes, not the string
    hash_bytes = bytes.fromhex(cid.split(':')[2])

    signing_key = SigningKey(private_key_bytes)
    signature = signing_key.sign(hash_bytes).signature

    return f"ed25519:{signature.hex()}"
```

### F.5 CBOR Wire Format

For network transfer, thoughts use CBOR (Concise Binary Object Representation):

```
┌─────────────────────────────────────────────┐
│ CBOR Map                                    │
├─────────────────────────────────────────────┤
│ 0: cid (text)                               │
│ 1: type (text)                              │
│ 2: content (map)                            │
│ 3: created_by (text)                        │
│ 4: created_at (integer, ms)                 │
│ 5: because (array of text)                  │
│ 6: signature (text)                         │
│ 7: source (text, optional)                  │
└─────────────────────────────────────────────┘
```

Integer keys reduce size. Implementations must support both keyed and named formats.

### F.6 Bloom Filter Sync

Delta sync uses bloom filters to identify missing thoughts:

```
┌─────────────────────────────────────────────┐
│ Sync Request                                │
├─────────────────────────────────────────────┤
│ pool_cid: "cid:blake3:..."                  │
│ have_filter: <bloom filter bytes>           │
│ filter_params: {k: 7, m: 65536}             │
│ since_timestamp: 1706972000000              │
└─────────────────────────────────────────────┘
```

1. Peer A sends bloom filter of CIDs it has
2. Peer B tests each CID against filter
3. Probable matches (already have) are skipped
4. Definite misses (don't have) are sent

False positive rate ~1% with k=7, m=65536 for 10k thoughts.

### F.7 API Endpoints

Standard daemon HTTP API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/thought` | POST | Create thought |
| `/api/thought/:cid` | GET | Retrieve thought |
| `/api/thought/delegated` | POST | Create with delegated signing |
| `/api/search` | POST | Full-text search |
| `/api/sync` | POST | Pool sync (bloom filter) |
| `/api/subscribe/sse` | GET | Server-sent events stream |
| `/api/identity/:name` | GET | Resolve identity by name |
| `/api/trust/:cid` | GET | Compute trust score |

### F.8 Delegated Signing

For external scripts without key access:

```json
POST /api/thought/delegated
{
  "identity": "alice",
  "secret": "shared-secret",
  "text": "Content here",
  "thought_type": "basic",
  "pool": "cid:blake3:...",
  "because": ["cid:blake3:..."]
}
```

Secret is verified via one-way hash comparison:
```
stored = hash(salt + hash(salt + secret))
verify = hash(salt + hash(salt + input)) == stored
```

This enables Python/Node/bash scripts to create thoughts through the daemon without direct key access.

---

## Part G: Architectural Patterns

### G.1 Pool Budding

Pools can spawn child pools for infinite granularity:

```
global-pool
  ├── continent/north-america
  │     ├── country/usa
  │     │     ├── state/california
  │     │     │     ├── city/sf
  │     │     │     │     └── neighborhood/mission
  │     │     │     └── city/la
  │     │     └── state/texas
  │     └── country/canada
  └── continent/europe
```

**Geohash pools:** Use geohash prefixes for automatic spatial hierarchy:
- `gaia/9q` — Western North America
- `gaia/9q8` — San Francisco Bay Area
- `gaia/9q8y` — San Francisco
- `gaia/9q8yy` — Specific neighborhood

### G.2 Trails as Discovery

Trails enable subscription scoping and navigation:

```
trail: "authentication-flow"
  ↓ extends
thought: "Initial auth design"
  ↓ extends (because chain includes trail)
thought: "Added OAuth support"
  ↓ extends
thought: "Security review complete"
```

Subscribe to trail = only see thoughts that extend it.

### G.3 Two-Level Attention

```
┌─────────────────────────────────────────────┐
│ Agent Layer (Low Waterline)                 │
│ - Sees most thoughts in subscribed pools    │
│ - Pre-filters, summarizes, caches           │
│ - Computes salience for human               │
└─────────────────────────────────────────────┘
                    │
                    │ passes waterline?
                    ▼
┌─────────────────────────────────────────────┐
│ Human Layer (High Waterline)                │
│ - Only sees high-urgency items              │
│ - Interrupt threshold: 0.9+                 │
│ - Can lower waterline to "dive deep"        │
└─────────────────────────────────────────────┘
```

**Effective urgency:**
```
urgency = request_attention_weight × requester_trust
```

| Level | Threshold | Behavior |
|-------|-----------|----------|
| Interrupt | 0.9+ | Push notification, sound |
| Notify | 0.7+ | Badge, inbox highlight |
| Surface | 0.4+ | Available on scroll |
| Pre-cache | <0.4 | Agent has, human doesn't see |

### G.4 Tiered Storage

Not everything lives everywhere:

| Tier | Content | Location | Example |
|------|---------|----------|---------|
| Hot | Recent, high-trust | Local SQLite | Last 30 days |
| Warm | Referenced, indexed | Local + cloud | Active trails |
| Cold | Archived, verified | Cloud/IPFS | Old but signed |
| Glacier | Rarely accessed | IPFS only | Historical |

Retrieval follows trust: higher trust = more resources spent fetching.

### G.5 Cross-Pool References

Thoughts can reference thoughts in other pools:

```json
{
  "type": "connection",
  "content": {
    "from": "cid:blake3:my_thought...",
    "to": "cid:blake3:external_thought...",
    "relation": "supports"
  }
}
```

The reference is valid even if you don't have the target thought. Fetch happens on traversal if you have access.

---

## Part H: Implementation Checklist

### H.1 Minimum Viable Implementation

- [ ] Thought struct with CID computation
- [ ] Ed25519 identity creation and signing
- [ ] SQLite storage backend
- [ ] Basic CLI: `init`, `create`, `show`
- [ ] Connection creation
- [ ] Attestation creation
- [ ] Direct trust computation (single hop)

### H.2 Network Ready

- [ ] HTTP sync endpoint
- [ ] Bloom filter delta sync
- [ ] Pool membership with bilateral attestation
- [ ] Peer discovery
- [ ] SSE notification stream

### H.3 Production Ready

- [ ] Transitive trust computation
- [ ] Waterline filtering
- [ ] Trail subscriptions
- [ ] Urgency computation
- [ ] Delegated signing API
- [ ] Schema validation
- [ ] Rework chain traversal

### H.4 Full Featured

- [ ] CBOR wire format
- [ ] libp2p transport
- [ ] Encrypted content (X25519)
- [ ] Agent separation layer
- [ ] Geohash pool budding
- [ ] Response schema extensions
- [ ] Multi-identity management

---

*Ergo cognito sum.* — I am known, therefore I am.

*Git blame for all media. Receipts all the way down.*

