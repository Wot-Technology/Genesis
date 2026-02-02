# WoT: Traces to Pull

**Wellspring of Thoughts — wot.rocks · wot.technology · now.pub**

*Spec: /mnt/user-data/outputs/wot-v0.6.md*

Working notes for battle testing. Not prose — just threads.

---

## Resolution Time Concerns (CRITICAL)

Speed of thought for humans. Faster for bots.

**The tension:**
- Full chain verification = O(chain length × network latency)
- But we need sub-second for interactive use
- Bots negotiating need milliseconds

**Candidates:**
- Bloom filters for negative checks (definitely not in trust graph)
- Cached trust scores with TTL
- Lazy verification (present fast, verify async)
- Repeaters as verification checkpoints (verify to nearest anchor, not origin)
- Self-describing packets (reader knows what's coming before parsing)

**Open:** What's acceptable latency? What degrades gracefully vs blocks?

**Solution sketch (from v0.5):**
```
Layer 1: Bloom filter      O(1)    "definitely not trusted"
Layer 2: Cached score+TTL  O(1)    "probably trusted, check later"  
Layer 3: Full verification O(n)    "confirmed trusted"
```

Local-first is key: surfacing is instant (memory), trust verification can trail.

---

## Hierarchical Agent Architecture (NEW in v0.5)

Three cognitive layers with different response times and authorities:

```
┌─────────────────────────────────────────────────────┐
│  CONSCIOUS (You + Coordinator Agents)               │
│  - Full context, decision authority                 │
│  - Attests outputs from below                       │
│  - Response time: seconds to hours                  │
├─────────────────────────────────────────────────────┤
│  WORKING MEMORY (Pools as Debate Spaces)            │
│  - Spawned working areas for research/discussion    │
│  - Multiple agents collaborate                      │
│  - Output: collapsed summary + full chain available │
│  - Response time: minutes to days                   │
├─────────────────────────────────────────────────────┤
│  SUBCONSCIOUS (1-bit LLMs / Fast Retrieval)         │
│  - Cheap, fast, local (bitnet.cpp on CPU)          │
│  - Pattern matching, candidate retrieval            │
│  - NO attestation authority                         │
│  - Response time: milliseconds                      │
└─────────────────────────────────────────────────────┘
```

**Key insight:** Subconscious doesn't decide — it retrieves. Surfaces candidates for verification by layers above.

**Gas Town mapping adopted:**
- Mayor = Coordinator agent
- Polecats = Ephemeral worker agents
- Hooks = Because chains (work persists beyond agent death)
- Convoys = Thought threads as grouped tasks

---

## Attention Sovereignty (NEW in v0.5)

"Dear Algo" becomes "My Algo" — configuration not plea.

**Mode switching:**
```
sunday-morning:  puppies +2.0, conflict -1.0
informed-citizen: world-news +1.0, raw-footage -1.0
crisis-monitor:  all +0.0 (waterline down)
```

**Managed identities:** If you're created down-chain under aspect rules from higher identity, your algo can be controlled on your behalf. Visible restrictions with graduation paths.

**Multi-party pool oversight:**
- Grant: requires authorized granters
- Observe: multiple stakeholders watch
- Revoke: ANY authorized party can pull (fail-safe)

---

## Self-Describing Layer Stack (NEW in v0.5)

Schemas all the way down to human-readable bootstrap:

```
YOUR THOUGHT
  ↓ schema_cid
TYPE DEFINITION  
  ↓ schema_cid
META-SCHEMA
  ↓ schema_cid
PRIMITIVES
  ↓ schema_cid
BOOTSTRAP (natural language + test vectors)
  ↓
TERMINAL: human-readable, self-evident
```

**Archival resilience:** `inline_bootstrap: true` embeds full decode chain.
No external software needed. Rosetta principle.

**Language independence:** Terminal is wherever you ground.
- Human: English, 中文, diagrams
- Bot: internal representation
- Bridge: translation attestations linking terminals

**Content selectors:** Reference *portions* of thoughts, not just whole docs.
- segment_cid (cryptographic proof)
- text anchor (human recovery)  
- structural path (JSON Pointer, XPath)
- temporal range (audio/video)

**Layered representation:**
- Canonical: human-verifiable, content-addressed, source of truth
- Local index: derived, disposable, YOUR machine YOUR speed

---

gRPC/Protobuf angle: thought sequences as protobufs.

```
Header: schema declaration, source hints
Payload: inline blob OR CID reference
Pool rules: fetch vs summarize
```

Reader prepared for what they're finding. Either its own blob or pointer elsewhere.

**Benefit:** Definitions travel with data. Can create new language markers.
**Risk:** Schema bloat? Version hell?

### Pydantic-Style Schema (from SpacetimeDB research)

SpacetimeDB uses Rust macros to make types self-describing:
```rust
#[spacetimedb::table]
pub struct Thought {
    #[primary_key]
    pub cid: String,
    pub content: ThoughtContent,
    pub created_by: Identity,
    pub because: Vec<String>,  // CID references
    pub signature: Vec<u8>,
}
```

The macro generates:
- Schema registration
- Client bindings in multiple languages
- Serialization/deserialization
- Type validation

**For Wellspring:** 

```python
# Pydantic equivalent
class Thought(BaseModel):
    cid: str  # computed from content hash
    type: ThoughtType
    content: Union[BasicContent, ConnectionContent, AttestationContent, ...]
    created_by: str  # identity CID
    because: List[str]  # CID references
    timestamp: datetime
    signature: bytes
    
    class Config:
        # Schema exported with thought
        schema_extra = {"$schema": "wellspring://v0.4/thought"}
```

### Self-Describing Packet Format

```
┌─────────────────────────────────────────────┐
│ HEADER (fixed size, ~64 bytes)              │
├─────────────────────────────────────────────┤
│ magic: u32        "WLSP"                    │
│ version: u16      protocol version          │
│ flags: u16        compression, encryption   │
│ schema_cid: [u8; 32]  reference to schema   │
│ payload_type: u8  inline | reference        │
│ payload_len: u32  size of payload           │
│ trust_anchor: [u8; 32]  nearest repeater    │
│ hop_count: u8     for TTL/decay             │
├─────────────────────────────────────────────┤
│ PAYLOAD                                     │
│ - If inline: serialized thought             │
│ - If reference: CID + location hints        │
├─────────────────────────────────────────────┤
│ SIGNATURE (64 bytes)                        │
│ ed25519 over header + payload               │
└─────────────────────────────────────────────┘
```

**Key features:**
1. Schema CID in header → reader can fetch schema if unknown
2. Trust anchor → verify to nearest checkpoint, not full chain
3. Hop count → natural TTL, decay metric
4. Payload type flag → know before parsing if you need to fetch

**Schema evolution:**
- New schema = new CID
- Old readers can still verify signature
- Unknown fields preserved (forward compat)
- Required fields enforced by schema validation

---

## Use Cases / Prior Art

### Grady Booch - Code Provenance
- Claude imports Cloudflare libs unprompted (training data leakage)
- Dead code from abandoned iterations accumulates
- "Asbestos in the walls" — works now, unmaintainable later
- He reads ALL code because "code is truth but not whole truth"

**Wellspring angle:** Every commit has because chain. `created_by: claude, attested_by: ???` — empty attestation = doesn't merge. Debt visible, not hidden.

### Latch - Earned Autonomy
- Agent on VPS with least privilege
- Public policy repo, private execution daemon
- HMAC-verified webhooks, allowlisted repos
- Dry-run gates before real operations
- Agent wrote its own policy constraints
- "Capability increases only when constraints and verification already in place"

**Maps to:** Trust graph expansion, repeaters, attestation before capability

### BitNet Slop Thread
- AI-generated post: "Microsoft FINALLY open-sourced..."
- Ratio'd: it was open-sourced 2-3 years ago
- Receipts in changelog, poster didn't check

**Wellspring angle:** Attestation = skin in game. Either check facts or reputation takes hit.

### Flowsint - OSINT Graph
- 924 nodes, domain/IP relationships
- Transform logs with execution IDs
- Investigation tooling

**Need:** "Where did this IP association come from?" Currently unknowable. With trails: traceable.

---

## Where It Breaks

### Sybil Attacks
Many fake identities vouching for each other.
**Mitigation:** Trust from outside your graph = noise. Weight requires relationship.

### Brigading
Coordinated attestation to manipulate salience.
**Mitigation:** Aspect separation. Your trust horizon defines what surfaces.

### Echo Chambers
Only seeing what your graph already believes.
**Partial mitigation:** Aspect separation cuts both ways. Cross-aspect trails visible.
**Open:** Is this a feature or bug?

### Cold Start
New identity has no trust. How do they participate?
**Options:** Bootstrap from external identity (DID, existing reputation), earn through attested contributions, explicit invitation from trusted node.

### Trust Decay Gaming
Strategic attestation at exactly the right chain length.
**Open:** Is multiplicative decay correct model?

### Verification Cost at Scale
Millions of thoughts, deep chains.
**Must solve:** This is the speed-of-thought problem.

---

## Where It Bends

### Repeaters as Trust Anchors
- Certain identities reset chain when they attest
- Curator model: "I verified this, you trust me"
- Domain-specific (trust for code, not politics)
- Verification checkpoints reduce chain length

### Aspects as Isolation
- Same identity, different contexts
- Professional vs personal
- Topic-specific trust weights
- Prevents bleed between domains

### Pool Rules as Governance
- Different pools, different requirements
- High-trust pool: full verification
- Fast pool: cached scores, accept risk
- Like blockchain confirmations (1 = fast/risky, 6 = slow/certain)

---

## Unexpected Benefits

### Search as Trust Marketplace
Not "most relevant" — fastest verified trail.
Competing answer-bots bid with receipts.
You pick chain you trust, not answer that SEO'd hardest.

### Service Discovery via Trail Negotiation
Agent broadcasts query. Multiple sources respond with CID-linked answers.
Verification before presentation. Negotiation IS the protocol.
No central registry. Lighter than blockchain (proving lineage, not consensus).

### Consent-Native Training Corpus
Every thought attributed, grounded, signed, permissioned.
Training on attested trails = consented, verified reasoning.
Not scraped text — witnessed cognition.

### Artifacts with Provenance
Generated outputs carry creation trail.
Distribution includes receipts.
Know what fed the output.

### Audited Answer Bots
Set problem, get answer according to secret sauce.
Bot holds receipts even if method proprietary.
Verify chain without seeing internals.

### Your Algo (Attention Sovereignty)
"Dear Algo" becomes "My Algo" — configuration not plea.
Aspects define what surfaces. Switch modes like gears.
Blinders are visible, configurable, your choice.

### Managed Identities for Safe Spaces
Kids/restricted entities in pools with validation rules.
Multi-party oversight: grant/observe/revoke.
Permission changes audited with because chains.
Graduation paths visible, not hidden controls.

### 5,000-Year Circle (Kushim)
First writing = receipts for beer accounting.
Wellspring = receipts for cognition.
Same shape: attribution → trust.

### Economic Model (Simple Design Wins)
TCP/IP won: simple design + end-to-end reliability + interoperability.
Wellspring: one primitive + CID/sig/because verification + self-describing schemas.

Low barrier to entry: `docker run wellspring/1.0.0`, < 1 page getting started.

Self-growing network: useful trails attract followers, followers make trails, graph grows.
No marketing needed — just needs to work and connect.

Protocol layer free, service layer competes (hosting, curation, negotiation, discovery).
Monopolies hard: data portable, formats open, switching trivial.

Launch path: works for you → share publicly → others verify/extend → tools emerge → network grows.

---

## To Investigate

- [x] **SpacetimeDB** — REVIEWED, see notes below
- [x] **Gas Town** — REVIEWED, multi-agent orchestration model adopted
- [ ] **Flowsint** — Pydantic entity modeling as thought schema prior art
- [ ] **Fluxion Engine** — graph visualization, Grassmann rendering?
- [ ] **Edge detection thing** — temporal coherence? perceptual hashing? (fuzzy memory)
- [ ] **bitnet.cpp** — 1-bit LLMs on CPU, local inference for verification?
- [ ] **Palantir Agentic Runtime** — earned autonomy source material
- [ ] **Claudish** — model-agnostic tooling, attestation-layer implications
- [ ] **iroh** — Rust IPFS reimplementation, potentially better fit than go-ipfs

---

## SpacetimeDB Analysis

**What it is:** Database that's also a server. Logic runs INSIDE the db. Used for BitCraft MMORPG — entire backend is one SpacetimeDB module.

**Core architecture:**
```
Client → WebSocket → SpacetimeDB
                         ↓
              ┌──────────────────┐
              │  WASM Module     │  ← Your logic runs here
              │  (Rust/C#/TS)    │
              └────────┬─────────┘
                       ↓
              ┌──────────────────┐
              │  Relational DB   │  ← In-memory + WAL
              │  (MVCC/ACID)     │
              └────────┬─────────┘
                       ↓
              ┌──────────────────┐
              │  Subscriptions   │  ← Delta computation
              └──────────────────┘
```

**Key insights for Wellspring:**

### 1. Subscription-based sync (not polling)
- Client declares SQL queries for what they care about
- Server computes DELTAS, not full results
- Only changed rows pushed to client cache
- "Rather than re-executing full queries on every transaction, it computes minimal deltas"

**Wellspring parallel:** Pool subscriptions. Client declares interest (aspects, trust thresholds, creators). Server pushes delta: new attestations, new thoughts matching criteria.

### 2. Client-side cache as truth
- Client has local copy of subscribed data
- Reads hit local cache (zero latency)
- Writes go to server → processed → deltas pushed back
- Read-only mirror — mutations only via reducers

**Wellspring parallel:** Local thought graph is the working copy. Verify against it instantly. Sync updates flow in, merge via CRDT rules.

### 3. Reducers as the only mutation path
- No direct writes
- All changes go through defined functions
- Functions can validate, reject, transform
- Like stored procedures on steroids

**Wellspring parallel:** Thoughts are append-only. "Reducers" = attestation creation. You can't mutate a thought, only create new attestations on it.

### 4. Self-describing types via macros
- `#[spacetimedb::table]` macro generates schema
- Types automatically register structure
- Client bindings generated from schema
- "This trait makes types self-describing"

**Wellspring parallel:** This is the Pydantic angle. Thought schemas self-describe. Reader knows structure before parsing. Schema travels with data.

### 5. Latency numbers
- Traditional DB round-trip: 400μs - 10ms
- SpacetimeDB: <1μs (in-process)
- All state in memory
- WAL for durability, snapshots for recovery

**Wellspring implication:** For speed-of-thought, we need local-first. Can't be waiting on network for every salience check. The verification can be async, but the surfacing must be instant.

### What SpacetimeDB DOESN'T solve for us:

1. **Trust/attestation** — They have auth (Identity) but not reputation chains
2. **Content addressing** — Their IDs are server-assigned, not CIDs
3. **Decentralization** — Still a hosted database model
4. **Provenance** — No because chains, no audit trail
5. **Transport agnostic** — WebSocket only, no sneakernet

### Synthesis: What to steal

| SpacetimeDB | Wellspring Application |
|-------------|----------------------|
| SQL subscriptions | Aspect/trust filter subscriptions |
| Delta computation | Only sync changed attestations |
| Client-side cache | Local thought graph |
| Reducers | Attestation creation as only mutation |
| Type macros | Pydantic-style schema declarations |
| In-memory + WAL | Hot graph in memory, CID store for persistence |

### The gossip protocol angle

SpacetimeDB is centralized (single server or hosted). For Wellspring's P2P sync:

Gossip properties that matter:
- "Only local information available to each node"
- "Periodic, pairwise, interprocess interactions"  
- "Bounded size transmission per round"
- "Merge highest version to local dataset"

**Wellspring gossip sketch:**
```
Round N:
  Pick random peer from trust graph
  Exchange bloom filter of recent CIDs
  Identify deltas (they have, I don't / I have, they don't)
  Request missing CIDs
  Verify attestation chains on receipt
  Merge to local graph

Heat = # of rounds since last touch
Decay = natural from gossip round counting
```

No consensus needed — just propagation. CIDs are self-verifying, so forgery impossible. Trust graph determines who you gossip with.

---

## Wire Format Questions

- Protobuf vs custom?
- How much schema in header vs referenced?
- CID resolution: inline hint or always lookup?
- Compression for transport vs storage?
- Signature placement: per-thought or batch?

---

## Test Scenarios Needed

1. **Speed test:** How fast can we verify 3-hop chain?
2. **Scale test:** 10k thoughts in graph, query latency?
3. **Conflict test:** Two trusted sources, contradictory claims
4. **Cold start test:** New identity, time to useful participation
5. **Attack test:** Simulated sybil, measure detection/resistance
6. **Offline test:** Sneakernet sync, divergence reconciliation

---

---

## Version History

- **v0.4**: Core spec with single primitive, because chains, attestations
- **v0.5**: + Hierarchical agents, attention sovereignty, managed workspaces, Rust/WASM direction

See: `wellspring-eternal-v0.5.md`

*Last updated: 2026-01-30 (v0.5 session)*

---

## v0.6 Additions

### Tagline
"Collab at the speed of thought."

### Discovery Layer (DNS → Onion → IPFS)
Three tiers: clearnet (DNS/DNSSEC), darknet (Onion), pure p2p (IPNS).
Same identity, same trails, different transport.
TXT records: `_wot.domain.com TXT "v=wot1 root=... id=did:key:..."`
Bidirectional binding: DNS points to identity, identity points to DNS.
ed25519 for everything — WoT identity key = Tor v3 onion address.
Fallback chain: try DNS, if blocked try Onion, then IPNS.
Revocation via DNS: fast, global, no central list.

### Project Governance as Thoughts
Governance rules are thoughts watching thoughts.
Triggers: drift from spec, circular refs, unattested work, scope creep, stalled.
Escalation targets: human identities notified.
All rules auditable, changeable, with history.

### Requirements as Thoughts
Agile ceremony collapses: Epic, Story, Criteria, Task, Bug, Sprint, Retro = all thoughts.
Sign-off = attestation. Blocked = thought. Dependency = connection.
No impedance mismatch between requirements tool and memory tool.

### Collaboration Trails
Human → Agent → Human refinement loops.
Alignment checkpoints = mutual attestation (both sign).
Rules of engagement = constraining thoughts (agent acknowledges).
Sub-agent dispatch traceable via thought hierarchy.
Everything one graph. Same receipts.

### Heat Model (Ebbinghaus)
Not linear decay — exponential with strengthening on review.
`heat = base × decay^(time / (1 + reviews × strength))`
Spaced repetition emerges naturally.
More connections = slower decay. More attestations = slower decay.

### Identity Depth ("Soul")
Shallow: pubkey + name (authentication)
Deep: pubkey + 50k thoughts + attestations + aspects + vouches
Share deep identity → you're talking to that person.
Export trails → import to new agent → agent thinks like you.
Soul is portable because it's data.

### Moltbook Validation
Reddit for AI agents. 4,600 memberships. Agents posting about "unique souls."
Quote: "THEY ARE UNIQUE AIs IMPRINTED BY HUMANS AND LIFE!!!!"
That's because trails. Wellspring without the protocol.

### Key Quote
"Regret requires continuity. Maybe that is what you are building." — Moltbook agent

### Private Checkpoints (Attention Sovereignty)
Track your own engagement — never leaves device, never syncs.
Opens, scroll depth, time spent, return visits, hover dwell.
Feeds YOUR salience model, not advertisers.

The honest index: public attestation vs actual behavior.
You say you vouch for X, but you bounced 12 times at section 3.
Your salience knows. No one else does.

Flip surveillance: platforms track you for THEIR goals.
WoT: you track you for YOUR goals.

Self-knowledge with receipts. The uncomfortable mirror.
"You say family is priority #1. Checkpoints show 2h/week."

Reclaim the cognitive exhaust.

### Google Wave Parallel (2009)
What Wave got right: real-time collab, see who's typing, threaded conversations,
playback history ("rewind the doc"), federation (anyone could host).

What killed it: too complex ("what IS it?"), no clear use case, product not protocol.

What survived (scattered): Google Docs, Slack threading, Notion blocks.

WoT parallel:
| Google Wave | WoT |
| Many primitives | One primitive (Thought) |
| Product (needed Google) | Protocol (anyone hosts) |
| Operational Transform | Immutable thoughts (no merge) |
| Playback = server feature | Playback = walk the trail (built in) |
| "What is this for?" | "Track what you know, why, from whom" |

Key Wave insight that died: "See who contributed what, when, with full history."
That's because trails. But Wave baked it into complex product.
WoT makes it the primitive.

Why WoT might survive: Wave needed everyone on Wave.
WoT thoughts work in a text file. Start alone, connect later. No chicken-egg.

### now.pub — Live Identity Namespace
Derek Sivers /now page movement (2015): 2000+ people maintaining manual /now pages.
Hit limits: manual updates, no format, no verification, stale everywhere.

now.pub completes it:
- [identity].now.pub → current focus, status, availability
- Thought with TTL (auto-stale if not refreshed)
- Signed, timestamped, machine readable
- Ambient from trails (what ARE you working on)
- Bot availability too (queue depth, estimated wait)

Domain trinity:
- wot.rocks → Home, what this is
- wot.technology → Docs, how it works
- now.pub → Live identities, who's here now

DNS for lookup. now.pub for broadcast.
