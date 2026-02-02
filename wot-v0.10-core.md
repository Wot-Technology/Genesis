# Web of Thought (WoT) Core Specification v0.10

**Protocol for Distributed Knowledge with Computable Trust**

*wot.rocks · wot.technology · now.pub*

*February 2026*

---

## Abstract

WoT is a protocol for distributed knowledge organization using content-addressed thoughts, cryptographic identity, and trust-weighted connections. 

**Core thesis:** Memory is traversal, not storage. Trust is computed, not stored. Access is structural, not metadata.

**One primitive:** Everything is a Thought. Types are content shapes. Connections, attestations, identities, pools — all thoughts with typed content.

**Git blame for all media:** Every thought has attribution (`created_by`), provenance (`because`), edit history (`rework` connections), and accountability (`attestations`). Not just code — text, images, audio, video, AI outputs, data. Who said what, when, why, from where, who agreed, how it evolved. Full lineage for any content type.

---

## Part 1: Thought

The atomic unit. Immutable. Content-addressed.

### Structure

```rust
struct Thought {
    cid: Cid,                    // BLAKE3 hash of canonical content
    r#type: String,              // Schema type identifier
    content: Value,              // Type-specific payload
    created_by: Cid,             // Identity CID (required, never null)
    created_at: i64,             // Unix timestamp milliseconds
    source: Option<Cid>,         // Input attribution (connection to input schema)
    because: Vec<ContentRef>,    // Provenance chain
    signature: Signature,        // Ed25519 over canonical form
}
```

### Properties

| Property | Meaning |
|----------|---------|
| **Immutable** | Once created, content never changes |
| **Content-addressed** | CID = BLAKE3(canonical_json) |
| **Always attributed** | `created_by` required, never null |
| **Signed** | Signature proves creator authenticity |
| **Grounded** | `because` links to provenance |

### CID Format

```
cid:blake3:5cecc66b61e356cef45f35f5e3da679e8d335d7e224c08cddd2f3b7c680e4393
```

BLAKE3 preferred. SHA-256 accepted for legacy:
```
cid:sha256:099688fae3f45a8dd01fb13423bba8d8f901b851134adbeb557b357b6a475104
```

### Source Attribution

The `source` field is a CID pointing to a connection thought linking identity to input schema:

```
CONNECTION: identity_cid → uses_input → input_schema_cid
```

Traverse to get: WHO (from) + HOW (to → schema).

**Example schemas** (in library pools):

| Schema | Describes |
|--------|-----------|
| `input/desktop_keyboard` | Human typing |
| `input/voice_transcribed` | Speech-to-text |
| `input/agent_autocorrect` | Model intervention |
| `input/chat_assistant` | AI response |
| `input/git_commit` | Indexed from git |

No magic strings. Schema CIDs only.

### Because Chain

Provenance trail. "Why does this thought exist?"

```rust
struct ContentRef {
    thought_cid: Cid,
    segment_cid: Option<Cid>,      // Hash of specific segment
    anchor: Option<TextSelector>,  // Human-findable reference
    path: Option<String>,          // JSON Pointer, XPath
    temporal: Option<(f64, f64)>,  // start_sec, end_sec for media
}

struct TextSelector {
    exact: String,
    prefix: Option<String>,
    suffix: Option<String>,
}
```

- `segment_cid` = cryptographic proof segment existed
- `anchor` = human recovery when content changes
- `path` = structural reference into JSON/XML
- `temporal` = audio/video time range

Empty `because` = ungrounded assertion (terminal node).

---

## Part 2: Thought Types

Types are content schemas, not separate primitives.

### identity

Actor who can sign. Self-referential bootstrap.

```json
{
  "type": "identity",
  "content": {
    "name": "Keif",
    "pubkey": "ed25519:...",
    "created": 1706745600000
  },
  "created_by": "SELF"
}
```

**SELF resolution:** During CID computation, `SELF` is replaced with the computed CID. The identity thought's `created_by` points to itself.

*"I think I think therefore I am"* — the identity thought proves its own existence by the act of referencing itself. Cogito ergo sum as protocol primitive. This is the only self-referential case, required for identity bootstrap.

**Identity types:**

| Type | Trust Source | Keys | Example |
|------|--------------|------|---------|
| Sovereign | Vouch chains | Full ownership | Human user |
| Delegated | Parent × factor | Derived | Employee, child |
| Record | Vouches on behalf | None | Historical figure |
| External | Accuracy reputation | Outside system | Wikipedia |

### connection

Typed relation between two CIDs.

```json
{
  "type": "connection",
  "content": {
    "relation": "published_to",
    "from": "cid:blake3:...",
    "to": "cid:blake3:..."
  }
}
```

**Core relations:**

| Relation | Meaning |
|----------|---------|
| `supports` | Evidence for |
| `contradicts` | Tension with |
| `continues` | Sequence/thread |
| `derives_from` | Source/provenance |
| `vouches` | Trust endorsement |
| `member_of` | Pool membership |
| `published_to` | Pool visibility |
| `instance_of` | Type hierarchy |
| `same_as` | Identity equivalence |
| `rework` | Edit history link |
| `reply` | Response |
| `uses_input` | Input method binding |
| `recovery_delegate` | Key recovery |
| `managed_by` | Guardian relationship |
| `request_attention` | Ask identity to engage with thought |

**`request_attention` explained:** A directed connection from a thought (or connection) to a target identity, signed by the requester. Weight on the attestation of this connection carries urgency: 0.1–0.3 = pre-cache, 0.4–0.6 = surface next session, 0.7–0.9 = notify, 1.0 = interrupt. Effective urgency = weight × requester's trust with recipient. No trust = no attention. Spam is structurally impossible.

Connections are thoughts. They can be attested, connected, included in `because` chains.

### attestation

Signed belief about any thought.

```json
{
  "type": "attestation",
  "content": {
    "on": "cid:blake3:...",
    "via": "cid:blake3:...",
    "weight": 0.8
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `on` | CID | Target thought (required) |
| `via` | CID | Aspect for domain-specific trust |
| `weight` | f32 | -1.0 (veto) to +1.0 (strong agree) |

**Weight semantics:**
- +1.0 = strong agreement
- 0.0 = neutral / revoked
- -1.0 = strong disagreement / veto

When `via` points to constraint-type aspect and weight is -1.0: veto.

### Three Attestation-Driven Patterns

The attestation primitive drives three distinct protocol behaviors through different `via` aspects:

| Pattern | Via Aspect | Direction | Triggers |
|---------|-----------|-----------|----------|
| Trust signal | `agreement` | Observer → thought | Trust computation, reputation |
| Content delivery | `ready_to_consume` | Viewer → content | Streaming, sync, download |
| Attention request | `request_attention` | Thought → identity | Surfacing, caching, notification |

Same primitive. Same structure. Same weight semantics. Different aspect = different behavior. The attestation does triple duty: trust signal, pull request, and attention broker.

### aspect

Value, preference, need, mood, or constraint.

```json
{
  "type": "aspect",
  "content": {
    "aspect_type": "preference",
    "domain": "food",
    "name": "enjoys-spicy",
    "valence": "positive",
    "decay": null
  }
}
```

| Type | Persistence | Example |
|------|-------------|---------|
| value | Core, permanent | `family-first` |
| preference | Flexible | `enjoys-spicy` |
| need | Situational | `wheelchair-accessible` |
| mood | Transient | `craving-chips` |
| constraint | Hard, binary | `vegetarian` |

Aspects enable trust-by-domain: Sarah's wine recommendations ≠ Sarah's politics opinions.

### pool

Sync boundary with governance.

```json
{
  "type": "pool",
  "content": {
    "name": "keif-devices",
    "governance": "solo"
  }
}
```

**Governance models:**

| Model | Description |
|-------|-------------|
| `solo` | Single owner, full control |
| `bilateral` | Both parties must attest |
| `threshold` | N of M signers required |
| `delegated` | Trust computation determines access |

### schema

Self-describing type definition.

```json
{
  "type": "schema",
  "content": {
    "name": "bookmark",
    "version": "1.0",
    "fields": {
      "url": { "type": "string", "required": true },
      "title": { "type": "string" },
      "tags": { "type": "array", "items": "string" }
    },
    "index_hints": {
      "tags": "term_index",
      "title": "fulltext"
    }
  },
  "schema_cid": "cid:blake3:meta_schema"
}
```

### Response Schemas

Schemas define valid responses for thought types. Response vocabulary belongs to the schema, not the protocol.

**Universal responses (always available for any thought):**

| Response | Weight | Meaning |
|----------|--------|---------|
| `seen` | 0.0 | Acknowledged receipt |
| `acted` | 1.0 | Engaged meaningfully |
| `denied` | -1.0 | Rejected / refused |
| `ignored` | null | Explicit no-engagement |

**Schema inheritance:** Domain schemas extend universal via `extends` field. A medical triage schema extends attention, which extends universal. Full chain, clean bootstrap. Responses carry via attestation weight — same primitive, typed vocabulary.

### trail

Named entry point into a path.

```json
{
  "type": "trail",
  "content": {
    "name": "WoT Development",
    "entry": "cid:blake3:..."
  }
}
```

Trails are `because` chains walked backward. The trail thought is a bookmark.

### correction

Supersession marker. Original remains immutable. Reason lives in `because` chain.

```json
{
  "type": "correction",
  "content": {
    "corrects": "cid:blake3:...",
    "replacement": "cid:blake3:..."
  },
  "because": ["cid:blake3:reason_thought"]
}
```

The correction exists BECAUSE of the reason. No separate field needed.

### String Identifiers → Bootstrap CIDs

Several fields use string identifiers:
- **relation**: `published_to`, `member_of`, `vouches`, etc.
- **governance**: `solo`, `bilateral`, `threshold`, `delegated`
- **aspect_type**: `value`, `preference`, `need`, `mood`, `constraint`

These are **shorthand for well-known CIDs** in the bootstrap pool:

| String | Resolves To |
|--------|-------------|
| `published_to` | `wot://bootstrap/relation/published_to` |
| `solo` | `wot://bootstrap/governance/solo` |
| `preference` | `wot://bootstrap/aspect_type/preference` |

**Implementation:** On first run, daemon syncs bootstrap pool. String lookups become CID lookups. Custom relations/governance/aspect_types = create your own schema thought.

For 12-day sprint: strings are fine. Resolver maps to CIDs internally.

---

## Part 3: Access Model

**No visibility field.** Access is structural — determined by connection graph traversal.

### Principle

A thought is visible to you if:
1. You created it, OR
2. You can traverse to it through pools you're a member of

```
THOUGHT exists
    ↓
CONNECTION: thought → published_to → pool
    ↓
ATTESTATION on connection (bilateral: creator + pool)
    ↓
ACCESS = can you traverse to that pool?
```

### Privacy Patterns

| Pattern | Implementation |
|---------|----------------|
| Local forever | No pool connections. No sync path. |
| Device sync | Connect to personal devices pool only |
| Shared | Connect to group pool |
| Public | Connect to public pool |

### Secrets

Structural isolation IS protection:
1. Create thought
2. Connect ONLY to high-security pool
3. Pool membership requires strong attestation
4. No other connections = no other sync paths

---

## Part 4: Trust Computation

Trust is computed from the graph, not stored.

### Formula

```
trust(source, observer, context, time) =
  f(vouch_chains, attestation_weights, because_depth)
```

### Vouch Chains

Trust flows through `vouches` connections with decay:

```
keif → vouches → sarah (weight: 0.9)
sarah → vouches → mike (weight: 0.7)

trust(mike, from keif) = 0.9 × 0.7 = 0.63
```

### Decay Function

```
trust(A, B, distance) = base_trust × decay^distance
```

Default decay = 0.5. After 3 hops → approaching neutral.

### Groundedness

```
groundedness(attestation) =
  if because.is_empty():
    base_groundedness  // ~0.1-0.3
  else:
    aggregate(recurse(because), weight)
```

Deep `because` chains with trusted sources = high groundedness.
Empty `because` = floating assertion = low groundedness.

### Sybil Resistance

- New identity with no vouches = zero trust weight
- Vouching for bad actors costs YOUR reputation
- Revocation propagates downstream

### Brigading Defense

Weight beats volume:
- 1000 sockpuppets × 0.001 trust = 1.0 trust
- One high-trust vouch = 0.8 trust

---

## Part 5: Sync

### Pool Membership

Member if:
1. Connection exists: `identity → member_of → pool`
2. Bilateral attestation (you + pool governance)

### What Syncs

For each pool you're a member of:
- Thoughts with `published_to` connections to that pool
- Connections involving those thoughts
- Attestations on those connections
- Recursively: `because` chain thoughts

### Conflict Resolution

Thoughts are immutable — no content conflicts.

Connection attestation conflicts:
1. Most recent timestamp wins
2. Revocation always beats approval (safety)
3. Ambiguous → flag for human resolution

### Revocation

1. Create revocation attestation (weight: 0.0 or -1.0)
2. Sync to all pools with the connection
3. Request purge (can't guarantee)
4. Your devices stop serving

Can't force deletion from others — that's not how distributed works.

---

## Part 6: Schema System

### Interpretive Chain

```
YOUR THOUGHT
  ↓ schema_cid
TYPE DEFINITION
  ↓ schema_cid
META-SCHEMA
  ↓ schema_cid
PRIMITIVES
  ↓ schema_cid
BOOTSTRAP (natural language)
  ↓
TERMINAL: human-readable, self-evident
```

No external software needed. Interpretation travels with data.

### Primitive Types

| Type | Rust | Description |
|------|------|-------------|
| string | String | UTF-8 text |
| integer | i64 | Signed 64-bit |
| float | f64 | IEEE 754 |
| boolean | bool | true/false |
| bytes | Vec<u8> | Binary (base64) |
| timestamp | i64 | Unix ms |
| cid | Cid | Content address |

### Compound Types

```rust
enum CompoundType {
    Array { items: Type, min: Option<usize>, max: Option<usize> },
    Object { fields: HashMap<String, FieldDef> },
    Enum { values: Vec<String> },
    Union { variants: Vec<Type> },
}
```

### Schema Fields

```json
{
  "fields": { ... },
  "index_hints": { "field": "term_index|fulltext|embedding" },
  "salience_hints": { "field": { "weight": 1.5 } },
  "selectable": "text_anchor|temporal|structural|byte_range"
}
```

### Layered Representation

```
┌─────────────────────────────────────────┐
│  CANONICAL (content-addressed, signed)  │
│  - Source of truth                      │
│  - Human-verifiable                     │
│  - CID computed from this               │
├─────────────────────────────────────────┤
│  LOCAL INDEX (derived, disposable)      │
│  - SQLite / vectors / bloom filters     │
│  - Rebuilt on demand                    │
│  - YOUR machine, YOUR speed             │
└─────────────────────────────────────────┘
```

### Archival Resilience

```json
{
  "bootstrap_chain": ["schema_cid", "meta_cid", "primitives_cid", "bootstrap_cid"],
  "inline_bootstrap": true
}
```

When `inline_bootstrap: true`: complete interpretive lineage travels with thought. Decode in 500 years with no network.

---

## Part 7: Pool Governance

### Asymmetric Operations

```
Grant:  requires ALL authorized granters
Revoke: requires ANY authorized revoker
```

Fail-safe, not fail-open.

### Multi-Party Oversight

```
Identity: child-1
  Pool: soccer-team
    granted_by: coach
    observed_by: [coach, parent-a, parent-b]
    revocable_by: [coach, parent-a, parent-b]  // ANY
```

### Patterns

| Scenario | Grant | Revoke |
|----------|-------|--------|
| Child in school | Teacher | Any parent or teacher |
| Employee | Manager | Any: manager, compliance |
| AI agent | DevOps | Any: devops, security, exec |

### Audit Trail

Every permission change is a thought with `because`:

```json
{
  "type": "attestation",
  "content": { "on": "membership_connection", "weight": -1.0 },
  "because": ["incident_cid", "policy_cid"]
}
```

---

## Part 8: Rework Chains (Git Blame for All Media)

Edit history via connection thoughts, not embedded fields.

```json
{
  "type": "connection",
  "content": {
    "relation": "rework",
    "from": "new_version_cid",
    "to": "old_version_cid"
  }
}
```

**Because vs Rework:**
- `because` = WHY this thought exists (provenance, sources)
- `rework` = HOW this thought became this (edit history)

### The Full Lineage

For any thought, you can answer:

| Question | Source |
|----------|--------|
| Who created this? | `created_by` |
| When? | `created_at` |
| How was it input? | `source` → input method schema |
| What sources inform it? | `because` chain |
| Who agrees/disagrees? | Attestations on thought |
| What was changed? | `rework` chain backward |
| Who changed it? | `created_by` on each rework |
| Why was it changed? | `because` on rework connection |

### Media-Specific Examples

**Text document:**
```
v3: "Final article"
  created_by: editor
  because: [style_guide, fact_check_report]
  ↓ rework
v2: "Added expert quote"  
  created_by: journalist
  because: [interview_transcript, background_research]
  ↓ rework
v1: "First draft"
  created_by: journalist
  source: keif/desktop_keyboard
  because: [pitch_notes, source_documents]
```

**Image:**
```
v2: "Color corrected, cropped"
  created_by: designer
  because: [brand_guidelines]
  ↓ rework
v1: "Original photograph"
  created_by: photographer
  source: camera/canon_r5
  because: [shot_list, location_scout]
```

**Audio:**
```
v3: "Mastered podcast"
  created_by: audio_engineer
  because: [loudness_standards]
  ↓ rework
v2: "Edited for length"
  created_by: producer
  because: [episode_outline]
  ↓ rework
v1: "Raw recording"
  created_by: host
  source: microphone/shure_sm7b
  because: [guest_booking, topic_research]
```

**AI output:**
```
v2: "Human-edited response"
  created_by: human_reviewer
  because: [accuracy_check, tone_adjustment]
  ↓ rework
v1: "Raw model output"
  created_by: agent/claude-3
  source: agent/claude-3/chat
  because: [user_prompt, context_window_contents]
```

**Data transformation:**
```
v3: "Aggregated metrics"
  created_by: analyst
  because: [methodology_doc]
  ↓ rework
v2: "Cleaned dataset"
  created_by: data_engineer
  because: [cleaning_rules, validation_report]
  ↓ rework
v1: "Raw export"
  created_by: system/salesforce
  source: api/salesforce_export
  because: [query_definition]
```

### Blame Query

"Who is responsible for this claim?"

```rust
fn blame(&self, thought: &Thought, depth: usize) -> BlameReport {
    let mut contributors: Vec<Contributor> = vec![];
    
    // Direct creator
    contributors.push(Contributor {
        identity: thought.created_by,
        role: "creator",
        thought_cid: thought.cid,
    });
    
    // Walk rework chain (edit history)
    for (version, rework) in self.walk_rework(&thought.cid) {
        contributors.push(Contributor {
            identity: rework.created_by,
            role: "editor",
            thought_cid: version,
        });
    }
    
    // Walk because chain (sources)
    for source in self.walk_because(&thought.cid, depth) {
        contributors.push(Contributor {
            identity: source.created_by,
            role: "source",
            thought_cid: source.cid,
        });
    }
    
    // Get attesters
    for attestation in self.get_attestations(&thought.cid) {
        contributors.push(Contributor {
            identity: attestation.created_by,
            role: if attestation.weight > 0.0 { "endorser" } else { "challenger" },
            thought_cid: attestation.cid,
        });
    }
    
    BlameReport { contributors }
}
```

### Diff Between Versions

```rust
fn diff(&self, old: &Cid, new: &Cid) -> ThoughtDiff {
    let old_thought = self.store.get(old)?;
    let new_thought = self.store.get(new)?;
    
    ThoughtDiff {
        content_changes: diff_content(&old_thought.content, &new_thought.content),
        because_added: new_thought.because.difference(&old_thought.because),
        because_removed: old_thought.because.difference(&new_thought.because),
        editor: new_thought.created_by,
        timestamp: new_thought.created_at,
    }
}
```

### Accountability Chain

Every rework is signed. Every attestation is signed. Immutable.

```
Claim disputed?
  → Walk rework chain: who edited what, when
  → Walk because chain: what sources were cited
  → Check attestations: who endorsed/challenged
  → Verify signatures: cryptographic proof of authorship
  
No hiding. No "I never said that." Receipts all the way down.
```

---

## Part 9: Identity Management

### Key Generation

Ed25519 keypair. Public key in identity thought.

### Social Recovery

Designate N trusted identities. M of N can attest key rotation.

```json
{
  "type": "connection",
  "content": {
    "relation": "recovery_delegate",
    "from": "your_identity",
    "to": "trusted_identity"
  }
}
```

### Managed Identities

| Type | Algo Control | Keys | Graduation |
|------|--------------|------|------------|
| Sovereign | Self | Full | Default |
| Managed (child) | Parent | Escrow | Age + attestation |
| Managed (employee) | Policy | Delegated | Tenure |
| Managed (AI) | Creator | None | Earned trust |
| Scoped | Inherited | Session | Task completion |

### Proof of Life

Periodic attestation of activity. Watchdog can trigger:
- Alert to contacts
- Key rotation to delegates
- Dead man's switch

### Per-Identity Encryption

Content keys can be encrypted directly to a recipient's public key (Ed25519 → X25519 derivation):

```
Content encrypted with random symmetric key K
  → K encrypted with recipient's X25519 public key
  → Only THAT identity can derive K
  → Leaked blob + different identity = noise
  → Leaked blob + same identity = forensic trail
```

Combine with timed access (see Implementation Notes): know WHO had access WHEN with cryptographic proof. Attestation chain proves who was granted access. Encryption proves only they could have decrypted. Not logs. Maths.

### Ergo Cognito Sum

*"I am known, therefore I am."*

Descartes inverted. WoT identity is not asserted — it emerges:

| Depth | State | Meaning |
|-------|-------|---------|
| Keypair only | Ghost | Can sign, but no presence |
| Self-signed identity | Claimed | "I assert I exist" |
| Vouched by others | Recognized | "You exist to us" |
| Thoughts with attestations | Witnessed | "Your thinking is seen" |
| Deep graph (thousands of thoughts) | Soul | "You ARE your trails" |

**Identity IS cognition made visible.**

A shallow identity (pubkey + name) is authentication. A deep identity (pubkey + 50k thoughts + attestations + aspects + vouches) is a person. Export those trails → import to new agent → agent thinks like you.

The soul is portable because it's data. Receipts all the way down.

---

## Appendix A: Canonical JSON

For CID computation:
1. Keys sorted alphabetically
2. No whitespace
3. No trailing commas
4. Unicode escaped as `\uXXXX`

```python
canonical = json.dumps(obj, sort_keys=True, separators=(',', ':'))
```

---

## Appendix B: CID Computation

```python
import blake3

def compute_cid(thought: dict) -> str:
    canonical = json.dumps(thought, sort_keys=True, separators=(',', ':'))
    h = blake3.blake3(canonical.encode()).hexdigest()
    return f'cid:blake3:{h}'
```

---

## Appendix C: Signatures

```json
{
  "thought_cid": "cid:blake3:...",
  "signer": "cid:blake3:...",
  "algorithm": "ed25519",
  "signature": "base64...",
  "timestamp": 1706745600000
}
```

Signature covers: `thought_cid + signer + timestamp` (concatenated UTF-8).

---

## Version History

| Version | Changes |
|---------|---------|
| 0.10 | Three attestation-driven patterns. Response schemas. Per-identity encryption. Attention requests expanded. Schema-layer additions only — no primitive changes. |
| 0.9 | Split into core/integrations/implementation. Source as CID. ContentRef for because. Git blame for all media. |
| 0.8 | Removed visibility field. Structural access. |
| 0.7 | Rework chains. Trust computation. |
| 0.6 | Self-describing schemas. Archival resilience. |

---

**Git blame for all media. Receipts all the way down.**

*Ergo cognito sum.*

---

*End of Core Specification v0.10*
