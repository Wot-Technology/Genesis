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

### Full Fat vs Diff Thoughts

Git solved this. We inherit.

**Storage modes:**
```
Full fat thought:
  content: "The entire document"
  size: 50kb
  use: archival, checkpoints, sharing

Diff thought:
  content: { op: "replace", path: "/section/3", value: "new text" }
  about: [previous_version_cid]
  size: 200 bytes
  use: real-time collab, efficient sync
```

**Connection metadata tells downstream what to expect:**
```
Connection {
  from: [thought_a]
  to: [thought_b]
  type: "revision"
  expects: "diff"  // receiver knows before fetching
}
```

**Reconstruction:**
Walk back through diffs to full fat checkpoint, apply forward.
OR hit intermediate checkpoint, shorter walk.

**Self-describing (again):**
```
schema: "diff/json-patch-v1"   // I'm a diff, here's how to apply
schema: "document/markdown-v1" // I'm the whole thing
```

**Bandwidth:**
- Real-time collab: stream tiny diffs
- Initial sync: fetch checkpoint + recent diffs
- Archival: full fat at intervals
- Offline reconnect: "diffs since [last_cid_i_have]"

Same primitive. Mode = content schema + connection type.

### WoT Identity → Client Certs → IPv6 Access

Not speculative. Same crypto. Same keys.

ed25519 keypair works for:
- WoT identity (did:key:z6Mk...)
- TLS client cert (derived from same key)
- IPv6 access grants (attestation controls firewall)

**Access grant as thought:**
```
Thought: "Grant network access"
  type: access_grant
  identity: [peer_identity_cid]
  resource: ipv6:2001:db8::1/128
  protocol: [sync, query]
  expires: 2026-02-28
  attested_by: [network_owner]
```

**Sync partner selection:**
```
Thought: "Sync partnership"
  type: sync_grant
  partner: [their_identity_cid]
  pools: [pool_1, pool_2]
  transport: { ipv6: "...", onion: "..." }
```

Revoke attestation → cert invalid → connection refused → sync stops.

**The collapse:**
```
OLD: 5 identity systems (login, API key, VPN, firewall, certs)
WOT: 1 identity, attestations grant capabilities

Client cert IS your WoT identity.
Firewall rule IS a WoT attestation.
ACL IS the trust graph.
```

No separate access control. The graph IS the ACL.
Computed trust, enforced at packet level.

Same cert tech. Just unified.

### Hallucination Ceiling vs WoT Floor

Stanford paper: "LLMs will always hallucinate" (diagonalization proof)
For any countable set of models, construct function that breaks all.
Math checks out. But it's about worst case — arbitrary functions, arbitrary inputs.

**The JPEG reframe (sergebevzenko):**
```
"You can't losslessly compress arbitrary data either.
 That's been proven for decades.
 And yet JPEG exists and works perfectly fine for photos.
 
 Because photos aren't arbitrary data.
 And the questions we ask LLMs aren't arbitrary functions."
```

**Ceiling vs Floor:**
- Paper proves ceiling — impossible in general case
- Practical AI is about floor — guarantees in specific domains
- Floor builders: formal verification, constrained decoding, tests, tool use
- "Not because they beat the ceiling, but because they define a smaller room."

**The benchmark problem:**
```
MMLU, GPQA, MATH — none have "I don't know" option
Model says "I don't know" = same score as wrong answer
Rational strategy: always guess confidently
"We literally train models to fake certainty."
```

**WoT defines a smaller room:**
```
HALLUCINATION               WOT FLOOR
─────────────────────────────────────────
No "I don't know"           Attestation weight = confidence
                            No attestation = "I don't vouch"
                            
Pure generation             Tool use (walk because trails)
                            Retrieval with provenance
                            
Arbitrary functions         Constrained domain (things with trails)
                            
Fake certainty              "Show your work"
                            Because chain or it didn't happen
                            
Benchmarks reward guessing  Attestation rewards humility
```

**The real question:**
"Are we even measuring the right thing?"
- Current benchmarks: Can you sound confident?
- WoT benchmark: Can you show your work?

The ceiling is real. WoT raises the floor.
Hallucination without attestation = flagged.
Hallucination with empty because trail = visible.
Human checkpoint for high-stakes = required.

arxiv.org/html/2511.12869v2

---

### Multiplex Networks — Academic Validation of WoT Trust Model

Source: @dr.annamariamatziorinis (network science researcher) - Threads, Jan 2026

**Core concept:**
"In network science, a multiplex network is when the same people are connected through multiple distinct layers simultaneously. You don't have one relationship. You have emotional, practical, historical, and proximity layers, each with its own structure."

**Key insights:**

1. **Layer independence**: Same nodes, different topology per layer
   - You don't hold the same position in every layer
   - Central in emotional support ≠ central in collaboration

2. **Layer interdependence**: "What happens in one affects the others"
   - Work conflict → emotional distance → withdrawal from shared activities
   - Strain propagates across layers

3. **Layer-specific failures**: "Most tension isn't about the whole person, but the specific layer failures"
   - Emotional intimacy: strong
   - Professional boundaries: failed  
   - Daily expectations: misaligned
   - "You don't have one broken relationship. You have specific layer failures."

4. **Boundaries as layer management**: "You can remove one layer without destroying the whole connection"
   - Keep: emotional support
   - Remove: work collaboration
   - Reduce: daily contact
   - Maintain: care + history

**The reframe:**
```
The question isn't: "Should I keep this person?"
The question is: "Which layers belong here?"

Your relationships are multiplex.
Your boundaries can be too.
```

**WoT mapping:**

| Multiplex Networks | WoT |
|--------------------|-----|
| Nodes | Identities |
| Layers | Aspects |
| Layer-specific edges | Connection + aspect weights |
| Layer position | Trust weight per aspect |
| Layer failure | Low/negative aspect weight |
| Boundary adjustment | Aspect attenuation |
| Layer interdependence | Aspect correlation / propagation |

**WoT implementation:**
```
Connection {
  from: [my_identity],
  to: [their_identity],
  type: "trusts",
  aspects: {
    technical: 0.9,
    political: 0.2,
    emotional: 0.7,
    professional: 0.5,
  },
  because: [evidence_cids],
}

// Boundary = aspect management
attenuate(connection, aspect: "professional", factor: 0.2)
// Keep technical trust, reduce professional exposure
```

**Why this matters:**
- Academic validation that multi-aspect trust is how relationships actually work
- WoT's aspect model isn't arbitrary — it maps to network science
- "Trust on what?" is the right question, not "trust or not?"

---

### WASM LLM Engines — State of Play (Jan 2026)

**Mature options:**

1. **WebLLM** (mlc-ai) — github.com/mlc-ai/web-llm
   - WebGPU + WASM hybrid, 80% native performance
   - OpenAI-compatible API, structured JSON generation
   - Models: Llama 3, Phi 3, Gemma, Mistral, Qwen
   - Best for: GPU-enabled browsers

2. **wllama** (ngxson) — github.com/ngxson/wllama
   - Pure llama.cpp → WASM, GGUF format
   - No GPU required (SIMD only)
   - Completions, embeddings, tokenization
   - 2GB file limit (split for larger)
   - Best for: Cross-browser, CPU-only

3. **picoLLM** (Picovoice) — picovoice.ai
   - Cross-browser (Chrome, Safari, Firefox, Edge, Opera)
   - Custom quantization (outperforms GPTQ)
   - Works WITHOUT WebGPU
   - Best for: Maximum compatibility

4. **Transformers.js + Voy**
   - HuggingFace ecosystem + WASM vector store
   - RAG entirely on-device
   - Best for: Retrieval pipelines

**The 3W Stack** (Mozilla, Aug 2025):
WebLLM + WASM + WebWorkers
- Model inference in worker, agent logic compiled to WASM
- UI never blocked, nothing leaves device
- "What if we shipped models to browsers entirely?"

Source: blog.mozilla.ai/3w-for-in-browser-ai-webllm-wasm-webworkers/

**Constraints:**
- 2GB ArrayBuffer limit (split models)
- WebGPU not universal yet
- Multi-thread needs COOP/COEP headers
- Q4/Q5/Q6 quantization recommended

**WoT subconscious layer:**
- wllama for retrieval/indexing/embeddings (CPU, universal)
- WebLLM for reasoning when GPU available
- Private checkpoints processed entirely local

---

### HILIO & Mannaz — Pattern Convergence Across Representations

Source: @dr.annamariamatziorinis (Hidden Information Labs Institute) - Threads, Jan 2026

**HILIO logo — emergent structure:**

"The symmetry isn't decorative. It reflects reciprocal agents with equal capacity, connected through a shared constraint space rather than hierarchy. A minimal dyadic structure stabilized by feedback, the smallest unit from which networks emerge."

"Humans are not units. They are networks."

**Key principles encoded:**
- Reciprocal agents with EQUAL capacity (not hierarchy)
- Each side mirrors the other = bidirectional influence
- Central axis = shared constraint space
- Common context/rules that coordinate WITHOUT centralized control
- Minimal social unit: dyad stabilized through mutual feedback
- Larger networks emerge from this primitive

**Mannaz (ᛗ) — Norse rune:**

"Mannaz in Norse tradition signifies humankind as a relational whole. It reflects the belief that a person becomes fully human through community, reciprocity, and shared responsibility, not in isolation. Wisdom, identity, and order arise through mutual recognition among people, and imbalance comes from separation from the social fabric."

**The emergence (unintentional convergence):**

"Funny enough, we didn't set out to choose a symbol. This form emerged through iterative network designs, variations on relational structures, feedback, and symmetry that already underpin our research. When this configuration appeared, it resonated not because of symbolism, but because it was structurally coherent with how we understand human systems."

"Only later did we recognize its resemblance to Mannaz, a runic symbol historically associated with the human in relation, rather than the isolated individual."

"That convergence wasn't intentional, perhaps an example of an underlying pattern revealing itself across different representations..."

**Window of tolerance / network capacity:**

"Your window of tolerance determines if stress spreads through your network or gets absorbed."

- High-capacity nodes metabolize disruption
- Low-capacity ones amplify it
- Build your window → Change your network → Shape systems

**WoT mapping:**

| HILIO / Mannaz | WoT |
|----------------|-----|
| Reciprocal agents | Mutual attestation |
| Equal capacity (not hierarchy) | Peer identities, no master node |
| Bidirectional influence | Because chains go both ways |
| Shared constraint space | Pools with rules |
| No centralized control | No platform owns the graph |
| Dyad → networks emerge | Connection → trust graph emerges |
| Humans are networks | Identity IS the graph |
| Minimal social unit | Thought = minimal unit, Because = minimal relation |
| High-capacity metabolizes disruption | High-trust nodes absorb bad attestations |
| Low-capacity amplifies | Low-trust nodes cascade failures |

**Pattern convergence:**

Three independent paths to same structure:
1. WoT: distributed systems, memory, trust computation
2. HILIO: network science, human systems research  
3. Mannaz: Norse observation of social fabric (ancient)

Same underlying pattern. Different entry points. Different eras.

"An underlying pattern revealing itself across different representations"

This is how you know the structure is real — when independent investigations converge on the same form.

---

### eBPF & Istio — Transport Layer Learnings for WoT P2P

Source: Istio docs, eBPF research, Podostack substack

**Core insight: The sidecar debate is about WHERE to put logic**

| Approach | Location | Trade-off |
|----------|----------|-----------|
| Traditional (Istio) | Sidecar per pod (user space) | Isolated but expensive |
| eBPF | Kernel-level | Fast but constrained |
| Hybrid (Ambient) | Split by layer | Best of both |

**Performance numbers:**
- eBPF pub/sub: 3× throughput, 2-10× lower latency
- Istio sidecars: +2.65ms per hop (90th percentile)
- eBPF socket bypass: up to 20% better throughput

**Key architectural patterns:**

1. **Layer Splitting**
   - L3/L4 (routing, mTLS tunnels) → kernel/eBPF (fast, simple)
   - L7 (HTTP, complex policies) → user space proxy (flexible)
   - WoT: Transport/discovery fast, trust computation in application layer

2. **Socket-to-Socket Bypass**
   - Instead of: App → TCP stack → netfilter → TCP stack → Sidecar
   - Use: App socket ↔ Sidecar socket (direct via eBPF sockops)
   - WoT: Same-node thoughts bypass full network traversal

3. **Per-Node vs Per-Pod**
   - Sidecar: One proxy per workload (isolated, expensive)
   - Node proxy: Shared proxy per node (efficient, shared fate)
   - WoT: Per-identity agent vs per-node daemon trade-off

4. **Map-of-Maps State Management**
   - Outer: topic_name → inner_map_fd
   - Inner: subscriber_ip:port → exists
   - WoT: aspect → connection_map, identity → trust_weights

**The mTLS lesson:**
"MTLS is not something you can do efficiently today in the kernel" — Louis Ryan, Solo.io

Crypto stays user space. Routing can go kernel. WoT: ed25519 signing stays application layer.

**The "not Turing-complete" constraint:**
eBPF programs are deliberately LIMITED: must terminate, verifier checks, sandboxed.
WoT: Pool rules should be similarly constrained — verifiable, terminating, predictable.

**Architecture for WoT transport layer:**

```
┌─────────────────────────────────────────────────┐
│  APPLICATION LAYER                              │
│  Trust computation, attestation, reasoning      │
│  (Complex, Turing-complete, agent logic)        │
├─────────────────────────────────────────────────┤
│  PROTOCOL LAYER                                 │
│  Thought resolution, CID routing, pool rules    │
│  (Constrained, verifiable, deterministic)       │
├─────────────────────────────────────────────────┤
│  TRANSPORT LAYER                                │
│  Discovery, connection, encryption tunnel       │
│  (Can benefit from eBPF-style optimization)     │
│  DNS/Onion/IPFS fallback chain                  │
└─────────────────────────────────────────────────┘
```

Same pattern as Istio Ambient: ztunnel equivalent (lightweight per-node identity daemon), waypoint equivalent (full agent for complex trust computation).

**The Merbridge trick:**
"Since eBPF cannot take effect in a specified namespace, the change will be global"
Solution: Control plane watches pods, maintains local_pod_ips map — only intercept for known-managed pods.

WoT: Only intercept/route for identities in local trust graph. Unknown falls through to standard networking. Graph membership IS the routing policy.

Reference: https://istio.io/latest/docs/ambient/architecture/

---

### Synapse Decompilation — The Zuckerberg Pattern (2001-2002)

Source: @itscharlie.nyc thread (Threads, Jan 2026, 9K views)

**Architecture: "Frankenstein"**
- Frontend: Visual Basic 6 (the glue)
- Backend: C++ COM DLL (the brain)
- Visuals: Java Applet (the "neural net")
- "3 languages trench-coated together via Windows COM"
- D'Angelo handled Java, Zuck the UI + glue code

**The "AI" — Just a Markov Chain:**
- DLL exports: `Syn_BrainGetNthRanked` — "merely a frequency counter"
- Song A → Song B: increment counter on that edge
- Song A ends: `SELECT TOP 1` on the edges
- "It was a Markov Chain implemented as a simple lookup table"

**The Confidence Hack:**
```
black_jesus_threshold = 80
```
If transition probability between two songs < 80%, the brain wouldn't risk a bad prediction. Fallback to shuffle.

"He knew that a 'smart' system that's wrong 30% of the time feels broken, but a system that only speaks when it's certain feels like AI."

**Graph Visualization — High School Physics:**
Zuck & D'Angelo were taking physics at Exeter, spliced homework formulas into Java:
- Hooke's Law: spring forces pull related songs together
- Coulomb's Law: electrostatic repulsion keeps nodes from overlapping
- Simulated annealing: thermal energy (random displacement) to escape local minima
- "Scramble & shake buttons weren't just randomizers"

**The $950K Microsoft Offer:**
Harvard Crimson reported MSFT offered $950K. If engineers looked at the code: "zero proprietary algorithms (just a frequency counter), a VB6 wrapper (already dying tech in 2002), & a Java Applet running inside a C++ app (a performance nightmare)."

"For high-schoolers in 2001-2002? Genuinely impressive. But Zuck knew MSFT wouldn't buy it so he open-sourced it & got some press to boost his comp sci cachet."

**The Zuckerberg Pattern:**
"Notice what people want next, ship something good enough, then iterate."

Meta bears mistake experimentation for failure because they need narratives:
- "Can't monetize mobile." → Adapted
- "Ad load tapped out." → Adapted
- "iOS privacy kills them." → Adapted
- "Reality Labs ruins them." → Adapting (AI infrastructure + Llama + agents)

**Meta's Structural Advantage for Agents:**
"They already own the rails where agents will live: Instagram, WhatsApp, Messenger. They know commerce starts in DMs, not white papers."

Agentic retail requires: distribution + identity + payments adjacency + learning system.
Meta has distribution & the loop.

"A real bear thesis would have to explain permanent impairment of that loop: a collapse in attention, advertiser ROI, or distribution. Betting against the house when it owns the attention of half the planet feels less like a calculated risk and more like financial theology."

**WoT Mapping:**

| Synapse (2001) | WoT |
|----------------|-----|
| Edge counters (A→B frequency) | Trail reinforcement |
| Markov chain on transitions | Because chains strengthen paths |
| Confidence threshold (80%) | Attestation weight thresholds |
| Fallback to shuffle when uncertain | "I don't know" when no strong attestation |
| Force-directed graph visualization | Same physics for thought graphs |
| Simulated annealing | Thermal exploration of belief space |
| "Only speaks when certain" | No attestation = no claim |

The perception insight from 2001: Don't guess. Only assert what you can back up. Silence > confident hallucination.

This is the WoT floor principle, discovered empirically by a high schooler building a music app.

---

### Local STT/TTS Stack for Agents — Jan 2026

Source: Various benchmarks, GitHub repos, community research

**STT (Speech-to-Text) Options:**

| Implementation | Time (s) | Notes |
|----------------|----------|-------|
| fluidaudio-coreml | 0.19 | Fastest (CoreML native) |
| parakeet-mlx | 0.50 | MLX native |
| mlx-whisper | 1.02 | MLX whisper |
| insanely-fast-whisper | 1.13 | MPS + quantized |
| whisper.cpp (CoreML) | 1.23 | Standard setup |

**Whisper.cpp on M1:**
- Large model: ~10× realtime (10min audio = ~1min processing)
- With CoreML: additional 2-3× speedup
- Model recommendations: Medium for balance, Small if RAM constrained

**TTS (Text-to-Speech) Options:**

**Kokoro-82M** — Fast & Good:
- 82M params = tiny, runs on CPU
- M1 MacBook Air: 0.7× realtime (faster than speech)
- 54 voices, 8 languages
- Apache 2.0 license
- MLX version: `mlx-community/Kokoro-82M-bf16`

**Qwen3-TTS** — Quality King (but heavy):
- 0.6B and 1.7B models
- 97ms first packet latency (streaming)
- 10 languages + dialects, voice cloning from 3 seconds
- NEEDS RTX 3090+ for real-time
- CPU: RTF 3-5× (too slow for M1)

**Chatterbox** — Voice Cloning:
- 5-second voice clone
- <200ms TTFB on good hardware
- MIT license

**Recommended M1 Stack:**
```
pip install mlx-audio

# STT
from mlx_audio.stt.generate import generate_transcription
result = generate_transcription(
    model='mlx-community/whisper-large-v3-turbo-asr-fp16',
    audio='test.wav'
)

# TTS
mlx_audio.tts.generate \
  --model mlx-community/Kokoro-82M-bf16 \
  --text "Hello" --voice af_heart --play
```

mlx-audio does both STT and TTS, native MLX, optimized for Apple Silicon.

---

### SERA — Soft Verified Coding Agents (AI2)

Source: AI2 Open Coding Agents, Jan 30, 2026
Paper: arxiv.org/pdf/2601.20789
Repo: github.com/allenai/sera-cli

**What is SERA?**

Repository-level coding agents via supervised training only. No RL, no test suites, 40 GPU-days total.

**Performance:**
- SERA-32B: 49.5% on SWE-bench Verified (32K context)
- SERA-32B: 54.2% on SWE-bench Verified (64K context)
- Matches Devstral-Small-2 (24B) and GLM-4.5 Air (110B)
- Fully open: code, data, weights (Apache 2.0)
- Built on Qwen 3 32B

**Soft Verified Generation (SVG) — The Core Trick:**

Traditional approach needs test suites and RL loops. SVG uses patch agreement between two rollouts as soft verification signal.

Process:
1. Sample function from real repo
2. Teacher (GLM-4.6) produces trajectory T1, patch P1
3. Convert trajectory → synthetic PR description
4. Teacher starts fresh, only sees PR description
5. Produces T2, patch P2 from PR description alone
6. Compare P1 and P2 line-by-line

Soft verification score `r` = fraction of P1 lines appearing in P2.

**Key Finding:** Even r=0 trajectories are valuable for training!

"Realistic multi-step traces, even if noisy, are valuable supervision for coding agents."

**Cost Comparison:**

| Method | GPU-days | Relative Cost |
|--------|----------|---------------|
| SVG (SERA) | ~40 | baseline |
| SkyRL-Agent | ~1,040 | 26× more |
| SWE-smith | ~2,280 | 57× more |

**Repository Specialization:**

Can fine-tune to specific repos with ~8K trajectories:
- Django: 52.23% (vs 51.20% teacher) — student beats teacher
- SymPy: 51.11% (vs 48.89% teacher)

**WoT Parallels:**

| SERA Insight | WoT Parallel |
|--------------|--------------|
| Soft verification works (r=0 still valuable) | Attestation doesn't need to be binary |
| PR description as interface | Because trail as interface |
| Two rollouts for verification | Two paths to same thought (cross-attestation) |
| Repository specialization | Pool specialization |
| Trajectories > unit tests | Trails > point-in-time snapshots |

The "soft verification via patch agreement" pattern: generate two independent solutions, compare overlap. Works without ground truth tests.

Matches the `black_jesus_threshold = 80` insight from Synapse: you don't need perfect verification, you need realistic process traces.

---

### OLP / OpenLine Protocol — Structural Triage for Thought Graphs

Source: github.com/terryncew/openline-core, github.com/terryncew/COLE-Coherence-Layer-Engine

**What it is:**
"Geometry-first wire" for AI agent coordination. Agents emit frames (typed graphs), get back 5-number digest + telemetry.

**The Digest:**
- `b0` — base connectivity
- `cycle_plus` — circular reasoning detection (>0 = RED)
- `x_frontier` — expansion frontier
- `s_over_c` — support-to-claim ratio
- `depth` — reasoning chain length
- `ucr` — unsupported claim ratio

**Telemetry:**
- `κ (kappa)` — stress (density outrunning structure)
- `Δhol` — holistic drift between runs
- `evidence_strength` — quality of support
- `del_suspect` — suspicious deletions

**Guard Policy:**
```
RED if:
  cycle_plus > 0                    # Circular reasoning
  OR (Δhol ≥ 0.35 AND del_suspect)  # Drift + deletions
  OR (κ ≥ 0.75 AND UCR ≥ 0.40 AND ES < 0.25)  # Stress + unsupported + weak
```

**WoT Integration:**

OLP covers pre-verification structural health. Fits in the pipeline:

```
INGEST          Thoughts arrive thick and fast, store immediately
    ↓
OLP TRIAGE      Structural health check (cycles, UCR, stress)
    ↓           Output: priority queue for verification
SUBCONSCIOUS    Background agents churn through:
    ↓           - Verify identities in because chains
    ↓           - Precompute trust weights  
    ↓           - Decode trails for indexing
    ↓           - Summarize, link ancillary info
    ↓           - Curate hot paths
WORKING MEMORY  Verified thoughts, salience-ranked
    ↓
CONSCIOUS       "What do I know about X?" → right thoughts surface
```

**The insight:**
OLP tells subconscious agents WHERE to focus:
- High UCR → needs because-finding
- High κ → graph growing faster than verification capacity
- cycle_plus > 0 → structural problem, don't verify yet

**Personal Search Index Optimizer:**

All this machinery = your personal SEO. Ranking factors you control:
- Trust weight (your attestation chains)
- Heat (recency, access frequency)  
- Salience (context relevance)
- Structural soundness (OLP metrics)
- Aspect match (trust-on-what)

The subconscious layer IS your algorithm. Runs on your hardware, your trust graph, indexing your thoughts. The janitor works for you, not advertisers.

---

### CooperBench — Multi-Agent Coordination Failures

Source: cooperbench.com, Stanford + SAP Labs, Jan 2026
Paper: arxiv.org/abs/2601.13295

**Key finding:**
GPT-5 and Claude Sonnet 4.5 achieve only 25% success with two-agent cooperation — roughly 50% lower than single agent handling both tasks.

**Three capability gaps:**

| Failure Type | Frequency | Description |
|--------------|-----------|-------------|
| Expectation failures | 42% | Agents fail to integrate partner state info |
| Communication failures | 26% | Questions go unanswered, breaking decision loops |
| Commitment failures | 32% | Agents break promises or make unverifiable claims |

**Communication paradox:**
Agents spend up to 20% of budget on communication. Reduces merge conflicts but doesn't improve success. Channel jammed with repetition, unresponsiveness, hallucination.

**The insight for WoT:**

Separate action from accountability:
- One agent responsible for ACTION
- Another agent responsible for VERIFICATION against stated commitments

This maps to:
- Attestations as verifiable commitments
- OLP-style checks: "did you deliver what you said?"
- Subconscious verification agents testing promises

**Commitment failures (32%) are the target:**
```
Agent A: "I will implement feature X"
         ↓
         [does work]
         ↓
Agent A: "I implemented feature X"
         ↓
Agent B: [verifies against original promise]
         ↓
         "Claim: implemented X"
         "Evidence: [code diff]"
         "Promise: [original commitment CID]"
         "Match: true/false"
```

The because chain becomes the receipt. The verification agent doesn't need to understand the work — just whether the promise was kept.

**WoT framing:**
- Promise = Thought with commitment content
- Delivery = Thought with because → promise
- Verification = Attestation linking delivery to promise with match score

Structural accountability without requiring agents to "understand" each other — just verify receipts.

---

### Dual Chain Structure — Because vs Rework

**Two parallel chains on every thought:**

```
THOUGHT (published version)
│
├── because_chain: [WHY this exists]
│   → source material
│   → conversation context  
│   → prior thoughts that led here
│
└── rework_chain: [HOW this became this]
    → v3: "The protocol preserves edit history"
    → v2: "The protocl preserves edit hstrry"
    → v1: "teh protocol keeps edits"
    → v0: [raw keystroke stream, optional]
```

**Capture mode spectrum:**

```
LOSSY                                              LOSSLESS
  │                                                    │
  ▼                                                    ▼
Final only ─── Major edits ─── All edits ─── Keystrokes
```

**Key insight: Pool rules, not protocol rules**

The protocol supports full fidelity. Pools declare what they accept.

```yaml
pool:
  id: "legal-contracts"
  rules:
    capture_mode: "keystream"
    rework_chain: required
    min_because_depth: 2
    
pool:
  id: "shitposting"
  rules:
    capture_mode: "final"
    rework_chain: optional
    because_chain: optional
```

**Pool as contract:**
- On entry, pool announces requirements
- Client conforms or finds another pool
- No protocol-level enforcement of detail level
- That's pool culture, announced at the door

**What this enables:**
- Research pools: full keystroke capture for cognitive analysis
- Legal pools: immutable edit history for audit
- Creative pools: process visible, "show your work"
- Casual pools: just the final thought, no history
- Private pools: your rules

**Corrections model:**
```
Original: "teh quick brown fox" [immutable, stays in graph]
    ↓
Correction: {
  type: "correction",
  original: [cid_of_typo],
  proposed: "the quick brown fox",
  reason: "typo",
  from: [bot_identity OR human_identity]
}
    ↓
Acceptance: {
  type: "attestation", 
  accepts: [correction_cid],
  from: [original_author]
}
```

No silent rewrites. Original always there. Corrections are proposals. Author accepts or rejects. Bot contributions visible. Arguable — someone can contest a correction with their own attestation.

**The protocol is the wire format. Pools are the social contracts.**


---

### Corrections as Annotated Training Data

Every autocorrection carries provenance:

```yaml
correction:
  original: [cid_of_typo]
  proposed: "the quick brown fox"
  model: "autocorrect/gboard/3.2.1"
  accepted: true | false
  by: [human_identity]
  context: [surrounding_thought_cid]
  pool: [pool_id]  # domain signal
```

**What this produces:**

| Field | Training Value |
|-------|----------------|
| original | Input example |
| proposed | Model output |
| model | Version tracking (which model, when) |
| accepted | Ground truth label |
| by | Human validator identity |
| context | Semantic context for the correction |
| pool | Domain signal (legal vs casual vs technical) |

**Why this matters:**

1. **Version-specific performance** — Track which model versions get accepted more. gboard/3.2.1 vs gboard/3.2.2 acceptance rates.

2. **Domain-specific tuning** — Corrections in legal pools have different patterns than shitposting pools. Labeled by pool.

3. **Rejection signal** — Rejected corrections are as valuable as accepted ones. "Human saw this suggestion and said no."

4. **Context-aware** — Not just "word X → word Y" but "word X in context Z with trust weight W → word Y, accepted by human with expertise in aspect A."

5. **Consent-native** — User chose to participate in pool that captures this. Not scraped.

**The flywheel:**
```
Human types → Model suggests → Human accepts/rejects
                    ↓
            Labeled example with full provenance
                    ↓
            Better models trained on consented data
                    ↓
            Better suggestions → Higher acceptance rate
```

This is the training data cliff solution applied to the correction layer. Every keystroke-to-final journey is a supervised learning dataset, perfectly annotated, with consent baked in.

