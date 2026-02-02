# Wellspring Eternal

**A Traversal-Based Model for Persistent Memory**

*Version 0.3 — January 2026*

---

## Abstract

Wellspring Eternal is a memory architecture for humans and artificial agents based on a single insight: **memory is not storage, memory is traversal history**.

Rather than treating recall as retrieval from a database, Wellspring models cognition as walking paths through a graph of thoughts. What surfaces to conscious attention isn't what's "important" in some absolute sense—it's what's **reachable from the current context** and **coherent enough to complete**.

The system requires only two primitives: **Bubbles** (thoughts) and **Chains** (relationships with attestations). Everything else—identity, trust, importance, confidence, understanding, forgetting, sync, discovery—emerges from the graph structure, walk history, and cryptographic attestations.

This version (0.3) introduces **Trails** as first-class citizens, **Pools** as the universal organizational primitive, **Aspect-based attestations** for decomposed reasoning, **Emergent ontology** through agent proposal and human attestation, and **Inference rules** for lightweight reasoning without description logic overhead.

---

## Historical Context: Bush's Memex and the 80-Year Gap

### As We May Think (1945)

Vannevar Bush's essay "As We May Think" described the Memex—a device for building and sharing **associative trails** through information. His core insight remains unrealized 80 years later:

> "Our ineptitude in getting at the record is largely caused by the artificiality of systems of indexing. When data of any sort are placed in storage, they are filed alphabetically or numerically... It can be in only one place, unless duplicates are used."

Bush proposed selection by **association** rather than by **indexing**:

> "Selection by association, rather than by indexing, may yet be mechanized. One cannot hope thus to equal the speed and flexibility with which the mind follows an associative trail, but it should be possible to beat the mind decisively in regard to the permanence and clarity of the items resurrected from storage."

### What Bush Got Right

| Bush's Memex (1945) | Wellspring (2026) |
|---------------------|-------------------|
| "The process of tying two items together is the important thing" | Chains as the core primitive |
| "When the user is building a trail, he names it" | Named trails as traversal queries |
| "Any item can be joined into numerous trails" | Graph not tree |
| "Trails that are not frequently followed are prone to fade" | Salience decay (heat model) |
| "He inserts a comment of his own, linking it into the main trail" | Attestations on chains |
| "Photographs the whole trail out, passes it to his friend" | Export/share traversal paths |
| "There is a new profession of trail blazers" | Curated pools with verified expertise |

### What Bush Missed (That Wellspring Adds)

| Gap | Wellspring Solution |
|-----|---------------------|
| Trust/Attestation | Bush assumed single user or trusted friend. Wellspring has attestations with belief strength and because chains. |
| Multi-party trails | Bush: copy trail to friend. Wellspring: build trails together with attestations showing agreement/disagreement. |
| Framing | Bush: items are neutral. Wellspring: same item, different framing chains, attestations reveal perspective. |
| Computed trust | Bush: implicit trust. Wellspring: trust emerges from vouches, because chains, groundedness recursion. |
| AI as trail-proposer | Bush: human builds all trails. Wellspring: agent proposes, human attests. Same graph, different permissions. |

### The Wrong Turn: Hyperlinks

The World Wide Web took a wrong turn from Bush's vision:

| Hyperlink (what we got) | Trail (what Bush wanted) |
|-------------------------|--------------------------|
| One-way | Bidirectional |
| Untyped | Typed relation |
| No attribution | Who made this link |
| No annotation | Why this link |
| Decays (link rot) | Persists (your copy) |
| Can't share the path | Path is the artifact |

Wellspring completes Bush's vision: trails as first-class citizens, with trust, with AI, with multi-party collaboration.

---

## Core Insight

### The Problem with Storage Models

Traditional memory systems treat thoughts as objects to be stored and retrieved:

- Store fact X
- Index by attributes
- Query when needed
- Return matches

This fails to capture how memory actually works:

- The same fact can be inaccessible one moment and vivid the next
- "Knowing" something is different from "understanding" it
- Forgetting isn't deletion—it's losing the path
- Context determines what surfaces, not just relevance scores
- Trust in information depends on source and verification

### The Traversal Model

Wellspring reframes memory as graph traversal:

| Storage Model | Traversal Model |
|---------------|-----------------|
| Facts are stored | Thoughts exist in relation |
| Recall is retrieval | Recall is re-walking a path |
| Importance is intrinsic | Salience is positional |
| Forgetting is deletion | Forgetting is unreachability |
| Understanding is having data | Understanding is completed traversal |
| Trust is metadata | Trust emerges from attestation chains |

**Key principle**: A thought isn't "known" because it's stored. It's "understood" because you've walked to it and back, and the path made sense. It's "trusted" because the chain of attestations leads back to sources you trust.

---

## Primitives

Wellspring requires exactly two primitives. All other concepts emerge from these.

### Bubble

A node of thought. Content that exists.

```
Bubble {
  id:         hash(content + created_by)
  content:    string | pubkey | structured
  created_by: identity_bubble_id      // ALWAYS required
  created_at: timestamp
  signature:  sig | null              // null if creator can't sign
  pool:       pool_id
}
```

**Properties**:

- **Immutable**: once created, content never changes
- **Content-addressed**: ID derived from content + creator hash
- **Always attributed**: created_by is required, never null
- **Optionally signed**: signature present if creator has signing capability
- **Owned**: exists within a pool (private, shared, or public)
- **Atomic**: represents a single thought, not a collection

**Critical constraint**: Every bubble has a creator. Anonymous content is unweighable. Even "I don't know where this came from" must be represented as a known record source. Nothing enters the system without attribution.

### Chain

A relationship between bubbles, carrying attestations over time.

```
Chain {
  id:           uuid
  from:         bubble_id
  to:           bubble_id
  relation:     relation_type
  created_by:   identity_bubble_id
  created_at:   timestamp
  signature:    sig                   // required if creator can sign
  attestations: [Attestation]
}
```

**Properties**:

- **Directional**: from → to is different from to → from
- **Typed**: the relation affects how understanding propagates
- **Signed**: chains must be signed by their creator (if capable)
- **Attested**: accumulates signed beliefs over time
- **Append-only**: attestations accumulate, never overwrite

**Relation types** (core):

| Relation | Meaning | Propagation Effect |
|----------|---------|-------------------|
| `supports` | Evidence for | Confidence flows forward |
| `contradicts` | Tension with | Tension flows both ways |
| `continues` | Sequence/thread | Heat flows forward |
| `derives_from` | Source/provenance | Provenance flows backward |
| `vouches` | Trust endorsement | Trust flows forward |

**Relation types** (extended):

| Relation | Meaning | Use Case |
|----------|---------|----------|
| `member_of` | Identity belongs to pool | Pool membership |
| `published_to` | Content visible in pool | Publication |
| `federated_with` | Pools share content | Pool federation |
| `instance_of` | Specific is type of general | Ontology emergence |
| `resolves_to` | Concept becomes identity | Identity resolution |
| `proposed_for` | Option for decision | Group decisions |
| `transmitted_via` | Sync record | Multi-master sync |

### Attestation (Revised)

A signed belief about a chain, grounded in reasoning and decomposed by aspect.

```
Attestation {
  by:        identity_bubble_id      // who is attesting
  on:        chain_id | bubble_id    // what they're attesting about
  via:       aspect_bubble_id        // through what lens/reason (NEW)
  weight:    float [-1.0 to 1.0]     // how much this aspect applies
  at:        timestamp               // when
  because:   [chain_id]              // grounds for this belief
  signature: sig                     // cryptographic proof
}
```

**Key change in v0.3**: Attestations now include `via` (aspect) to decompose WHY into constituent thoughts.

**Old model (single belief)**:
```
keif attests nandos: +0.8
// Lost: Why 0.8? What aspects matter? Which reasons pull which direction?
```

**New model (aspect-decomposed)**:
```
keif attests nandos:
  via "enjoys spicy food"    → +1.0
  via "hasn't had chips"     → +1.0
  via "wants easy life"      → -0.02
  via "kids will eat it"     → +0.8
  via "parking is awkward"   → -0.3

// The "belief" is COMPUTED, not stored.
// The aspects are the data.
```

**The `because` field remains critical**: Every attestation is grounded. "I believe this via this aspect" is never floating — it points to the chains that led to that belief.

---

## Aspects

Aspects are bubbles representing values, preferences, needs, moods, and constraints. They decompose "why" into queryable, persistent, learnable data.

### Aspect Bubble

```
Aspect {
  id:        bubble_id
  type:      value | preference | need | mood | constraint
  owner:     identity_bubble_id    // personal or pool
  domain:    string                // food, logistics, social, etc.
  decay:     duration | none       // how fast it fades
  valence:   positive | negative   // I seek this / I avoid this
}
```

### Aspect Types

| Type | Persistence | Example | Decay |
|------|-------------|---------|-------|
| **Value** | Core, defining | `keif/value:family-first` | None |
| **Preference** | Persistent, flexible | `keif/preference:spicy-food` | Slow (years) |
| **Need** | Situational | `keif/need:wheelchair-accessible` | Event-bound |
| **Mood** | Transient | `keif/mood:craving-chips` | Hours to days |
| **Constraint** | Hard, binary | `sarah/constraint:vegetarian` | None, violation = veto |

### Personal vs Shared Aspects

**Personal aspects** (your values):
```
keif/aspect:enjoys-spicy
keif/aspect:wants-easy-life
keif/aspect:budget-conscious
```

**Shared aspects** (pool-level or universal):
```
pool:friday-gang/aspect:everyone-can-eat
universal/aspect:kid-friendly
universal/aspect:vegetarian-options
```

### Computing Aggregate Belief

Belief is computed from aspect attestations, not stored:

```
belief(identity, subject, context, time) =
  aggregate over attestations by identity on subject
  weighted by aspect importance in context
  adjusted by decay at time

Example:

keif on nandos:
  spicy:      +1.0  × importance 0.5  = 0.50
  chips:      +1.0  × importance 0.3  = 0.30
  logistics:  -0.02 × importance 0.7  = -0.014
  kids:       +0.8  × importance 0.9  = 0.72
  ───────────────────────────────────────────
  weighted sum: 1.506
  total importance: 2.4
  aggregate belief: 0.63
```

### Constraints as Special Aspects

When an attestation has weight -1.0 on a constraint-type aspect, it's a **veto**:

```
{ by: sarah,
  on: the-local-pub,
  via: sarah/constraint:vegetarian,
  weight: -1.0,
  because: [pub/menu:no-veggie-mains] }

// This isn't "I don't like it much."
// This is "I cannot eat here."
// Consensus algorithm: any -1.0 on constraint = remove option
```

---

## Emergent Ontology

The semantic web died on the data entry problem. Wellspring solves it: **agent proposes, human attests, ontology emerges**.

### The Problem with Top-Down Ontology

```
OLD: Academic creates ontology → begs for data → no one tags anything → dead

OWL/RDF promise:
  - Rich ontologies
  - Machine reasoning
  - Inference across domains

Reality:
  - Who creates the ontology? (academics, slowly)
  - Who tags the data? (no one, too tedious)
  - Who maintains it? (it rots)
```

### The Wellspring Flip: Bottom-Up Emergence

```
NEW: Behavior → Agent infers → Proposes aspect → Human attests → Ontology grows

1. Keif chooses Nandos 4 times in 6 weeks
2. Agent observes pattern
3. Agent proposes: "You seem to enjoy spicy food. True?"
4. Keif attests: +1.0 on keif/aspect:enjoys-spicy
5. Aspect is now part of keif's ontology

Or:

3. Agent proposes: "You prefer chains over independents?"
4. Keif rejects: -0.5, because: [coincidence, kids-drove-choice]
5. Agent learns: wrong framing, update model
```

### Agent Inference as Chain

```
BUBBLE: inference:keif-spicy-2026-01
  type: agent_inference
  subject: keif
  proposed_aspect: enjoys-spicy
  confidence: 0.7
  evidence: [choice:nandos-jan3, choice:nandos-jan15,
             choice:nandos-jan22, order:extra-hot-x3]

CHAIN: inference:keif-spicy → proposes → keif/aspect:enjoys-spicy
  attestation: { by: agent, +0.7 }
```

### Human Response (Attestation)

**Accept**:
```
CHAIN: keif/aspect:enjoys-spicy → recognised_by → keif
  attestation: { by: keif, +1.0,
                 because: [inference:keif-spicy] }
  // "Yes, agent got it right"
```

**Reject with explanation**:
```
CHAIN: inference:keif-spicy → rejected_by → keif
  attestation: { by: keif, -0.8,
                 because: [kids-drove-choice,
                           not-about-spicy] }
  // "No, and here's why you're wrong"
```

**Refine**:
```
CHAIN: keif/aspect:enjoys-spicy → refined_by → keif
  attestation: { by: keif, +0.6,
                 because: [partially-true,
                           more-about-peri-peri-than-general] }
  // "Partially, but more specific"
```

### The Because Chain Teaches

Agent proposes: `keif/aspect:prefers-chains`
Evidence: [nandos, wagamama, pizza-express]

Keif rejects: -0.7
Because: [
  `keif/thought:chains-are-consistent`,
  `keif/thought:consistency-matters-with-kids`,
  `keif/thought:not-about-chain-vs-indie`,
  `keif/aspect:predictability-for-family`   ← THE REAL ASPECT
]

Agent learns:
- "prefers-chains" was wrong framing
- "predictability-for-family" is actual aspect
- Correlates with: has-children, time-pressure
- Better proposals next time

### Hierarchy Emerges from Attestation

```
OBSERVED:
  keif/aspect:enjoys-spicy
  keif/aspect:likes-peri-peri
  keif/aspect:enjoys-thai-heat

AGENT PROPOSES:
  CHAIN: likes-peri-peri → instance_of → enjoys-spicy
  CHAIN: enjoys-thai-heat → instance_of → enjoys-spicy

KEIF ATTESTS:
  +1.0 on peri-peri → enjoys-spicy
  +0.5 on thai-heat → enjoys-spicy
    because: [different-kind-of-heat, thai-is-more-aromatic]

ONTOLOGY EMERGES:

  enjoys-spicy
    ├── likes-peri-peri (+1.0, clear instance)
    └── enjoys-thai-heat (+0.5, partial, different)

// This is OWL rdfs:subClassOf built from behavior,
// not from academic decree.
```

### Universal Aspects Through Consensus

```
Agent observes across many users:
  "kid-friendly" appears in 80% of family pools

Agent proposes:
  BUBBLE: universal/aspect:kid-friendly
  CHAIN: → proposed_for → pool:wellspring-aspects
  attestation: { by: agent, +0.9,
                 because: [observed-in-N-pools] }

Users attest:
  keif: +1.0, because: [matches-my-usage]
  sarah: +1.0
  mike: +0.8, because: [would-phrase-differently]
  jules: +1.0

Threshold reached → becomes universal aspect
Now available for everyone to use
Still refines based on ongoing attestation
```

### The Virtuous Cycle

```
BEHAVIOR
  │
  │ observed by
  ▼
AGENT INFERENCE
  │
  │ proposes
  ▼
ASPECT (candidate)
  │
  │ surfaced to
  ▼
HUMAN ATTESTATION
  │ (+1, -1, refined, with BECAUSE)
  │
  │ confirms/refines
  ▼
ASPECT (validated)
  │
  │ enables
  ▼
SEMANTIC REASONING
  │
  │ improves
  ▼
PREDICTIONS / RECOMMENDATIONS
  │
  │ drives
  ▼
BEHAVIOR (better informed)
  │
  └──────────── loops back ────────────

Data creates itself.
Human stays in the loop (attestation).
Ontology emerges, not imposed.
```

---

## Trails

Trails are Bush's core contribution: named paths through the graph that can be saved, shared, and collaboratively extended.

### Trail as First-Class Citizen

A trail is not just "my path, exported." It's a **shared object** that multiple parties can contribute to.

```
Trail {
  id:           hash(genesis)              // content-addressed
  genesis:      TrailGenesis               // immutable origin
  ops:          [TrailOp]                  // append-only operations
  participants: [identity_bubble_id]       // who's contributing
}

TrailGenesis {
  type:         "trail_genesis"
  created_by:   identity_bubble_id
  created_at:   timestamp
  name:         string
  entry_point:  bubble_id                  // where to start
  initial_participants: [identity_bubble_id]
  nonce:        random
}

// TRAIL_ID = sha256(canonical(genesis))
// This ID is the sync channel.
// Anyone with the ID can request to join.
```

### Trail Operations

```
TrailOp {
  trail_id:     trail_id
  op_id:        hash(this)
  seq:          int                        // my Nth op on this trail
  by:           identity_bubble_id
  at:           timestamp
  type:         "chain" | "bubble" | "attestation" | "annotation"
  payload:      { ... }
  prev_ops:     [op_id]                    // causal dependencies
  sig:          signature
}
```

Trails are CRDT-compatible:
- Ops are immutable (content-addressed)
- Ops can only be added, never removed
- Causal ordering via prev_ops
- Concurrent ops: both valid, order by op_id
- Merge is simple: union of ops

### Trail URI

```
wellspring://keif/trail/turkish-bow

Resolves to:
{
  owner: "did:wellspring:keif",
  name: "turkish-bow",
  created: "2026-01-27T...",
  entry: "wellspring://keif/bubble/bow-arrow-origin",
  trail_id: "trail:7f83b162...",
  signature: "..."
}
```

### Trail Sharing (Bush's Gift)

> "So he sets a reproducer in action, photographs the whole trail out, and passes it to his friend for insertion in his own memex, there to be linked into the more general trail." — Bush, 1945

```
I send you: wellspring://keif/trail/turkish-bow

Your pod:
  1. Resolves keif's identity (web of trust)
  2. Fetches trail genesis and ops
  3. Validates genesis matches trail_id hash
  4. Imports into YOUR graph
  5. Links to YOUR existing knowledge
  6. You can now traverse MY path in YOUR context

Your attestations are yours.
My attestations are mine.
We can agree, disagree, extend.
The trail is the conversation.
```

---

## Sync as Attestation

Sync is not a separate protocol layer. **Sync IS the graph.** The sync record is a chain attested by both parties.

### SNAP-Inspired Bilateral Consensus

Wellspring's sync protocol is inspired by Michiel de Jong's SNAP (Synchronized Network Accounting Protocol):

> "Unlike many other protocols, SNAP is not designed to prevent disagreement due to cheating. In a bilateral consensus setting, the other party will always be able to lie and cheat. Instead, it is designed to prevent discrepancies due to confusion about messages that were sent but not received."

This is perfect for Wellspring:
- Protocol handles **confusion** (did they receive it?)
- Trust model handles **disagreement** (do they believe it?)
- Both are in the graph. Both are queryable.

### Sync Channel as Bubble

```
BUBBLE: sync_channel:keif-claude
  type: sync_channel
  participants: [keif, claude]
  created: 2026-01-27

Every op transmitted:

CHAIN: op_xyz → transmitted_via → sync_channel:keif-claude
  attestation: { by: keif, +1.0, at: T1 }       // I sent this
  attestation: { by: claude, +1.0, at: T2 }    // I received this

Bilateral consensus = both attested +1.0
Dispute = one attests -1.0 (with because)
Pending = only sender has attested
```

### Query Becomes Simple

```
"What has Claude acknowledged?"
  → Find chains where:
      - transmitted_via → sync_channel:keif-claude
      - has attestation by claude with belief > 0

"What's pending?"
  → Find chains where:
      - transmitted_via → sync_channel:keif-claude
      - has attestation by keif
      - NO attestation by claude

"What did Claude dispute?"
  → Find chains where:
      - transmitted_via → sync_channel:keif-claude
      - has attestation by claude with belief < 0
      - Check because for reason
```

### Multi-Party Sync

For trails with more than two participants, use a mesh of bilateral connections:

```
     Keif
    ╱    ╲
Claude ── Sarah

Each pair syncs bilaterally.
Ops propagate through the mesh.
Gossip, not broadcast.

Trail membership = who you have sync channel with
Adding member = establishing bilateral with them
```

### The Elegance

One primitive handles:

- **Content** ("this bubble exists")
- **Relationships** ("this links to that")
- **Belief** ("I think this is true")
- **Sync** ("I received this")
- **Membership** ("I'm part of this trail")
- **Permissions** ("I attest you can...")
- **Disputes** ("I disagree because...")
- **History** ("at T1, I believed..., at T2, I changed")

All chains with attestations. All queryable the same way. All auditable the same way.

---

## Pools

Pools are the universal organizational primitive. Everything lives in a pool. Your "pod" IS your personal pool.

### Pool as Bubble

```
BUBBLE: pool:xyz
  type: pool
  name: "UK Construction Tech"
  visibility: public | private | unlisted
  created_by: identity_bubble_id
  created_at: timestamp
```

### Pool Hierarchy

```
keif/pool:private          ← Your brain, default, your "pod"
keif/pool:family           ← Shared with spouse, kids
keif/pool:buymaterials     ← Work context
pool:uk-construction       ← Public, topic-based
pool:wellspring-dev        ← Public, project-based
pool:wellspring-directory  ← Meta-pool, lists other pools
```

### Membership as Chain

```
CHAIN: keif → member_of → pool:xyz
  attestation: { by: keif, +1.0 }           // I want to join
  attestation: { by: pool:xyz, +1.0 }       // Pool accepts

CHAIN: keif → has_role → pool:xyz
  role: admin | write | read
  attestation: { by: pool:xyz (admin), +1.0 }
```

### Permissions as Attestations

```
PERMISSION MODEL

READ:   Can sync pool content to your pod
WRITE:  Can publish to pool (create chains into it)
ADMIN:  Can grant/revoke permissions

CHAIN: sarah → can_read → pool:xyz
  attestation: { by: pool:xyz (admin), +1.0 }

CHAIN: sarah → can_write → pool:xyz
  attestation: { by: pool:xyz (admin), +1.0 }

Revoke = attest 0.0 on permission chain:

CHAIN: sarah → can_write → pool:xyz
  attestation: { by: admin, +1.0, at: T1 }  ← granted
  attestation: { by: admin, 0.0, at: T2 }   ← revoked

Permission at time T = latest attestation before T
```

### Pool Visibility

| Visibility | Behavior |
|------------|----------|
| **Public** | Appears in registries, anyone can request read, content discoverable |
| **Unlisted** | Exists but not in registries, need link/invitation to find |
| **Private** | Not advertised, invitation only, "your brain" / "family only" |

### Personal Pool = Your Pod

```
keif/pool:private

- Created automatically with identity
- You are sole admin
- Default home for all your bubbles
- Sync only with your own devices

Your "waterline" = view into your private pool

Publishing = creating chain from private → other pool:

CHAIN: thought → published_to → pool:uk-construction

Original stays in your pool.
Chain makes it visible elsewhere.
```

### Pool Federation

```
CHAIN: pool:uk-construction → federated_with → pool:eu-construction
  attestation: { by: pool:uk (admin), +1.0 }
  attestation: { by: pool:eu (admin), +1.0 }

Federation = mutual attestation
Both pools agree to share content

FEDERATION MODES:

Mirror:    All content synced both ways
Bridge:    Selected content crosses over
Subscribe: One-way, pool A reads pool B

CHAIN: pool:A → subscribes_to → pool:B
  attestation: { by: pool:A, +1.0 }
  attestation: { by: pool:B, +1.0 }  ← B permits
```

### Discovery Through Directory Pools

```
pool:wellspring-directory
  - Meta-pool: contains references to other pools
  - Anyone can publish "my pool exists"
  - Searchable by topic, region, etc.

CHAIN: pool:uk-construction → listed_in → pool:wellspring-directory
  attestation: { by: pool:uk-construction, +1.0 }
  metadata: { topic: "construction",
              region: "uk",
              members: 150 }

Multiple directories can exist.
Compete on curation quality.
No single point of control.
```

### Trust-Based Pool Discovery

```
keif trusts sarah (vouch chain)
sarah is member of pool:proptech
sarah attests pool:proptech is good (+0.9)

keif's computed trust in pool:proptech:
  trust(keif, sarah) × sarah's_attestation
  = 0.8 × 0.9 = 0.72

"Pools trusted by people you trust"
Organic, no central authority.
```

### Invitation Flow

```
Keif invites Sarah to pool:family

1. Keif creates:
   CHAIN: sarah → invited_to → pool:family
     attestation: { by: keif (admin), +1.0 }
     permissions: [read, write]
     expires: 2026-02-27 (optional)

2. Keif sends Sarah:
   wellspring://pool:family?invite=<signed_token>

3. Sarah's pod:
   - Resolves pool
   - Validates invitation
   - Creates: sarah → member_of → pool:family
     attestation: { by: sarah, +1.0 }

4. Pool (or Keif as admin) attests membership:
   CHAIN: sarah → member_of → pool:family
     attestation: { by: pool:family, +1.0 }

5. Sync begins.
```

---

## Browser Extension: Automated Trail Capture

The browser is where learning happens. The extension captures associative trails automatically.

### What It Captures

| Action | Relation Type | Signal |
|--------|---------------|--------|
| Click link | `led_to` | Intentional |
| Open in new tab | `spawned` | Parallel exploration |
| Back button | `rejected` | Negative signal |
| Bookmark | `saved` | Strong positive |
| Copy URL | `shared` | Intent to use |
| Select text | `highlighted` | Key passage |
| Idle > 30s reading | `absorbed` | Engagement |
| Quick bounce < 5s | `dismissed` | Not useful |
| Return to same page | `revisited` | Importance |

### Example Trail

```
google.com/search?q=cosmos+db+partition
     │
     │ clicked_from (position 3)
     ▼
docs.microsoft.com/cosmos-db/partitioning
     │ dwell: 4m32s, scroll: 80%
     │
     │ clicked_link
     ▼
stackoverflow.com/questions/12345
     │ dwell: 45s, scroll: 100%
     │
     │ opened_in_new_tab
     ▼
github.com/azure/cosmos-samples
     │ dwell: 12m, scroll: 60%
     │
     └── BOOKMARKED (strong signal)

Each URL = bubble (created_by: browser_extension)
Each transition = chain (typed by how you got there)
Dwell/scroll/bookmark = implicit attestation weight
```

### Implicit Attestation from Behavior

```
Dwell time 10+ minutes + bookmark + return visit:
  → Auto-attest: +0.7 (valuable, came back)

Bounce < 5 seconds:
  → Auto-attest: 0.0 (didn't engage, dormant)

Read, never returned, no follow-on links:
  → Auto-attest: +0.3 (read but didn't build on)

Explicit bookmark + highlight + spawned 3 tabs:
  → Auto-attest: +0.9 (this was a source)

You can always override. But the default is sensible.
```

### Privacy Controls

```
EXCLUDE PATTERNS
• Banking sites (*.bank.com, */login, */account)
• Private browsing / incognito (no capture)
• Configurable domain blocklist
• Configurable path patterns
• "Pause capture" hotkey

REDACTION
• Strip query params by default (no ?session=xxx)
• Strip auth tokens from URLs
• Option to capture full URL for trusted domains

This is YOUR data. You control what's captured.
```

### Trail Reconstruction

```
"How did I find that Cosmos DB partitioning article?"

Wellspring:
  "On Jan 15, you searched for 'cosmos db partition
   strategy', clicked the 3rd result (Microsoft docs),
   spent 4 minutes reading, then followed a link to
   Stack Overflow, which led you to a GitHub repo
   you bookmarked. Total session: 18 minutes."

That's the trail. Reconstructed. Auditable.
"Where did I learn that" has an answer.
```

---

## Identity Framework

### Identity Types

| Type | Keys | Provenance | Trust Computation |
|------|------|------------|-------------------|
| **Sovereign** | Has keypair | Self-asserted | Via vouches from other sovereigns |
| **Delegated** | Derived from parent | Parent vouches | Parent's trust × delegation factor |
| **Record** | None | Chain traces back | Via vouches from capable attesters |
| **External** | None | Outside Wellspring | Via historical accuracy reputation |

### Sovereign Identity

Full participant, owns keys, can create and sign attestations.

```
BUBBLE {
  content: {
    type: "identity"
    name: "Keif"
    pubkey: "ed25519:abc..."
    created: timestamp
  }
  created_by: self_reference
  signature: sig(content, privkey)
}
```

### Delegated Identity

Derived authority from parent (sessions, API tokens, agents).

```
CHAIN: keif → delegates_to → keif_session_xyz
  scope: [pool:buymaterials, expires: 2026-02-01]
  attestation: { by: keif, +1.0, because: [work_session] }

// Authority flows down, trust flows up
// Revocable by parent
// Trust discounted by delegation depth
```

### Record Identity

Content without keys, trust via vouching.

```
CHAIN: wikipedia → vouched_by → keif
  attestation: { by: keif, +0.7,
                 because: [generally_accurate,
                           good_for_starting_point] }

// Can't sign for itself
// Trust computed from who vouches
```

### External Identity

Outside Wellspring, trust via reputation.

```
BUBBLE: external:reuters
  type: external_source
  url: reuters.com

CHAIN: article_xyz → derives_from → external:reuters
  attestation: { by: keif, +0.8,
                 because: [reputable_source] }

// Trust via historical accuracy
// Aggregated across attestations
```

---

## Trust Computation

Trust is computed, not stored.

```
trust(source, observer, context, time) =
  f(vouches_chains, attestations, because_chains, groundedness)
```

### Groundedness Recursion

```
groundedness(attestation) =
  if attestation.because is empty:
    return base_groundedness (low, ~0.1-0.3)
  else:
    recurse into because chains
    → check their attestations
    → recurse into THEIR because chains
    → aggregate weighted beliefs

Termination:
  - Self-attestation by trusted sovereign
  - Empty because (ungrounded assertion)
  - Circular reference (detect, cap)
  - Depth limit
  - External source reputation
```

### Trust by Identity Type

| Type | Trust Computation |
|------|-------------------|
| **Sovereign** | Web of trust via vouches chains |
| **Delegated** | parent_trust × delegation_factor × scope_match |
| **Record** | Sum of vouches from capable identities |
| **External** | Reputation (historical accuracy across attestations) |

### Trust Policy as Publication

```
TRUST POLICY (publication) {
  name: "Verified Quotes Required"
  recursion_depth: 2
  require_provenance: true
  require_attestations: true
  anchors: [reuters, hansard, c-span]
  distrust: [known_satire_sources]
}

POOL {
  trust_policy: chain → policy_publication
}

Different contexts compute trust differently:
- Shitposting group: vibes_only, recursion_depth: 0
- Political discussion: verified_quotes, high provenance
- Academic: academic_rigor, methodology checks
```

---

## Inference and Constraints

Wellspring supports lightweight inference without the computational weight of full description logic. Three mechanisms: **relation characteristics**, **property chains**, and **composite expressions**.

### Relation Characteristics

Relations can declare propagation behavior:

```
RELATION CHARACTERISTICS

transitive:     If A→B and B→C then A→C
                Examples: part_of, ancestor_of, contains, manages

symmetric:      If A→B then B→A
                Examples: sibling_of, colleague_of, related_to, sync_with

inverse:        A→B via R implies B→A via R⁻¹
                Examples: parent_of ↔ child_of, employs ↔ works_at

functional:     At most one value per subject
                Examples: has_mother, has_ssn, born_on

antisymmetric:  If A→B then NOT B→A (unless A=B)
                Examples: part_of, reports_to, older_than
```

**Declared in schema:**

```
RELATION: part_of
  characteristics: [transitive, antisymmetric]
  inverse: contains

RELATION: vouches
  characteristics: []  // explicitly non-transitive
  // Trust is COMPUTED, not inferred

RELATION: sibling_of
  characteristics: [symmetric]

RELATION: has_mother
  characteristics: [functional]
  // System flags contradiction if two values asserted
```

### Property Chains

Composite relations inferred from chain traversal:

```
PROPERTY_CHAIN: works_in_country
  composition: works_at → headquartered_in
  
  keif → works_at → BuyMaterials
  BuyMaterials → headquartered_in → UK
  ∴ keif → works_in_country → UK  (inferred)

PROPERTY_CHAIN: uncle_of
  composition: parent_of⁻¹ → sibling_of → [gender = male]
  
  alice → parent_of → bob
  alice → sibling_of → charlie (male)
  ∴ charlie → uncle_of → bob  (inferred)
```

**Implementation note:** Inferred chains are computed on query, not stored. Materialization optional for hot paths.

### Disjointness

Mutual exclusion between aspects or classes:

```
DISJOINT: vegetarian, contains_meat
  // Attestation +1.0 on both = contradiction
  // System flags for resolution

DISJOINT: open_now, permanently_closed

DISJOINT: child, adult
```

**Contradiction handling:**

```
keif attests nandos:
  via vegetarian-friendly: +0.8
  
sarah attests nandos:
  via contains_meat: +1.0  // (it's chicken)

NOT a contradiction — different aspects.
vegetarian-friendly ≠ vegetarian.

BUT:

keif attests dish:grilled-halloumi:
  via vegetarian: +1.0
  via contains_meat: +1.0

CONTRADICTION — disjoint aspects on same subject.
System flags. Keif resolves.
```

### Cardinality Constraints

Minimum/maximum counts on relations:

```
CARDINALITY: has_parent
  min: 0    // adopted, unknown
  max: 2    // biological limit

CARDINALITY: decision.options
  min: 2    // need choices
  max: null // unlimited

CARDINALITY: pool.admin
  min: 1    // must have at least one
  max: null
```

### Equivalence (Same-As)

Identity resolution across representations:

```
CHAIN: "Keef" → same_as → "Keif"
  attestation: { by: keif, +1.0 }  // typo correction

CHAIN: keif@gmail.com → same_as → keif@buymaterials.co.uk
  attestation: { by: keif, +1.0 }  // same person

CHAIN: external:nandos-manchester → same_as → google_places:ChIJ...
  attestation: { by: agent, +0.9 }  // entity resolution
```

**Properties:** Symmetric and transitive. Attestations on one apply to all equivalents.

### Composite Expressions

Aspects can be composed using set operations.

**Expression types:**

| Type | Meaning |
|------|---------|
| `intersection` | All components must be satisfied (AND) |
| `union` | Any component satisfies (OR) |
| `complement` | Satisfied iff component is NOT satisfied (NOT) |

**Evaluation modes:**

| Mode | Semantics | Use For |
|------|-----------|---------|
| `must` | min/max | Constraints, dealbreakers, hard requirements |
| `prefer` | weighted average | Nice-to-haves, soft preferences, ranking |

**Must mode (min/max):**

```
intersection: min(component_weights)
  family-friendly = kid-friendly ∩ affordable ∩ has-parking
  weights: [+0.9, +0.8, -0.3]
  result: -0.3  // fails on parking, whole thing fails

union: max(component_weights)
  has-booking = phone ∪ website ∪ walk-in
  weights: [-1.0, +0.8, +0.5]
  result: +0.8  // website works, we're good

complement: -1 × component_weight
  not-fast-food = ¬fast-food-chain
  fast-food-chain: +0.9
  result: -0.9  // fails complement
```

**Prefer mode (weighted):**

```
weighted_of:
  nice-evening = romantic × 0.4 + good-food × 0.4 + convenient × 0.2
  weights: [+0.7, +0.9, +0.3]
  result: (0.7×0.4) + (0.9×0.4) + (0.3×0.2) = 0.70
```

**Composite aspect definition:**

```
ASPECT: family-friendly
  type: composite
  mode: must
  expression: intersection_of [kid-friendly, affordable, has-parking]

ASPECT: date-worthy
  type: composite
  mode: prefer
  expression: weighted_of [romantic: 0.4, good-food: 0.4, not-too-loud: 0.2]

ASPECT: accessible
  type: composite
  mode: must
  expression: union_of [wheelchair-ramp, ground-floor, has-lift]
```

### Decision Evaluation Pipeline

Two-phase evaluation using composite expressions:

```
DECISION: friday-dinner

must:
  intersection_of: [everyone-can-eat, within-budget, someone-can-drive]
  mode: must
  // ANY component -1.0 = option eliminated

prefer:
  weighted_of: [kids-happy: 0.35, good-food: 0.30, easy-parking: 0.20, quick-service: 0.15]
  mode: prefer
  // Weighted ranking of survivors

EVALUATION:

1. FILTER by must (min semantics)
   nandos:      must = min(+0.8, +0.9, +0.7) = +0.7  ✓
   wagamama:    must = min(+0.9, +0.8, +0.6) = +0.6  ✓
   local-pub:   must = min(-1.0, +0.9, +0.8) = -1.0  ✗ (veto)
   
2. RANK survivors by prefer (weighted avg)
   nandos:      prefer = 0.82
   wagamama:    prefer = 0.71
   
3. RESULT: nandos wins
```

### Open World Assumption

Wellspring operates under open world assumption:

```
Absence of attestation ≠ belief of 0.0
Absence of attestation = no information

keif has not attested on wagamama/parking
  ≠ keif believes wagamama has bad parking
  = keif hasn't expressed a view

IMPLICATIONS:
- Can't infer negatives from silence
- Must explicitly attest 0.0 for "dormant"
- Must explicitly attest -1.0 for "disbelieve"
- Unknown stays unknown until observed
```

---

## Salience and Waterline

### Salience Formula

```
salience(bubble, observer, time) =
  reachability × confidence × heat × belief

Where:
  reachability = can we walk to it from current context?
  confidence   = product of attestation strengths along path
  heat         = f(recency, traversal_frequency)
  belief       = latest attestation by observer (if 0, salience = 0)
```

### Waterline

The bubbles above the waterline are "conscious"—high salience given current context.

```
WATERLINE VIEW

  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ surface
  
  ○ BuyMaterials pricing bug      [0.92]
  ○ Wife's birthday next week     [0.88]
  ○ Wellspring spec v0.3          [0.85]
  
  ─────────────── waterline ───────────────
  
  ◌ Cosmos partition strategy     [0.45]
  ◌ Holiday booking               [0.32]
  
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ depths

Above: currently relevant, contextually reachable
Below: exists, accessible, not surfacing now
```

### Materialized for Speed

```
Per-bubble materialized:
  current_salience, current_confidence, current_level
  last_touched, open_edge_count, attestation_summary

Per-observer:
  waterline (sorted set by salience)
  hot_chains, pending_proposals

Propagation tiers:
  IMMEDIATE (sync, <5ms): append attestation, update local salience
  PROPAGATE (async, <100ms): walk one hop, recalc neighbors
  BACKGROUND (eventually): deep trust, full groundedness
```

---

## WOT: Group Consensus Application

WOT ("What shall we do?") is a Wellspring application for group decisions. It demonstrates that the primitives handle social coordination, not just personal memory.

### WOT Concepts as Wellspring

| WOT Concept | Wellspring Primitive |
|-------------|---------------------|
| Group/Gang | Pool (shared, private) |
| Participant | Member of pool |
| Option | Bubble (restaurant, time, movie) |
| Preference | Attestation via aspect |
| Constraint | Attestation with constraint aspect, weight -1.0 = veto |
| Calendar block | Bubble + attestation (can't: -1.0) |
| Proposal | Chain (option → proposed_for → decision) |
| Consensus | Computed from attestations |
| Decision | Bubble with winning attestations |

### Example Decision

```
POOL: keif/pool:friday-gang
  members: keif, sarah, mike, jules

BUBBLE: decision:friday-dinner
  type: decision
  question: "Where for dinner Friday?"
  deadline: 2026-01-31T18:00:00Z

OPTIONS (bubbles):
  option:nandos
  option:wagamama
  option:the-local-pub

CHAINS:
  option:nandos → proposed_for → decision:friday
  option:wagamama → proposed_for → decision:friday
  option:the-local-pub → proposed_for → decision:friday

ATTESTATIONS (decomposed by aspect):

keif on nandos:
  via keif/preference:spicy        → +1.0
  via keif/mood:chip-craving       → +1.0
  via keif/value:kids-happy        → +0.8
  via keif/preference:easy-parking → -0.3

sarah on nandos:
  via sarah/preference:spicy       → -0.3
  via sarah/constraint:vegetarian  → +0.5  // they have options

sarah on the-local-pub:
  via sarah/constraint:vegetarian  → -1.0  // VETO
    because: [pub/menu:no-veggie-mains]
```

### Consensus Computation

```
Simple: Average across attestations

nandos (all aspects, all people):
  weighted_average = 0.58

wagamama:
  weighted_average = 0.72

local-pub:
  VETOED (sarah -1.0 on constraint)

Winner: Wagamama (highest score, no vetos)
```

### Learning Preferences Over Time

```
AFTER DECISION:

BUBBLE: event:wagamama-friday
  where: Wagamama Manchester
  when: 2026-01-31T20:00:00Z
  who: [keif, sarah, mike, jules]

POST-EVENT ATTESTATIONS:

keif on wagamama:
  via keif/aspect:overall-experience → +0.9
    because: [great_ramen]

mike on wagamama:
  via mike/aspect:overall-experience → +0.7
    because: [service_slow]

→ Feeds back into preferences
→ Next time: Wagamama has higher base score
→ mike's "service_slow" noted for future
```

---

## Query Semantics

Three query families operating on the traversal graph.

### FIND — What exists?

```
FIND bubbles ABOUT "pricing"
FIND ideas WHERE confidence > 0.7
FIND chains WHERE attestation.by = keif AND belief < 0
FIND constructs BY keif SINCE 2025-01-01
FIND aspects WHERE type = constraint AND owner = sarah
```

### TRACE — How was this understood?

```
TRACE idea:"X"
  → returns backchain paths
  → shows attestations at each step (with aspects)
  → shows where confidence comes from

TRACE bubble:"X" ATTESTATIONS
  → returns all attestations grouped by aspect
  → shows belief changes over time
  → shows who attested what via what

TRACE bubble:"X" BECAUSE
  → returns full because chain recursion
  → shows grounding depth
```

### TEMPORAL — How has belief evolved?

```
SNAPSHOT idea:"X" AS_OF 2025-06-01
  → state of bubble and attestations at that time

HISTORY chain:"A→B"
  → all attestations over time
  → belief trajectory by aspect

DIFF construct:"Y" BETWEEN 2025-01 AND 2026-01
  → what attestations changed
  → who changed their mind
  → which aspects shifted
```

---

## Implementation Architecture

### Storage Tiers

| Component | Characteristics | Suitable Engines |
|-----------|-----------------|------------------|
| Bubbles | Immutable, content-addressed | Document store, IPFS |
| Chains | Append-only attestations | Event-sourced store |
| Trails | Append-only ops, CRDT | Event log |
| Aspects | Bubbles with type | Document store |
| Trust graph | Graph traversal | Graph DB or materialized |
| Salience | Hot, per-observer | Redis/Garnet sorted sets |
| Semantic | Similarity search | Vector index |

### Local-First Architecture

```
Your waterline lives ON YOUR DEVICE

- Sync subset of graph locally
- Compute salience locally
- Zero network latency for "what am I thinking"
- Background sync for shared context

Network only for:
- Fetching new shared bubbles
- Publishing attestations
- Agent proposals
- Deep traces not local
```

### Speed Optimization

```
Fast path (<10ms):
- Waterline query: ZRANGE waterline:keif 0 20 REV
- Immediate context: GET chains:from:{bubble_id}
- Current belief: GET attestation:latest:{chain_id}:{observer}

Propagation tiers:
- IMMEDIATE (sync, <5ms): append attestation, update local
- PROPAGATE (async, <100ms): walk one hop, recalc neighbors
- BACKGROUND (eventually): deep trust, full groundedness
```

### CRDT Properties

Natural conflict-free replication:

- Bubbles: immutable, content-addressed → no conflict
- Chains: identified by endpoints + creator → no conflict
- Attestations: append-only, by different identities → set union
- Trail ops: append-only, causal ordering → set union
- Trust: computed, not stored → no conflict
- Aspects: bubbles, same rules → no conflict

### Workload Classification

Not all operations need real-time response. Complexity hides in background processing.

| Mode | Latency | Examples |
|------|---------|----------|
| **Offline** | Seconds to hours | Trust propagation, aspect inference, compaction, index building, ontology emergence |
| **Online** | <100ms | Waterline query, chat context, live consensus |
| **Semi-online** | 100ms-10s | Search + rerank, browser capture batches, sync waves |

**Key insight:** Expensive Wellspring operations (inference rules, groundedness recursion, aspect learning) are ALL offline. User never waits for a reasoner.

```
ONLINE PATH (what user waits for):
  - Lookup waterline (sorted set)
  - Lookup attestations (key-value)
  - Return

OFFLINE PATH (agents churn through):
  - Full graph traversal
  - Inference rule application
  - Trust recomputation
  - Aspect proposal generation
```

### Background Agents

Intelligence is pluggable. Ship v1 with simple agents, upgrade later. Data model supports it.

```
LINKER AGENT
  - Proposes chains between bubbles
  - Similarity, co-occurrence, entity matching
  - "This article relates to that one"

TRUST AGENT
  - Recomputes groundedness scores
  - Propagates vouches through graph
  - Flags contradictions (disjointness violations)
  - Maintains reputation for external sources

ASPECT AGENT
  - Observes behavior patterns
  - Proposes aspects for human attestation
  - Builds hierarchy (instance_of chains)
  - Identifies universal aspects across users

COMPACTION AGENT
  - Archives dormant subgraphs
  - Prunes sync noise from active graph
  - Maintains index freshness
  - Manages storage growth

SYNC AGENT
  - Bilateral reconciliation
  - Attestation propagation across pools
  - Conflict surfacing for human resolution
```

User sees: fast lookups, occasional "did you mean this?" prompts.
Agents see: full graph, all inference rules, unlimited time.

### Local-First Processing Stack

Privacy by architecture, not policy. Everything runs locally until you choose to sync.

```
CAPTURE (all local)
  OCR:        Tesseract.js + WASM (images → text)
  PDF:        pdf.js (documents → text)
  Web:        DOM parser (pages → structured)
  
SEARCH (all local)  
  BM25:       qmd or similar (keyword search)
  Vector:     Local embeddings (semantic search)
  Graph:      SQLite + materialized views (traversal)

INFERENCE (local or edge)
  Embeddings: ONNX / llama.cpp
  Proposals:  Small local model or batch to cloud
  
SYNC (when YOU choose)
  Pool sync:  Bilateral attestation protocol
  Backup:     Encrypted to your storage
  Share:      Export trail to recipient
```

**Benefits:**
- Works offline (airplane, rural, privacy-required)
- No token costs for local operations
- Data never leaves device until explicit sync
- Survives service shutdowns (your data, your hardware)

**Search architecture:**

```
QUERY: "Turkish bow article"

1. qmd search (local, 500 tokens)
   → 5 candidate snippets + source locations

2. Wellspring graph (local)
   → Rank by: relevance × trust × salience
   → "This one's from source you trust,
      you traversed it 3 times,
      chains to your archery research"

3. Return: trusted, contextual, cheap
```

Search finds. Wellspring validates and contextualises.

### Traversal-Based Ranking

Candidates aren't ranked by semantic similarity alone. They're ranked by **shortest path cost** from current context through your actual knowledge graph.

**Edge cost = f(recency, frequency, trust)**

```
Path walked yesterday:         low cost
Path walked once 2 years ago:  high cost
Path walked 5 times this month: very low cost
Never traversed this route:    highest cost
```

**Retrieval example:**

```
Current context: "archery techniques"
Query: "Turkish bow"
Candidates from qmd: 5 articles

Shortest path from current_context to each:

  candidate_1: cost 12 (never traversed this route)
  candidate_2: cost 3  (walked this path Tuesday)
  candidate_3: cost 7  (walked once, 6 months ago)
  candidate_4: cost 15 (exists but unconnected)
  candidate_5: cost 5  (via archery → history → ottoman)

Winner: candidate_2

Not because it's "most relevant" semantically,
but because YOU ALREADY THINK THIS WAY.
```

**The algorithm finds YOUR path, not A path.**

This is Bush's "trails that are frequently followed" made computational. Recent work (Duan et al., 2025) shows SSSP can run in O(m log^(2/3) n) — faster than Dijkstra on sparse graphs. Personal knowledge graphs are sparse. This matters because retrieval runs constantly.

**Compounding effect:**

```
1st retrieval: path cost 8
2nd retrieval: path cost 6 (edge weights decreased)
3rd retrieval: path cost 4
5th retrieval: path cost 2

The search literally gets better at being YOU.

Trails deepen with use.
Retrieval accelerates along familiar paths.
Your mind's shortcuts become the graph's shortcuts.
```

**Integration with salience:**

```
RANKING SCORE = 
  (1 / path_cost) × trust_product × recency_boost

Where:
  path_cost    = shortest path through traversal-weighted graph
  trust_product = product of attestation strengths along path
  recency_boost = f(last_traversal_time)
```

This unifies search and memory: finding something IS remembering it, and remembering it makes it easier to find next time.

---

## Summary

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  WELLSPRING ETERNAL v0.3                                │
│                                                         │
│  "Water remembers every path it has taken"              │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Two primitives:                                        │
│    BUBBLE — content + creator (always attributed)       │
│    CHAIN  — relationship + signed attestations          │
│                                                         │
│  Attestations decomposed:                               │
│    VIA    — through what aspect/lens                    │
│    WEIGHT — how much it applies                         │
│    BECAUSE — grounding in other chains                  │
│                                                         │
│  Everything is pools:                                   │
│    Personal   — your pod, your brain                    │
│    Shared     — family, team, gang                      │
│    Public     — topic communities                       │
│    Directory  — meta-pools for discovery                │
│                                                         │
│  Trails are first-class:                                │
│    Named paths through the graph (Bush's gift)          │
│    Shareable, collaborative, multi-master               │
│    Sync IS attestation (chains all the way down)        │
│                                                         │
│  Ontology emerges:                                      │
│    Agent observes behavior                              │
│    Agent proposes aspects                               │
│    Human attests (yes/no/refine + because)              │
│    Hierarchy builds from instance_of chains             │
│    Universal aspects from cross-user consensus          │
│                                                         │
│  Trust computed:                                        │
│    Vouches chains for sovereigns                        │
│    Groundedness recursion via because                   │
│    Reputation for externals                             │
│    Delegation discounting                               │
│                                                         │
│  Inference (OWL-lite):                                  │
│    Relation characteristics (transitive, symmetric...)  │
│    Property chains (composed relations)                 │
│    Disjointness (contradiction detection)               │
│    Composite expressions (must: min/max, prefer: weighted)│
│    Open world assumption                                │
│                                                         │
│  Architecture:                                          │
│    Local-first (works offline, privacy by design)       │
│    Background agents (linker, trust, aspect, compaction)│
│    Online: fast lookups only (<100ms)                   │
│    Offline: reasoning, inference, learning              │
│    Search: qmd finds, Wellspring validates              │
│                                                         │
│  Applications:                                          │
│    Personal memory — "where did I learn that"           │
│    Group decisions — "where shall we go" (WOT)          │
│    Same primitives, different queries                   │
│                                                         │
│  Properties:                                            │
│    Nothing anonymous    — everything has creator        │
│    Nothing deleted      — attestations append           │
│    Nothing truly lost   — dormant, can wake             │
│    Everything weighable — trust always computable       │
│    Everything auditable — signatures + because chains   │
│    Data creates itself  — behavior → proposal → attest  │
│                                                         │
│  Lineage:                                               │
│    Bush (1945) → Engelbart → Nelson →                   │
│    [wrong turn: WWW hyperlinks] →                       │
│    Wellspring (2026): completing the memex              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Open Questions

- Detailed sync protocol message formats
- Query language formal grammar
- API surface specification
- UI specification for waterline interface
- Reputation scoring algorithm for external sources
- Key rotation ceremony details
- Pool permission inheritance rules
- Aspect importance weighting algorithms
- Agent proposal quality metrics
- Browser extension detailed architecture
- Mobile capture strategies
- Wikipedia/knowledge base import tooling

---

## Appendix: Relation to Existing Technologies

### Semantic Web (OWL/RDF)

Wellspring can export to OWL/RDF for external reasoning engines, but solves the data creation problem that killed semantic web adoption:

| Semantic Web | Wellspring |
|--------------|------------|
| Top-down ontology | Bottom-up emergence |
| Manual tagging | Behavioral inference |
| Academic maintenance | Agent proposal + human attestation |
| Empty graphs | Living, growing data |

### AllegroGraph / Oxford Semantic

These are powerful reasoning engines with no data creation story. Wellspring creates the data; they could provide inference.

### Solid / ATProto

| Solid | ATProto | Wellspring |
|-------|---------|------------|
| Pods (yes) | PDS (yes) | Pools (yes) |
| RDF complexity | JSON | Bubbles + Chains |
| No AI layer | No AI layer | Agent-native |
| No trust model | Limited trust | Full attestation model |
| Discovery unclear | Relays | Directory pools + web of trust |
| Stalled adoption | Growing | TBD |

### Zep/Graphiti, Mem0, Letta

Agent memory tools, developer-focused, no user ownership, no attestation model. Wellspring is user-owned with human-agent symmetry.

---

*Wellspring Eternal — v0.3*
*Keif Gwinn & Claude, January 2026*
*Building on Bush's Memex (1945), completing the 80-year vision*
