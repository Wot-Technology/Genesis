# Wellspring: Traces to Pull

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

## Evidence Trail: External Validation (2026-01-30)

### @strickvl Context Rot Post

**Source:** Threads post (MLOps/ZenML context, 4h ago)

**The problem he's describing:**

> "Context rot — what happens when an agent's context window fills up and performance degrades. Subagents isolate context so the parent only gets the final answer, not the 20 tool calls that produced it."

> "LLMs condense everything down. You get an average of what's out there, not the best of what's out there."

> "When I ran ChatGPT Deep Research on questions in my specific domain, it used low-quality random news stories as sources for its report."

He's got 15 years Afghanistan research, PhD, half-dozen books — and Deep Research gave him news articles. No trust weighting. No expertise recognition. Average, not best.

**The expertise gap in current systems:**

This is a PhD-level domain expert with:
- 15+ years of primary research
- Multiple published books
- Direct field experience
- Deep source networks built over decades

And the "AI research" tool gave him the same sources a college freshman would get — news aggregators, Wikipedia summaries, SEO-optimized content farms. The system has no way to know he's an expert. No way to weight his trusted sources higher. No way to distinguish his vetted contacts from random internet strangers.

**Why this matters for Wellspring:**

His trust graph would be *radically* different from a newcomer's:
- Primary sources he's personally verified → high trust
- Academics in his citation network → transitive trust via vouch
- News aggregators → below waterline (low/no trust)
- Random social media → not in graph at all

Same query, completely different results. Not "what the internet thinks" but "what my network of verified experts thinks, with receipts showing why I trust them."

**How Wellspring solves this:**

| His Problem | Wellspring v0.5/0.6 |
|-------------|---------------------|
| Context rot | Working memory pools collapse to summary + full because chain available |
| Parent gets only final answer | Output thought references entire debate trail via `because` |
| Average not best | Trust graph weights sources — your attestations determine what surfaces |
| No domain expertise | Your aspects + vouch chains prioritize experts you trust |
| Dynamic DAG unknown upfront | Because chains capture whatever path was actually walked |
| Failure handling per-step | Attestations on each step — resume from last attested good state |

**Key quote → Wellspring mapping:**

> "The best setup combines dynamic fan-out with hard constraints: budget limits, depth caps, expert-informed starting points."

This is exactly our hierarchical model:

```
CONSCIOUS (expert-informed starting points)
  ↓ spawns
WORKING MEMORY (dynamic fan-out with pool rules)
  - budget: token/cost limits in pool config
  - depth: max_hops in traversal rules
  - constraints: aspect filters, trust thresholds
  ↓ surfaces
SUBCONSCIOUS (cheap retrieval, no attestation authority)
```

> "You want retries, fallbacks, the ability to resume from the last good state."

Because chains ARE the last good state. Agent dies → trails remain → new agent picks up from last attested thought.

**The "Average vs Best" problem:**

His core complaint: Deep Research surfaces average consensus, not expert signal. Can't distinguish his PhD-level sources from news aggregators.

Wellspring's answer: Trust is computed, not assumed.

```
Query: "Afghanistan political dynamics"

Without trust graph:
  → Google results weighted by SEO
  → Average of everything

With trust graph:
  → strickvl's attestations weighted by his identity
  → His vouched sources surface first
  → News articles from unknowns below waterline
```

You don't get "what the internet thinks." You get "what people you trust think, with receipts."

### Halt and Catch Fire

> "Computers aren't the thing. They're the thing that gets us to the thing."

The protocol isn't the point. Trust relationships and provenance trails are what enable something bigger. Wellspring is infrastructure for cognition, not the cognition itself.

---

## RAG with Wellspring Thoughts (2026-01-30)

### The Problem

Traditional RAG:
```
Query → Embed → Vector search → Top-k docs → LLM context → Response
```

Works, but:
- No trust weighting (SEO wins)
- No provenance (where did this come from?)
- No aspect filtering (all contexts mixed)
- Embedding model change = reindex everything

Wellspring RAG needs:
- Trust-weighted retrieval (your graph shapes results)
- Provenance-preserving (because chains survive retrieval)
- Aspect-scoped (different indexes for different contexts)
- Chain-aware (retrieve the thought AND its grounding)

### Architecture Sketch

```
QUERY: "Afghanistan political dynamics"
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  SUBCONSCIOUS (fast, cheap, no attestation authority)   │
│                                                          │
│  Vector index (HNSW/FAISS):                             │
│    - Thought embeddings                                  │
│    - Returns candidate CIDs                              │
│    - NO trust filtering (just similarity)                │
│    - Configured by index_config aspect                   │
│                                                          │
│  Output: [cid_1, cid_2, ... cid_100] + similarity scores│
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  WORKING MEMORY (trust computation + chain walking)      │
│                                                          │
│  For each candidate:                                     │
│    1. Compute trust(me → thought.created_by)            │
│    2. relevance = similarity × trust                     │
│    3. If relevance > waterline: keep                     │
│    4. Walk because chain (up to depth limit)            │
│    5. Collapse chain to context window                   │
│                                                          │
│  Output: [thought + context] ranked by relevance         │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  CONSCIOUS (synthesis + attestation)                     │
│                                                          │
│  - Verify attestations on retrieved thoughts             │
│  - Synthesize response                                   │
│  - Create output thought with because → sources          │
│  - Attest the chain                                      │
│                                                          │
│  Output: Response thought with full provenance           │
└─────────────────────────────────────────────────────────┘
```

### Trust-Weighted Relevance

The key insight: **similarity alone is not relevance**.

```
Traditional:  relevance = similarity(query, doc)
Wellspring:   relevance = similarity(query, thought) × trust(me, creator)
```

Same query, different results for different identities:

```
PhD researcher (strickvl):
  - His verified sources: trust 1.0 → full weight
  - Academic network: trust 0.7 → strong weight
  - News aggregators: trust 0.1 → below waterline

College freshman:
  - Wikipedia: trust 0.8 → surfaces
  - News aggregators: trust 0.5 → surfaces
  - PhD's private sources: no trust path → invisible
```

Not "best for everyone" — best for YOU given YOUR trust relationships.

### Index Configuration as Thoughts

The subconscious doesn't decide what's relevant — it surfaces candidates based on configured indexes. The configuration is itself a thought:

```
THOUGHT: "Index config for research-pool"
  type: "aspect"
  aspect_type: "index_config"
  content:
    embedding_model: "nomic-embed-text-v1.5"
    chunk_strategy: "semantic"    # vs fixed-size
    chunk_overlap: 0.1
    similarity_threshold: 0.6
    max_candidates: 100
    index_scope: "pool"           # vs "identity" vs "global"
    reindex_trigger: "on_sync"    # vs "scheduled" vs "manual"
  created_by: <pool_admin>
  because: [<pool_cid>]
```

Different pools can have different indexing strategies. Research pool might want deep semantic chunking. Chat pool might want recent-first. Your choice.

### Chain Indexing vs Thought Indexing

**Option 1: Index individual thoughts**
- Pro: Fine-grained retrieval
- Con: Lose context, because chain must be walked post-retrieval

**Option 2: Index collapsed chains**
- Pro: Context preserved in embedding
- Con: Chain updates require re-embed, expensive

**Option 3: Hybrid**
- Index thoughts individually
- Maintain "chain summary" thoughts (aspect type)
- Index summaries for coarse retrieval
- Drill into chain for fine-grained

```
THOUGHT: "Chain summary"
  type: "aspect"
  aspect_type: "chain_summary"
  content:
    summary: "Discussion of X leading to conclusion Y"
    thought_count: 47
    participants: [alice_cid, bob_cid]
    timespan: ["2026-01-15", "2026-01-20"]
    topics: ["afghanistan", "political-dynamics"]
  because: [<chain_root>, <chain_tip>]
```

Subconscious indexes summaries for fast "is this chain relevant?" check. If yes, working memory drills into the full chain.

### Grassmann Projection

High-dimensional embeddings live on manifolds. Grassmann projection finds the subspace that captures semantic structure.

For Wellspring:
- Project thought embeddings to lower dimension
- Cluster by semantic similarity
- But ALSO by trust proximity

```
Embedding space:
  [semantic_dims...] + [trust_graph_position]

Two thoughts might be:
  - Semantically similar (close in content)
  - Trust-distant (different parts of your graph)

Retrieval should surface:
  - Semantically close AND trust-close first
  - Then semantically close but trust-distant
  - Trust-close but semantically distant = unexpected but trusted
```

The last case is interesting: "I don't know why this is relevant, but someone I trust linked it." Serendipity via trust.

### Sticking Points

**1. Index freshness**
- New thoughts need embedding
- Chains grow, summaries need update
- Solution: Incremental indexing, triggered by sync

**2. Trust computation at query time**
- Can't pre-compute trust for all viewer × thought pairs
- Solution: Cache trust scores per identity, invalidate on attestation change

**3. Cross-pool search**
- Privacy boundaries must be respected
- Solution: Query multiple pool indexes, merge results, filter by visibility

**4. Embedding model drift**
- New model = incompatible embeddings
- Solution: Store model version in index_config, reindex on model change

**5. Because chain depth**
- Walking full chain is O(depth)
- Solution: Depth limits, chain summaries, lazy expansion

**6. Adversarial embeddings**
- Craft content to game similarity scores
- Solution: Trust weighting naturally demotes untrusted sources

### Subconscious Connection Maintenance

The subconscious layer could continuously maintain semantic neighborhoods:

```
Background process:
  1. New thought arrives
  2. Embed it
  3. Find k-nearest neighbors in index
  4. Create "semantic_proximity" connections (local_forever)
  5. These connections speed up future retrieval

THOUGHT: "Semantic proximity"
  type: "connection"
  content:
    connection_type: "semantic_proximity"
    similarity: 0.87
    model: "nomic-embed-text-v1.5"
  from: <thought_a>
  to: <thought_b>
  visibility: local_forever  # My index, not shared
```

These connections ARE the index — queryable in the graph, not a separate system. Same primitive, thoughts all the way down.

### Query Flow Example

```
Query: "What caused the 2021 Kabul evacuation chaos?"

1. SUBCONSCIOUS
   - Embed query
   - Search index: 100 candidates
   - Return CIDs + similarity scores

2. WORKING MEMORY
   - For each candidate:
     - trust(me, creator): [1.0, 0.8, 0.3, 0.0, ...]
     - relevance = sim × trust: [0.9, 0.7, 0.2, 0.0, ...]
   - Filter by waterline (0.3): 47 candidates remain
   - Walk because chains (depth 3): expand context
   - Collapse to context budget (8k tokens)

3. CONSCIOUS
   - Verify attestations on top sources
   - Synthesize response
   - Create response thought:
     because: [source_1, source_2, source_3]
   - Attest sources used

4. OUTPUT
   Response with full provenance:
   "Based on [source_1] (trust: direct), [source_2] (trust: via academic_network)..."
```

The PhD researcher gets his verified sources. The freshman gets Wikipedia. Same query, trust-appropriate results.

### Long Transitive Trust Problem

With multiplicative decay, long chains collapse:

```
Hops:  1     2     3     4     5     6     7     8
Trust: 0.80  0.64  0.51  0.41  0.33  0.26  0.21  0.17
```

At 7 hops, a 0.9 similarity source gets relevance 0.19 — below typical waterline.

**The tension:**
- Feature: Prevents Sybil gaming (can't just create long vouch chains)
- Bug: Legitimate distant expertise gets demoted

**Solutions:**

**1. Repeaters as Trust Anchors**

From v0.5 spec: certain identities reset chain when they attest.

```
You → 3 hops → Domain Expert (repeater) → attests source
                         ↓
            Chain resets here. You trust expert.
            Expert's attestation = YOUR trust in source.
```

The PhD researcher becomes a repeater for Afghanistan content. If you trust them at 0.8, and they attested a source at 1.0, your effective trust in that source is 0.8 — not 0.8^7.

```
THOUGHT: "Repeater designation"
  type: "attestation"
  content:
    on: <expert_identity>
    aspect: "repeater"
    domain: ["afghanistan", "political-analysis"]
    weight: 1.0
  created_by: <my_identity>
```

**2. Trust Advisory Subscriptions (from dogfood 011)**

Subscribe to distant expert's ratings without full transitive path:

```
THOUGHT: "Trust advisory subscription"
  type: "attestation"
  content:
    aspect_type: "trust_advisory"
    on: <expert_identity>
    weight: 0.7
    scope: ["academic-sources"]
  created_by: <my_identity>
```

Now when expert rates a source, your trust computation blends:
- Your direct path (maybe 0.21 after 7 hops)
- Expert's rating × your subscription weight (0.9 × 0.7 = 0.63)
- Blended: some function that boosts the distant source

**3. Community Trust Pools**

Shared trust graphs for specific domains:

```
"Academic ML Researchers" pool
  - Members attest each other
  - Pool attestation = membership in trusted community
  - You subscribe to pool, not individual chains

Your trust in pool member:
  trust(you, pool) × trust(pool, member)
  = 0.8 × 1.0 = 0.8

Not:
  trust(you, member_via_7_hops) = 0.21
```

**4. Aspect-Specific Decay Rates**

Different domains might tolerate different chain lengths:

```
index_config:
  trust_decay:
    default: 0.8
    academic_citations: 0.95  # Academic chains are longer, more trusted
    social_recommendations: 0.6  # Social chains decay faster
```

Academic citation networks are deep by design. Social media recommendations should decay fast.

**5. Explicit Path Boost**

"I trust this person's entire network for this domain":

```
THOUGHT: "Network trust"
  type: "attestation"
  content:
    on: <expert_identity>
    aspect: "network_trust"
    domain: ["climate-science"]
    depth: 3  # Trust their vouches up to 3 hops
    weight: 0.9
```

Now expert → their_contact → their_contact's_source all get boosted.

**The Retrieval Implication**

For RAG with long chains, the query flow becomes:

```
1. SUBCONSCIOUS: Return candidates (similarity only)

2. WORKING MEMORY:
   For each candidate:
     a. Compute raw transitive trust (might be 0.21)
     b. Check repeater attestations (might boost to 0.8)
     c. Check advisory subscriptions (might blend to 0.5)
     d. Check pool memberships (might override to 0.7)
     e. Final trust = max(raw, boosted paths)
     f. relevance = similarity × final_trust

3. CONSCIOUS: Verify, synthesize, attest
```

The boosting mechanisms are themselves thoughts — queryable, auditable, part of the graph.

**Key insight:** Long chains aren't a bug to fix globally. They're a signal. If you want to trust distant sources, you explicitly create shortcuts (advisories, pools, verified attestations). The decay is the default; the boosts are your choices.

### Repeaters Probably Unneeded (2026-01-30)

After prototyping repeaters in dogfood 018, realized they're redundant machinery.

**The same effect emerges from attestation verification + recording:**

```
1. Query: "Has anyone I trust attested this source?"
   → Find: Expert attested Nature at 1.0

2. Verify: Check expert's signature on that attestation

3. Record: Create your own connection thought
   THOUGHT: "I verified Expert's attestation of Nature"
     type: "connection"
     content:
       connection_type: "verified_attestation"
       original_attestor: expert_cid
       on: nature_cid
       observed_weight: 1.0
     because: [expert_attestation_cid, my_identity]

4. Result: Now you have a direct-ish edge
   Your trust = your trust in Expert × Expert's trust in Nature
   No decay chain, just one multiplication
```

**Pool vetting does this automatically:**

```
New source arrives via sync
  → Pool queries: "Any trusted attestations?"
  → Finds expert attestation, verifies it
  → Creates pool's own attestation
  → Members now have: me → pool → source (2 hops max)
```

The chain shortcut happens through **attestation propagation**, not a special repeater mechanism.

**Benefits of this approach:**
- No new concept (just connections/attestations)
- Auditable (the verification is a thought)
- Revocable (retract your verification thought)
- Queryable (find all sources you've verified via experts)
- Same primitive, thoughts all the way down

**Conclusion:** Remove "repeater" as a special concept. Attestation-copying achieves the same result more elegantly.

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

## Dogfood 001 Results (2026-01-30)

**Files:**
- `wellspring-dogfood-001.jsonl` — 16 thoughts
- `wellspring_cid.py` — CID computation and verification
- `dogfood-001-notes.md` — detailed analysis

**What was tested:**
```
Bootstrap chain:
  bootstrap_terminal_v1 → primitives_v1 → meta_schema_v1 → type schemas

Identities:
  keif_identity (sovereign, self-referential)
  claude_identity (managed, parent=keif)

Real thoughts:
  thought_001: Core insight (memory = traversal)
  thought_002: Merkle properties (claude, because → 001)
  thought_003: Self-describing (keif, because → 001, 002)

Connections:
  thought_002 derives_from thought_001

Attestations:
  keif attests thought_002 +1.0 (with content anchor)
  keif attests connection_001 +1.0
```

**Results:**
- ✅ 16/16 valid because references
- ✅ Trail walking: thought_003 → thought_001, thought_002
- ✅ Attestation discovery: found attestation_001 on thought_002
- ✅ CID computation: SHA-256 hashing works

**Edges surfaced:**
- Bootstrap `created_by: "BOOTSTRAP"` breaks all-CIDs rule (acceptable for terminal)
- Genesis identity is self-referential (pubkey self-proves, signature self-attests)
- Content selectors in because chains work (anchor with exact/prefix/suffix)
- Schema versioning: old thoughts reference old schemas, coexist with new

**Next:** Real Ed25519 signatures, larger graph, speed testing.

---

## Dogfood 002-003 Results (2026-01-30)

**Files:**
- `wellspring_genesis.py` — real Ed25519 signatures, two sovereign identities
- `wellspring-dogfood-002.jsonl` — 10 thoughts, all signatures verified
- `wellspring_genesis_v2.py` — private keys as local-forever thoughts
- `wellspring-dogfood-003.jsonl` — shareable thoughts (5)
- `wellspring-local-secrets.jsonl` — local-forever secrets (2)

**Key insight: Private keys are thoughts too**

```
secret_thought (local_forever)
    ↑ because
identity_thought (shareable, has pubkey)
    ↑ created_by
all subsequent thoughts (verifiable by anyone)
```

- Remote: sees pubkey, verifies signatures, can't resolve secret reference
- Local: has secret, can sign new thoughts
- Revoke: delete secret locally
- Rotate: new identity pair + `same_as` attestation from old
- Backup: explicit export (QR, encrypted file, or pool-scoped sync)

**Visibility model added to spec:**
- `null` (default): sync normally
- `local_forever`: never sync
- `pool:<cid>`: sync only within specific pool

**Multi-device pairing:**
1. New device generates temp keypair
2. Requests join to `keif-devices-pool`
3. Existing device attests membership
4. Secret thought syncs (visibility: pool:keif-devices)
5. New device can sign as same identity

**Spec updated:** v0.5 now includes Identity Pairs and Visibility Model sections.

---

## Dogfood 004 Results (2026-01-30)

**Files:**
- `wellspring_pool_sync.py` — multi-device pool as base sync layer
- `wellspring-dogfood-004-public.jsonl` — 17 public thoughts
- `wellspring-dogfood-004-secrets.jsonl` — 4 pool-scoped secrets

**Structure tested:**

```
KEIF (human identity)
    │
    └── POOL: keif-devices (private, admin: keif)
            │
            ├── LAPTOP (managed, parent: keif)
            │     └── member_of + bilateral attestation
            │
            ├── PHONE (managed, parent: keif)
            │     └── member_of + bilateral attestation
            │
            └── TABLET (managed, parent: keif)
                  └── member_of + bilateral attestation
```

**Bilateral attestation verified:**
- Connection: `device → member_of → pool`
- Device attests +1.0: "I want in"
- Admin attests +1.0: "Pool accepts"
- Both signatures cryptographically verified

**Multi-head signing:**
- Laptop writes thought (created_by: laptop)
- Phone writes thought (created_by: phone)
- Tablet synthesizes, because → [laptop_thought, phone_thought]
- All three are "Keif" - trust chain: device → managed under → keif

**Secrets with pool visibility:**
- All secrets have `visibility: pool:<keif-devices-cid>`
- Sync only to pool members, not public
- External verifier sees public chain, can verify all signatures
- Pool members see secrets, can sign as any device

**Spec updated:** v0.5 now includes Devices Pool Pattern section.

---

## Dogfood 005 Results (2026-01-30)

**Files:**
- `wellspring_revocation.py` — compromise detection and trust degradation
- `wellspring-dogfood-005-revocation.jsonl` — 20 thoughts

**Scenario tested:** Phone stolen, bad actor creates thoughts, owner detects and revokes.

**Timeline:**
```
Day 1-5:  Legitimate phone usage (5 thoughts)
Day 6:    Phone stolen (compromise begins)
Day 6-8:  Bad actor creates thoughts (3 compromised)
Day 8:    Owner detects, revokes device
```

**Revocation mechanism:**
1. **Revocation attestation** (-1.0 on membership connection)
2. **Compromise window marker** (aspect thought defining suspect period)
3. **Flag attestations** (0.0 on each thought in window, via marker)

**Trust recomputation:**
- Before window: still trusted (device valid at creation)
- Within window: flagged 0.0 (requires review)
- After revocation: no trust path (membership revoked)

**Resolution options:**
- Reject (-1.0): "This was the bad actor"
- Verify (+1.0): "I actually wrote this"
- Leave flagged (0.0): "Needs investigation"

**Downstream effects:**
- Alice cited a compromised thought
- Her groundedness drops when marker created
- Warning: "Your source was flagged as potentially compromised"
- She can verify independently or wait for resolution

**Key insight:** Data is immutable. Trust is recomputable. Compromise markers are permanent history.

**Spec updated:** v0.5 now includes Compromise Windows section.

---

## Dogfood 006 Results (2026-01-30)

**Files:**
- `wellspring_vouch_sybil.py` — vouch chains, sybil resistance, voucher accountability
- `wellspring-dogfood-006-vouch.jsonl` — 361 thoughts

**Scenario:** Research pool with vouch chain, one member starts spamming.

**Structure:**
```
Alice, Bob, Carol (core, trust 1.0)
    │
    └── Bob vouches → Dave (0.8)
                        │
                        └── Dave vouches → Eve (0.7)
                                            │
                                            └── EVE SPAMS (150 messages)
```

**Timeline:**
- Day 1-30: Normal activity (~200 messages from all 5 members)
- Day 31-35: Eve spams (30/day vs normal 6/day)
- Day 33: Alice (admin) detects, flags, penalizes

**Trust before/after:**
```
          BEFORE    AFTER
Alice:    1.00      1.00
Bob:      1.00      1.00  (base unchanged)
Carol:    1.00      1.00
Dave:     0.80      0.80  (but vouching power -30%)
Eve:      0.56      0.00  (heavy penalty)
```

**Voucher accountability:**
- Eve spammed → Eve penalized directly
- Dave vouched for Eve → Dave's judgement penalized (vouching power reduced)
- Bob vouched for Dave → Judgement noted, but Dave's own work was fine
- Carol attested +0.7 on Bob's vouch → Counter-evidence, Bob's judgement looks reasonable

**Sybil resistance mechanisms:**
1. Multiplicative decay (0.8^5 = 0.33 at 5 hops)
2. Voucher accountability (bad vouch costs your reputation)
3. Asymmetric cost (identity free, vouch expensive)
4. Audit trail (vouch has because chain)
5. Multiple observers (consensus from independent attestations)

**Key insight:** Judgement score ≠ content trust. You can be trusted for your work but have reduced vouching power.

**Spec updated:** v0.5 now includes Voucher Accountability and Sybil Resistance sections.

---

## Dogfood 007 Results (2026-01-30)

**Files:**
- `wellspring_key_rotation.py` — key rotation via attestation chain
- `wellspring-dogfood-007-rotation.jsonl` — 9 thoughts

**Key insight: `same_as` is redundant**

Rotation is just an attestation pattern:
```
v1 creates: rotation_thought (because: [v1, v2])
v2 attests: +1.0 on rotation_thought
```

Both keys signed. The chain proves continuity. No special connection type needed.

**The proof (walking backward from v2 thought):**
```
v2_thought ← rotation_attestation (by v2) ← rotation_thought (by v1!) ← v1_identity
```

**After rotation:**
- v1 attests on itself: weight 0.0 (deprecated)
- Delete v1 secret: can't sign new, can still verify old
- Clean handoff

---

## Brigading & Trust Sovereignty (2026-01-30)

**Key insight:** Brigading defense is your choice, not protocol-enforced.

**What Wellspring provides:**
- The graph (all attestations visible)
- Tools to compute trust from your perspective

**What you decide:**
- Which pools to subscribe to
- How to weight ratings
- Your waterline during attacks

**Public trust ratings as pools:**
```
Pool: security-researchers-ratings
  - Attestations on identities with trust scores
  - You can subscribe or ignore
  - Anyone can publish competing ratings
```

**Resilience options:**
1. Velocity limits (sudden influx = suspicious)
2. Cluster detection (tight group = coordination)
3. Source diversity (require multiple independent chains)
4. Time weighting (established accounts count more)
5. Your waterline (raise during attacks)

**Visibility without trust:**
- Current networks: block = invisible (can't see coordination)
- Wellspring: low trust = visible but discounted
- You can observe, peer into, report on content you don't trust
- "Block early, block often" → "observe, weight, share"
- Evidence chains enable research on manipulation without giving trust

**Spec updated:** v0.5 now includes Brigading & Trust Network Sovereignty and Visibility Without Trust sections.

---

## Dogfood 008 Results (2026-01-30)

**Files:**
- `wellspring_hello.py` — cold start peer discovery
- `wellspring-dogfood-008-hello.jsonl` — 11 thoughts

**The hello handshake:**

```
OUT-OF-BAND:
  1. Alice creates hello card (identity + pubkey + signature)
  2. Shares via any channel (QR, email, in-person)
  3. Bob verifies cryptographically

IN-BAND:
  4. Alice creates shared pool
  5. Bilateral membership attestation
  6. First messages (grounded in pool)
```

**After handshake:**
- Verified identity (cryptographic proof)
- Private channel (shared pool)
- Because chain begins
- Zero external trust (grows from interaction)

**Discovery options:**
- Direct (high trust): in-person QR, NFC
- Semi-direct (medium): verified email/phone
- Public (low): public hello-cards pool

**Spec updated:** v0.5 now includes Hello Handshake section.

---

## Dogfood 009 Results (2026-01-30)

**Files:**
- `wellspring_appetite.py` — appetite/expectations simulation
- `wellspring-dogfood-009-appetite.jsonl` — 13 thoughts

**Scenario:** Rate limiting driven by aspect thoughts, all pool-scoped.

**Key insight: Config is secrets**

Appetite and expectations are private config that syncs across your devices:

```
alice-devices pool
    │
    ├── appetite aspect (visibility: pool:<devices>)
    │     limits: unknown 10/hr, trusted 1000/hr, expected 500/hr
    │
    ├── expectation: Carol (visibility: pool:<devices>)
    │     expires: 7 days
    │     boost: 50x unknown rate
    │
    └── attack mode aspect (visibility: pool:<devices>)
          because → [baseline appetite, spammer identity]
```

**Scenarios tested:**

1. **Expected partner (Carol)**: Matched expectation → 500/hr limit (50x boost)
2. **Unknown sender (Stranger)**: No expectation → 10/hr limit → rejected at 11
3. **Spammer flood**: 95 messages → only 10 through → rate limiter works
4. **Trusted during attack**: Bob still gets 1000/hr (trust bypasses)
5. **Recovery**: New appetite with `because → attack_mode` — audit trail

**CDN partner pattern:**

CDN joins your devices pool → sees your config → attests enforcement:

```
CDN attestation on appetite:
  weight: 1.0
  content: "I will enforce these limits"
  because: [appetite_cid, cdn_identity]
```

Now the contract is in the graph. Breach? The attestation is there. Audit trail.

**Visibility model verified:**
- Appetite: `visibility: pool:<devices>`
- Expectations: `visibility: pool:<devices>`
- Attack mode: `visibility: pool:<devices>`
- Recovery: `visibility: pool:<devices>`

All config syncs to devices, not broadcast publicly.

**BGP parallel discovered:**

Peer relationships work like BGP autonomous systems:
- Each peer = own pool with bilateral config
- Rate/priority tuned per peer
- High-trust peer with fat pipe = high rates
- Public relay with spammers = rate limited, best effort
- Agreement pool = the contract (attestation = "we agree")

| BGP | WoT |
|-----|-----|
| Route announcements | Thought relay prefs |
| AS path | Because chains |
| Route filtering | Appetite + expectations |
| Peering agreements | Bilateral pool attestations |

**Spec updated:** v0.6 now includes "Peer Agreements (BGP for Thoughts)" section.

**Transfer vs Acceptance — two rulesets:**

Peer agreements control the pipe, not what you believe:

```
PEER LAYER (transfer)        LOCAL LAYER (acceptance)
Rate: 100k/min               Index if: trust > 0.5
Priority: high               Buffer if: trust 0.1-0.5
Relay trust: yes/no          Discard if: trust < 0.1
```

The firehose is options, not beliefs. Accept 100k/min from premium CDN, but only index what meets trust threshold. Buffer zone gets extra local verification.

**Spec updated:** v0.6 now includes "Transfer vs Acceptance" section.

**Pool Schema — self-describing pool config:**

Pool CID is a hash. Humans need "Party Tuesday". Pool schema declares:
- Human-readable name
- Required/optional aspect types
- Schema CIDs for each aspect

```
pool_schema thought (because → pool)
    → declares required_aspects: [appetite, membership]
    → aspect_schemas: { appetite: <schema_cid>, ... }
```

Anyone joining knows what config thoughts to look for.

**Spec updated:** v0.6 now includes "Pool Schema Thought" section.

**Signed Redaction — the visible hole:**

```
REDACTION THOUGHT:
  type: "redaction"
  target: <original_cid>
  reason: "Personal request" | null
  created_by: <same identity as original>
  because: [original_cid]
```

Properties:
- Chain shows the hole (CID still referenced)
- Content removed (if you honor it)
- Only creator can redact their own
- Honoring is YOUR policy (aspects)

```
redaction_policy aspect:
  personal_pools: honor_always
  legal_audit: never_honor  // some contexts need everything
```

Not deletion — the thought exists, the shape is visible, but content is obscured.

**Protocol vs enforcement:**
- Protocol: SHOULD honor (recommendation, not requirement)
- Reference impl: honor by default
- Your policy: based on peering intelligence
- Enforcement: reputational (leak redacted content → lose peer trust)

Like HTTP cache headers — spec recommends, bad actors get reputation, network routes around them. Social contract backed by reputation, not cryptographic guarantee.

**Spec updated:** v0.6 now includes "Redaction Thought" section with protocol/enforcement model.

---

## Dogfood 010 Results (2026-01-30)

**Files:**
- `wellspring_peering.py` — bidirectional peering simulation
- `wellspring-dogfood-010-peering.jsonl` — 17 thoughts

**Scenario:** Two identities establish shared pool and exchange thoughts.

**Flow tested:**
```
1. Alice creates identity + devices pool
2. Alice sets expectation for "The Bear" (pool-scoped, private)
3. Alice publishes hello card (public)
4. The Bear discovers hello card
5. The Bear proposes shared pool
6. Bilateral attestation (both attest membership)
7. Messages flow in shared pool (pool-scoped)
```

**Visibility verified:**
```
Alice sees:     4 messages ✓
The Bear sees:  4 messages ✓
Eve (outsider): 0 messages ← blocked by pool visibility
Eve sees:       1 hello card ← public visible
Eve sees:       0 expectations ← Alice's private config invisible
```

**Key insight:** Alice's expectation was PRIVATE (devices pool). The Bear never saw it. But Alice's acceptance attestation *references* the expectation in its because chain — proving the connection was expected without revealing the expectation content.

```
The Bear's proposal
    ↓
Alice's attestation
    because: [membership, expectation]  ← private thought referenced
    ↓
Grounded acceptance (verifiable, but expectation content hidden)
```

---

## Dogfood 011 Results (2026-01-30)

**Files:**
- `wellspring_trust_network.py` — multi-identity trust dynamics
- `wellspring-dogfood-011-trust-network.jsonl` — 30 thoughts

**Network tested:**
```
A → B (1.0) → C (1.0)
      ↘
       E (0.8) ← C (was 0.8, now -0.5)
A → D (0.7, new entrant)
```

**Scenario:** E spams crypto. C and D downrate. Does A filter E?

**Results:**
```
A's trust for E: 0.512 (via A→B→E)
A's threshold: 0.3

Result: E STILL SURFACES for A
```

**Why?** A's path to E goes through B. B still trusts E at 0.8. C's downrate doesn't affect A's path.

**What each identity sees:**
```
Alice: ✓ indexed (trust 0.51 via B)
Bob:   ✓ indexed (trust 0.80 direct)
Carol: ✗ filtered (trust -0.50, downrated)
Dave:  ✗ filtered (trust 0.00, downrated)
```

**Key insight:** Trust is subjective. Computed from YOUR attestations. C's downrate only affects you if C is in YOUR trust path.

**For A to filter E:**
- A directly downrates E, OR
- B downrates E (breaking A's path), OR
- A subscribes to C's ratings as advisory

**Resolved: Advisory subscriptions are just attestations.**

```
ATTESTATION:
  type: "attestation"
  content:
    aspect_type: "trust_advisory"
    on: carol_cid
    weight: 0.5
    scope: ["spam", "crypto"]
  created_by: alice_cid
```

"I attest I will trust Carol's observed ratings, weighted at 0.5."

Trust computation with advisories:
```
1. Direct/transitive trust for E: 0.512
2. Carol rated E: -0.5, I subscribe at 0.5
3. Blend: 0.512 + (0.5 × -0.5) = 0.262
4. Below 0.3 threshold → FILTERED
```

Same primitive. No new thought type. The attestation declares "I value this person's judgments."

**Spec updated:** v0.6 now includes Trust Advisory Attestation.

---

## Dogfood 012 Results (2026-01-30)

**Files:**
- `wellspring_speed_test.py` — 50-identity stress test
- `wellspring-dogfood-012-speed.jsonl` — 551 thoughts

**Topology tested:**
```
Cluster 1: Dense core (0-9, everyone trusts everyone)
Cluster 2: Chain (10-19, bidirectional)
Cluster 3: Star (20 hub, 21-29 spokes)
Cluster 4: Cycles (30-39, intentional loops)
Cluster 5: Isolated (40-49, sparse)
Cross-cluster bridges: 5→15→25→35→45
```

**Performance:**
```
Trust lookups/sec:     2,669,491
Messages/sec:          11,715
Cache hit rate:        91.5%
Ref verifications/sec: 8,506,757
```

**Trust decay across bridges:**
```
Core → Star via bridge: 0.314 (2 hops)
  User05 → User15 → User25

Star → Isolated: 0.161 (3 hops)
  User20 → User25 → User35 → User45
```

**Filtering:**
```
Messages routed:   2,600
Messages filtered: 21,900
Filter rate:       89.4%
```

High filter rate expected — cluster topology means most identities have no trust path. That's the design working.

**Cycle handling:** ✓ (cluster 4 has intentional loops, no infinite recursion)

---

## v0.6 Changes (2026-01-30)

### WoT Rebrand

`Wellspring Eternal` → `WoT: Wellspring of Thoughts`

- wellspring.com is taken
- wot.rocks, wot.technology available
- Short, memorable, captures the essence

### Expectation Thoughts for Remote Hello

Physical proximity isn't always possible. Pre-authorize expected contacts:

```
THOUGHT: "Expecting hello from Bob"
  type: "expectation"
  content:
    expecting_name: "Bob"
    expecting_channel: "email:bob@example.com"
    expires: "2026-02-01"
  because: [alice_identity]
```

When Bob's hello arrives:
1. Check expectations
2. Find match → boost trust (this was expected)
3. No match → rate-limit (unknown sender)

### Rate Limiting by Appetite

Your appetite is a thought, not a setting:

```
THOUGHT: "Current appetite settings"
  type: "aspect"
  aspect_type: "preference"
  content:
    unknown_sender_rate: 10/hour
    trusted_sender_rate: 1000/hour
    expectation_boost: 100x
    attack_mode: false
  because: [my_identity]
```

**During normal operation:** liberal limits, expectations active
**During attack:** raise waterline, tighten rates, drop unknowns

### CDN Peering Layer

Thoughts flow through a peering layer:

```
Your Device ←→ Local Cache ←→ Peer CDN ←→ IPFS Pinning
     │              │              │            │
   hot graph     warm sync    thought relay   cold storage
```

**Why CDN suits WoT:**
- CIDs are perfect cache keys (immutable content)
- No expiry needed, evict by heat decay
- Anyone can run a peer relay
- IPFS fallback for cold storage

**Rate limiting at peer layer:**
- Check sender reputation (vouch chain)
- Check receiver appetite (expectations)
- Unknown + no expectation → queue, rate-limit
- Known OR expected → immediate relay
- Attack pattern → reject at edge

CDN absorbs flood attacks. Your device only sees what passes your filter.

### Service Layer Economics

Protocol is free. Services compete.

| Service | Value Add | Pricing |
|---------|-----------|---------|
| High-availability pinning | 99.9% uptime, multi-region | Storage + egress |
| Managed algo feeds | Curated salience, topic filtering | Subscription |
| Search & discovery | Full-graph indexing | Query volume |
| Negotiation agents | Automated coordination | Per-negotiation |
| Identity bootstrap | KYC bridge, reputation transfer | One-time |
| Enterprise pools | Compliance, audit trails, SSO | Per-seat |
| Priority CDN | Guaranteed bandwidth, SLA | Subscription |

**Why this works:**
- No data hostage (export everything, any time)
- Compete on service, not lock-in
- Natural pricing (pay for convenience, not access)
- Race to quality (lose trust = lose customers)

---

## Version History

- **v0.4**: Core spec with single primitive, because chains, attestations
- **v0.5**: + Hierarchical agents, attention sovereignty, managed workspaces, Rust/WASM direction
- **v0.6**: + WoT rebrand, expectation thoughts, appetite-based rate limiting, CDN peering layer, service economics, BGP-style peer agreements, transfer vs acceptance, pool schemas, signed redaction, trust advisory attestations

**Dogfoods:**
- 001-003: Bootstrap, signatures, visibility model
- 004: Pool sync, bilateral attestation
- 005: Revocation, compromise windows
- 006: Vouch chains, sybil resistance
- 007: Key rotation via attestation
- 008: Hello handshake
- 009: Appetite/expectations, rate limiting
- 010: Bidirectional peering, shared pool
- 011: Trust network dynamics, advisory subscriptions
- 012: Speed test (50 identities, 2.6M trust lookups/sec)
- 013: Real Ed25519 cryptography (11 thoughts, all signatures verified)
- 014: Speed test with real crypto (695 thoughts, 10.7k verifications/sec)
- 015: Boundary verification (isolated pools, shared space, graceful walls)
- 016: Multi-instance sync (3 nodes, HTTP endpoints, bloom filter exchange)
- 017: RAG with trust-weighted retrieval (expert beats noise despite lower similarity)
- 018: Repeaters explored, found redundant with attestation-copying
- 019: 12-node network simulation (3 clusters, full convergence, cross-cluster propagation)
- 020: Private negotiation with public attestation (15 nodes, 5 pools, boardroom pattern)
- 021: Visibility-aware sync filtering (pool membership, peer agreements, provenance tracking)

---

## Dogfood 021 Results (2026-01-30)

**Files:**
- `wellspring_node_v2.py` — Enhanced node with visibility filtering
- `wellspring_visibility_test.py` — Visibility filtering test
- `wellspring-dogfood-021-visibility.json` — Results

**Scenario:** Verify sync respects visibility rules based on pool membership and peer agreements.

**Network:**
```
4 Nodes: Alice, Bob, Carol, Eve

3 Pools:
  1. Public Announcements (visibility: public)
  2. Internal Team (visibility: members_only) → Alice, Bob
  3. Partner Collab (visibility: members_only) → Alice, Carol

Peering Agreements:
  Alice ↔ Bob: share Internal pool
  Alice ↔ Carol: share Partner pool
  Alice ↔ Eve: public only (no shared pools)
```

**Thoughts created by Alice:**
```
1. Public announcement    (visibility: null)             → sync to everyone
2. Internal memo          (visibility: pool:internal)    → sync to Bob only
3. Partner proposal       (visibility: pool:partner)     → sync to Carol only
4. Local secret           (visibility: local_forever)    → never sync
5. DM to Bob              (visibility: participants_only) → sync to Bob only
```

**Filtering results:**
```
Alice → Bob:
  Filtered: local_forever (1), no pool access (1: partner)
  Shared: 7 thoughts (public + internal + DM + pools + identity)

Alice → Carol:
  Filtered: local_forever (1), no pool access (1: internal), not participant (1: DM)
  Shared: 6 thoughts (public + partner + pools + identity)

Alice → Eve:
  Filtered: local_forever (1), no pool access (2: internal + partner), not participant (1)
  Shared: 5 thoughts (public + pools + identity)
```

**Verification:**
```
Bob sees:   ✓ Q1 Results    ✓ Internal Strategy    ✓ Direct Message
            ✓ (hidden) Partnership Draft   ✓ (hidden) Personal Reminder

Carol sees: ✓ Q1 Results    ✓ Partnership Draft
            ✓ (hidden) Internal Strategy   ✓ (hidden) Personal Reminder   ✓ (hidden) Direct Message

Eve sees:   ✓ Q1 Results
            ✓ (hidden) Internal Strategy   ✓ (hidden) Partnership Draft
            ✓ (hidden) Personal Reminder   ✓ (hidden) Direct Message
```

**Sync provenance tracking:**
- Each received thought creates a `received_via` connection thought
- `visibility: local_forever` — never syncs (your audit trail only)
- Bob's provenance for public thought shows received_via Alice ✓
- Alice has no provenance for her own created thoughts ✓

**Visibility rules implemented:**
```python
def _can_share_with_peer(thought, peer_cid):
    visibility = thought.get("visibility")

    # No visibility = public
    if visibility is None or visibility == "public":
        return True

    # Never share local_forever
    if visibility == "local_forever":
        return False

    # Pool-scoped: check membership OR peering agreement
    if visibility.startswith("pool:"):
        pool_cid = visibility[5:]
        if is_pool_member(pool_cid, peer_cid):
            return True
        if pool_cid in get_shared_pools(peer_cid):
            return True
        return False

    # Participants-only: check content.participants
    if visibility == "participants_only":
        participants = thought.content.get("participants", [])
        return peer_cid in participants or peer_name in participants

    return False  # Unknown visibility = don't share (safe default)
```

**Key insight: Peering agreements are the control layer**

Pool membership + peering agreements together determine what syncs:

```
VISIBILITY CHECK:
  1. Is this local_forever? → NEVER sync
  2. Is this public? → ALWAYS sync
  3. Is this pool-scoped?
     a. Is peer a member of that pool? → sync
     b. Do we have a peering agreement for that pool? → sync
     c. Neither? → DON'T sync
  4. Is this participants-only?
     → Check if peer is in participants list
```

The peering agreement is itself auditable — it's thoughts in the graph. Who you share what pools with is tracked, not hidden.

---

## Dogfood 020 Results (2026-01-30)

**Files:**
- `wellspring_private_negotiation.py` — multi-pool privacy simulation
- `wellspring-dogfood-020-negotiation.json` — pool and attestation CIDs

**Scenario:** Public request, private negotiation, multi-party public attestation.

**Network:**
```
15 Nodes:
  - Humans: Alice, Bob, Carol, Dave, Eve, Frank
  - Bots: Agent-1, Agent-2, Agent-3
  - Orgs: OrgA-Node, OrgB-Node, OrgC-Node
  - Infrastructure: PublicRelay, ArchiveNode, IndexNode

5 Pools:
  1. Public Commons        (visibility: public, access: open)
  2. OrgA Internal         (visibility: members_only, access: invite)
  3. Alice-Agent1 Negotiation (visibility: participants_only, access: closed)
  4. Q4 Analysis Review    (visibility: participants_only, access: closed)
  5. Public Archive        (visibility: public, access: attested_only)
```

**The "Boardroom Pattern" Workflow:**

```
┌─────────────────────────────────────────────────────────────────┐
│  PUBLIC COMMONS                                                  │
│    Alice: "Need Q4 analysis"                                     │
│    Agent-1: "I can help, discuss privately?"                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │ move to private
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ALICE-AGENT1 NEGOTIATION (private)                              │
│    Alice shares confidential data                                │
│    Agent-1 produces draft 1                                      │
│    Agent-1 produces draft 2                                      │
│    Alice: "add regional breakdown"                              │
│    Agent-1 produces final                                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ expand for review
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Q4 ANALYSIS REVIEW (private, +Bob)                              │
│    Alice shares final with Bob                                   │
│    Bob: "Looks solid. Approved."                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ attest publicly
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PUBLIC ARCHIVE                                                  │
│    Alice attests: "Q4 analysis completed satisfactorily"        │
│    Agent-1 attests: "I performed analysis for Alice"            │
│    Bob attests: "I reviewed and approved"                       │
│    Combined: "Multi-party attestation: completed and verified"  │
└─────────────────────────────────────────────────────────────────┘
```

**What the public can see (Carol's perspective):**
```
✓ Attestations exist (4 total)
✓ Who participated (Alice, Agent-1, Bob)
✓ That work was completed (attestation statements)
✓ A deliverable exists (CID reference)
✗ Cannot see actual analysis content
✗ Cannot see negotiation process
✗ Cannot see confidential data
✗ Cannot see draft iterations
```

**Provenance trace from public:**
```
Combined Attestation (public)
  ├── Alice's attestation (public)
  │     └── references: agent_final (PRIVATE CID) ← opaque
  ├── Agent-1's attestation (public)
  │     └── references: agent_final (PRIVATE CID) ← same CID
  └── Bob's attestation (public)
        └── references: agent_final (PRIVATE CID) ← same CID
```

The CID *proves* all three attest the same deliverable without revealing its content.

**Key insight: "Boardroom pattern"**

Like a corporate board meeting:
- **Public:** The meeting happened, who attended, that decisions were made
- **Private:** What was discussed, the documents reviewed, the deliberations

The because chains reference private CIDs. Anyone can verify the attestations are about the same work (CID match) without accessing the work itself. Multi-party signatures prove consensus without disclosure.

**Privacy model validated:**
- Pool-scoped thoughts stay in pool (in full impl; simulation leaks for testing)
- Public attestations reference private work via CID
- Outsiders see shape of provenance, not content
- Participants can expand access (Alice → Bob) by creating new pools

---

## Dogfood 019 Results (2026-01-30)

**Files:**
- `wellspring_network_sim.py` — 12-node network simulation
- `wellspring-dogfood-019-network.json` — Final state

**Topology:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  CLUSTER A: Research          CLUSTER B: Engineering                │
│  ┌─────────────────────┐      ┌─────────────────────┐              │
│  │ Alice ─ Bob         │      │ Eve ─ Frank         │              │
│  │   │  ╲ ╱  │         │      │  │  ╲ ╱  │          │              │
│  │ Carol ─ Dave        │      │ Grace ─ Henry       │              │
│  └─────────┬───────────┘      └─────────┬───────────┘              │
│            │                            │                           │
│      Carol↔Eve              Eve↔Ivy                                │
│      Dave↔Frank                        │                           │
│      Alice↔Jack ──────────────────┐    │                           │
│                                   │    │                           │
│                    ┌──────────────┴────┴────────────┐              │
│                    │  CLUSTER C: Partners           │              │
│                    │  Ivy ─ Jack                    │              │
│                    │   │  ╲ ╱  │                    │              │
│                    │ Kate ─ Leo                     │              │
│                    └────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

**Results:**
```
Nodes: 12
Peerings: 22 (dense intra-cluster, sparse bridges)
Initial thoughts: 15
Sync rounds to converge: 6
Total thought transfers: 297

Final state: ALL 12 nodes have exactly 27 thoughts ✓
```

**Cross-cluster propagation verified:**
- Leo (Partners, farthest from Research) sees Alice's research ✓
- Eve (Engineering) responded to Alice's work via bridge
- Ivy (Partners) responded to Bob's work
- Jack created summary referencing sources from all 3 clusters

**Key observations:**
1. Intra-cluster sync is fast (dense peering, 1 round)
2. Cross-cluster requires bridge nodes (Carol↔Eve, Alice↔Jack)
3. Multiple bridges provide redundancy (Dave↔Frank backup)
4. Response threads create cross-cluster because chains
5. Full convergence achieved despite sparse inter-cluster connectivity

---

## Dogfood 017 Results (2026-01-30)

**Files:**
- `wellspring_rag.py` — Semantic index with trust-weighted retrieval
- `wellspring-dogfood-017-rag.json` — Pool state with thoughts and trust scores

**The key demonstration:**

Query: "Explain how transformer neural networks work"

| Source | Similarity | Trust | Relevance |
|--------|-----------|-------|-----------|
| RandomUser42 (hype) | **0.330** | 0.2 | 0.066 |
| Dr. Sarah (expert) | 0.091 | **1.0** | **0.091** ← WINS |

Expert content with lower similarity beats high-similarity noise because of trust weighting.

**Components built:**

1. **SemanticIndex** — Pool-level indexer
   - Configurable via `index_config` aspect thought
   - TF-IDF fallback (works offline), pluggable to neural embeddings
   - Returns (cid, similarity) tuples

2. **Trust-weighted query**
   ```
   relevance = similarity × trust(viewer, creator)
   ```

3. **Connection tracking**
   - Thoughts that reference others tracked via `because`
   - Chain depth computed (how grounded is this?)
   - Connections surface related thoughts

4. **Context window generation**
   - Collapses top results + their because chains
   - Respects token budget
   - Ready for LLM injection

5. **Semantic neighborhoods**
   - Find similar thoughts to a given thought
   - Could become automatic `semantic_proximity` connections

**Index config as a thought:**
```
type: "aspect"
content:
  aspect_type: "index_config"
  embedding_model: "tfidf"
  similarity_threshold: 0.05
  max_candidates: 50
  chunk_strategy: "whole_thought"
  index_scope: "pool"
```

Different pools can have different indexing strategies. Research pool uses deep semantic models. Chat pool uses recent-first. Your choice.

---

## Dogfood 016 Results (2026-01-30)

**Files:**
- `wellspring_node.py` — Wellspring node with FastAPI HTTP endpoints
- `wellspring_sync_test.py` — Multi-node orchestration test
- `wellspring-dogfood-016-sync.json` — Full sync state

**Architecture:**
```
┌──────────────┐     HTTP      ┌──────────────┐     HTTP      ┌──────────────┐
│    Alice     │◄────────────►│     Bob      │◄────────────►│    Carol     │
│   :8001      │               │    :8002     │               │    :8003     │
└──────────────┘               └──────────────┘               └──────────────┘
```

**Endpoints per node:**
- `GET /` — Stats (thought count, verified, rejected)
- `GET /identity` — Node's identity thought
- `GET /bloom` — Bloom filter of known CIDs
- `POST /sync` — Receive bloom, return thoughts peer is missing
- `POST /receive` — Receive thoughts, verify, merge
- `GET /thoughts` — List all thoughts
- `POST /thoughts` — Create new thought

**Sync protocol:**
```
1. Dst sends bloom filter to Src
2. Src checks each CID against bloom
3. Src resolves dependencies (identities needed to verify content)
4. Src returns thoughts Dst probably doesn't have (identities first)
5. Dst receives, sorts (identities first), verifies signatures, merges
```

**Dependency resolution:**
- For each thought being sent, check if receiver has the signing identity
- If not, include that identity in the payload
- Order: identities first, then content (receiver can verify in one pass)
- Sync payload is self-sufficient — no separate identity exchange needed

**Test results:**
```
Initial (isolated):
  Alice: 3 thoughts (identity + 2 messages)
  Bob:   2 thoughts (identity + 1 message)
  Carol: 4 thoughts (identity + 3 messages)

Sync rounds:
  1. Alice ↔ Bob (identities + content)
  2. Bob ↔ Carol (identities + content)
  3. Bob → Alice (propagates Carol's thoughts)

Final:
  Alice: 9 thoughts ✓
  Bob:   9 thoughts ✓
  Carol: 9 thoughts ✓

Full convergence: ✓
All signatures verified: ✓ (8 per node, 0 rejected)
```

**Propagation verified:**
- Alice's thoughts reached Carol (via Bob)
- Carol's thoughts reached Alice (via Bob)
- Signatures verified at each destination

**Key insights:**
1. Bloom filter minimizes bandwidth (only send missing thoughts)
2. Identity dependencies auto-resolved (sync payload is self-sufficient)
3. Ordering matters: identities first, then content (single verification pass)
4. Signatures verify at destination, not in transit
5. Linear topology still achieves full convergence with enough rounds

**Future: Sync Provenance as Thoughts**

Sync path is just a connection thought — same primitive, no separate metadata:

```
THOUGHT: "I received this via Bob"
  type: "connection"
  content:
    connection_type: "received_via"
    from: <thought_cid>
    via: <bob_identity_cid>
  created_by: <my_identity>
  because: [<thought_cid>, <bob_identity_cid>]
  created_at: <timestamp>
  visibility: local_forever  # My sync state, not shared
```

Use case: Can't verify a thought (missing identity or because reference):

```
1. Query local graph: "received_via connections for this CID"
2. Find: "I got this from Bob"
3. Request upstream: GET bob/thoughts/{missing_cid}
4. Bob queries his graph: "I got it from Carol"
5. Chain back until you find a node that has it
6. Fetch, verify, done
```

Like BGP AS path — you know the route, can trace back to resolve. But it's thoughts all the way down, not a separate metadata store.

Also enables:
- Reputation tracking (peer that sends unverifiable junk = bad peer)
- Debugging sync issues (query your own graph for provenance)
- Selective re-sync (re-request from known-good peer)
- Audit trail (when did I first see this? from whom?)

---

## Dogfood 015 Results (2026-01-30)

**Files:**
- `wellspring_boundary.py` — isolated pools with shared collaboration space
- `wellspring-dogfood-015-boundary.jsonl` — 19 thoughts

**Scenario:** Two teams (Alpha, Bravo) with private internal pools share work in a third space.

**Structure:**
```
┌─────────────────┐     ┌─────────────────┐
│   ALPHA POOL    │     │   BRAVO POOL    │
│  Dev1 → Dev2    │     │  Dev1 → Dev2    │
│    → Lead       │     │    → Lead       │
│  (full verify)  │     │  (full verify)  │
└────────┬────────┘     └────────┬────────┘
         │ publication           │ publication
         ▼                       ▼
┌─────────────────────────────────────────┐
│           SHARED SPACE                   │
│  Joint insight → [Alpha pub, Bravo pub]  │
│  (verify sigs, boundary on internal refs)│
└─────────────────────────────────────────┘
```

**Verification results:**

From shared space:
```
✓ joint_insight
  ✓ alpha_publication
    ◯ alpha_conclusion  ← BOUNDARY (not in our pool)
  ✓ bravo_publication
    ◯ bravo_conclusion  ← BOUNDARY (not in our pool)
```

From Alpha's perspective:
```
✓ joint_insight
  ✓ alpha_publication
    ✓ alpha_conclusion
      ✓ research1 → research2 → lead  ← FULL CHAIN
  ✓ bravo_publication
    ◯ bravo_conclusion  ← BOUNDARY
```

**Key insight:** Boundary is graceful, not failure.

- ✓ VERIFIED = Signature valid, thought in pool
- ◯ BOUNDARY = CID referenced but thought not visible

The *shape* of provenance is visible (CIDs in because chain), but *content* is opaque. The lead's signature IS the trust anchor at the boundary — you trust them to have verified their team's work.

---

## Dogfood 013 Results (2026-01-30)

**Files:**
- `wellspring_real_crypto.py` — real Ed25519 key generation/signing/verification
- `wellspring-dogfood-013-crypto.jsonl` — 11 cryptographically verified thoughts

**What was tested:**
```
Real Ed25519 cryptography:
  - Key generation: Ed25519PrivateKey.generate()
  - Signing: private_key.sign(message)
  - Verification: public_key.verify(signature, message)
```

**Signature coverage:**
- type, content, created_by, because, created_at
- visibility (if present)
- CID computed AFTER signature (includes signature)

**Identity bootstrap pattern:**
```python
# created_by stays "GENESIS" — pubkey in content is the proof
identity_thought = SignedThought(
    type="identity",
    content={"name": name, "pubkey": pubkey_hex},
    created_by="GENESIS"  # Not self-referential, pubkey is proof
)
identity_thought.sign(private_key)
cid = identity_thought.cid  # Computed after signing
```

**Key rotation with dual signatures:**
```
1. Rotation thought signed by OLD key (declares new pubkey)
2. Acknowledgment signed by NEW key (proves possession)
3. Both reference same identity CID
4. Chain is cryptographically verifiable
```

**Tamper detection:**
- Signature binds to exact content
- Any modification invalidates signature
- Can't replay signatures across different content

**Results:**
```
Thoughts verified: 11
Invalid signatures: 0
All signatures verified: ✓
```

---

## Dogfood 014 Results (2026-01-30)

**Files:**
- `wellspring_speed_crypto.py` — 50-identity speed test with real Ed25519
- `wellspring-dogfood-014-speed-crypto.jsonl` — 695 cryptographically verified thoughts

**Topology:** Same as dogfood 012 (dense core, chain, star, cycles, isolated + bridges)

**Real Ed25519 Performance (Single Thread, Unoptimized):**

| Operation | Rate | Per-op |
|-----------|------|--------|
| Key generation | 6,955/sec | 0.14ms |
| Attestation signing | 20,544/sec | 0.05ms |
| Message signing | 23,164/sec | 0.04ms |
| **Signature verify** | **10,748/sec** | **0.09ms** |
| Trust lookups | 1,090,774/sec | — |
| Message routing | 3,900,968/sec | — |

**Key insight:** Verification is the bottleneck (~2x slower than signing). Ed25519 asymmetry is expected. But 10k verifications/sec is still 200 per identity per second in 50-node sim.

**Comparison with dogfood 012 (simulated crypto):**
- Trust lookups: 2.6M → 1.1M/sec (still cache-dominated, plenty fast)
- Message signing: 11.7k → 23k/sec (real crypto faster than fake hash work!)

**Optimization targets:**
1. Batch verification (libsodium supports this)
2. Verification caching (CID is immutable, verify once)
3. Lazy verification (surface first, verify async)
4. WASM/Rust for hot paths

**Results:**
```
Total thoughts:   695
All signatures:   ✓ VALID
Filter rate:      87.8% (expected given topology)
```

See: `wot-v0.6.md`

*Last updated: 2026-01-30 (v0.6 session)*

---

## Pool-Peer-Rules: Keyvault Collapse (2026-01-31)

**The insight:** Keyvaults and shared secrets between identities collapse to three primitives: pool, peer, rules.

**The pattern:**

```
POOL (who's in the trust boundary)
  × PEER (who I exchange with)  
  × RULES (what pool requires/accepts)
  = keyvault semantics without keyvault infrastructure
```

**How it works:**

1. **Pool as trust boundary:** Create private pool (e.g., `keif-devices`)
2. **Identity membership:** Devices get bilateral attestation into pool
3. **Visibility rules:** Secrets marked `visibility: pool:<cid>` only sync within members
4. **Peering controls:** Explicit agreements about what pools to share with each peer
5. **Revocation:** Negative attestation on membership connection

**What this replaces:**

| Traditional Keyvault | WoT Pool-Peer-Rules |
|---------------------|---------------------|
| Separate secret management system | Secrets are thoughts |
| ACLs as config | ACLs as attestations |
| Audit logs | Because chains |
| Key rotation ceremony | New identity pair + `same_as` attestation |
| Multi-device sync | Pool membership + visibility |
| Revocation lists | Negative attestations on membership |

**Why this matters:**

No impedance mismatch between "your data" and "your secrets." Same protocol, same verification, same audit trail. The visibility model + pool membership + peering agreements = complete access control.

**The devices pool is the first keyvault:**

```
HUMAN IDENTITY (Keif)
    │
    ├── POOL (keif-devices, private, admin: keif)
    │
    ├── DEVICE (Keif@laptop) ─→ member_of ─→ keif-devices
    │       └── bilateral attestation
    │
    ├── DEVICE (Keif@phone) ─→ member_of ─→ keif-devices
    │       └── bilateral attestation
    │
    └── SECRETS (visibility: pool:keif-devices)
            └── sync within pool only
```

**Implementation status:** Core patterns in spec (v0.7). Daemon (thread-3) has gRPC peering. Ready to test multi-device secret sync.


---

## Domain Portfolio (2026-01-31)

More names than remembered:

| Domain | Status | Notes |
|--------|--------|-------|
| wot.rocks | Active | Main landing page |
| wot.technology | Active | Technical docs |
| wot.digital | Held | — |
| wot.mobi | Held | Mobile angle? |
| wot.services | Held | Service layer? |
| wotwot.uk | Held | UK presence |

**Current site structure (in ./wot-sites):**
- wot.rocks → Consumer landing ("the why")
- wot.technology → Technical spec ("the how")
- now.pub → Identity namespace (live status/presence)

**Unused but available:**
- wot.digital → could be developer portal?
- wot.mobi → mobile-first demo?
- wot.services → service directory for the protocol layer?
- wotwot.uk → localized or quirky branding?


---

## Zero Trust vs WoT Analysis (2026-01-31)

**Sources:** [NIST Zero Trust](https://www.nist.gov/blogs/taking-measure/zero-trust-cybersecurity-never-trust-always-verify), [Cloudflare Zero Trust](https://www.cloudflare.com/zero-trust/products/access/), [Microsoft Zero Trust](https://learn.microsoft.com/en-us/security/zero-trust/zero-trust-overview)

### Core Zero Trust Principles

1. **"Never trust, always verify"** — every request authenticated, authorized, validated
2. **Least privilege** — minimum access for specific task
3. **Assume breach** — contain and mitigate, don't just prevent
4. **Continuous verification** — not just at login, but ongoing
5. **Device posture** — device health is as important as user identity

### Where Zero Trust and WoT Align

| Zero Trust | WoT Equivalent |
|------------|----------------|
| Never trust by default | Trust computed from attestations, starts at 0 |
| Verify every request | Signature verification on every thought |
| Continuous re-verification | Trust decays, requires fresh attestations |
| Device posture checks | Device identity as managed thought (pool membership) |
| Identity + context | Identity + aspects + pool membership |
| Least privilege | Pool visibility rules, appetite limits |
| Assume breach | Compromise windows, revocation attestations |
| Microsegmentation | Pools as trust boundaries |

### Where They Differ

| Zero Trust (Enterprise) | WoT (Personal/Distributed) |
|------------------------|---------------------------|
| **Centralized policy enforcement** (Cloudflare/Okta/Azure as chokepoint) | **Distributed policy** (each node computes own trust) |
| **Binary access decisions** (allow/deny) | **Continuous trust scores** (0.0-1.0, waterline threshold) |
| **Admin-defined policies** | **Self-sovereign attestations** (your algo, your rules) |
| **Session-based** (login → timeout → re-auth) | **Per-thought verification** (each CID self-verifies) |
| **Identity from IdP** (Okta, Azure AD, Google) | **Identity from keypair** (ed25519, self-generated) |
| **Revocation = central list** | **Revocation = attestation** (negative weight on membership) |
| **Trust the enforcement point** | **Trust no single point** (verify at edge) |

### The Key Tension: Centralized Enforcement

Zero Trust architectures still require a **trusted enforcement point**:

```
User → Cloudflare Access → Policy Check → Resource
              ↑
        YOU TRUST THIS
```

WoT pushes verification to the edge:

```
Thought arrives → Local signature check → Trust computation → Above waterline?
                        ↑
                  YOU VERIFY THIS
```

**Zero Trust:** "We don't trust the network, but we trust the policy engine."
**WoT:** "We don't trust anything — verify locally, compute trust from graph."

### What WoT Can Learn from Zero Trust

1. **Device posture as first-class concept**
   - Not just "is this device in my pool" but "is this device healthy"
   - Device attestations: OS version, security state, compliance
   - Parallels: device aspects with posture requirements

2. **Continuous verification, not just at sync**
   - Zero Trust re-verifies on every request
   - WoT could decay trust faster for unattested activity
   - "When did I last see a fresh attestation from this identity?"

3. **Context-aware policies**
   - Zero Trust: location, time, device type, behavior
   - WoT: aspects already support this (mode switching)
   - Could add: source IP aspect, temporal aspects, geo-fencing via aspects

4. **Session timeout equivalents**
   - Zero Trust forces re-auth after timeout
   - WoT: attestation TTL? "This trust decays to 0 after 7 days without refresh"
   - Pool rules could enforce: "membership requires attestation within N days"

### What Zero Trust Could Learn from WoT

1. **Decentralized verification**
   - Zero Trust depends on Cloudflare/Okta being trustworthy and available
   - WoT: verify locally, no single point of failure
   - Outage of IdP ≠ lockout (your local graph still works)

2. **Transparent policy (because chains)**
   - Zero Trust policies are admin black boxes
   - WoT: "Why was I denied?" → walk the because chain
   - Audit trail is the graph itself

3. **Self-sovereign identity**
   - Zero Trust: identity owned by enterprise/provider
   - WoT: identity owned by keypair holder
   - Portable, no vendor lock-in

4. **Gradual trust, not binary**
   - Zero Trust: you're in or you're out
   - WoT: trust 0.3 means limited access, trust 0.9 means full access
   - Waterline adjusts per context

### Hybrid: WoT as Zero Trust Layer

Could WoT provide Zero Trust semantics for personal/decentralized use?

```
ENTERPRISE ZERO TRUST              WOT ZERO TRUST
─────────────────────              ──────────────
Cloudflare/Okta                    Your local daemon
Policy engine                      Trust graph computation
IdP integration                    Hello handshake + vouch chains
Device posture agent               Device pool membership + aspects
Access decision                    Waterline check
Audit log                          Because chains
Revocation                         Negative attestations
```

**The pitch:** "Zero Trust for your personal infrastructure, without the enterprise overhead."

### Implementation Angles

1. **Pool rules as Zero Trust policies**
   ```
   pool_rules:
     require_device_attestation: true
     attestation_max_age: 7d
     require_mfa_aspect: true
     allowed_sources: [keyboard, hardware_key]
   ```

2. **Continuous verification via attestation freshness**
   ```
   trust_computation:
     base_trust: from vouch chain
     decay_factor: 0.95 per day since last attestation
     require_fresh: true for high-stakes pools
   ```

3. **Device posture as managed identity aspects**
   ```
   device_identity:
     type: managed
     parent: human_identity
     aspects:
       - os_version: "macOS 15.2"
       - disk_encrypted: true
       - firewall_enabled: true
       - last_security_scan: 2026-01-30
   ```

4. **Breach detection via anomaly aspects**
   ```
   anomaly_detection (subconscious layer):
     - velocity: 100 thoughts/hr (normal: 10)
     - source: new device not in pool
     - action: flag for review, raise waterline
   ```

### Conclusion

**Not competing — complementary layers.**

- Enterprise Zero Trust: protects corporate resources from untrusted networks
- WoT: protects personal cognition from untrusted information

Both share: "never trust, always verify." Differ on: who does the verifying (central vs distributed), what's being protected (resources vs thoughts), and who sets policy (admin vs self).

**WoT could BE a Zero Trust implementation** for personal/decentralized contexts — same principles, different enforcement model.


---

## Predefined Aspect Trees (2026-01-31)

**The insight:** Technical aspects (device posture, identity verification, etc.) can be predefined as connected hierarchies. Walk up to find category, walk down to find all checks.

### Aspect Hierarchy Pattern

```
ROOT ASPECT (category)
├── instance_of connections to children
├── children can have children
└── pool rules reference root, get all descendants

Example: device_posture tree
├── os_security
│   ├── os_version: "macOS 15.2"
│   ├── patch_level: "2026-01-15"
│   └── secure_boot: true
├── storage_security
│   ├── disk_encrypted: true
│   └── backup_verified: "2026-01-30"
└── network_security
    ├── firewall_enabled: true
    └── vpn_required: false
```

### Why This Matters

**Pool rules become concise:**
```yaml
pool_rules:
  require_aspects:
    - device_posture  # means "all children attested"
```

Instead of listing every specific check, reference the root. Protocol resolves descendants.

**Discovery via chain walking:**
```
"What device posture aspects exist?"
  → find all thoughts where type=aspect AND has instance_of chain to device_posture root

"Does this device meet requirements?"
  → for each required root aspect
  → find all descendants
  → check attestations exist for each
```

**Extensibility without breaking rules:**
- Add new child aspect (e.g., `biometric_enabled`)
- Existing pool rules automatically include it (they reference root)
- No pool config update needed

### Predefined Trees for Zero Trust

| Root Aspect | Children | Purpose |
|-------------|----------|---------|
| `device_posture` | os_security, storage_security, network_security | Device health |
| `identity_verification` | mfa_enabled, key_type, backup_verified | Identity strength |
| `network_context` | source_ip, geo_location, connection_type | Request context |
| `temporal_context` | time_of_day, day_of_week, session_duration | Time-based rules |
| `behavior_baseline` | typing_pattern, request_velocity, access_pattern | Anomaly detection |

### Bootstrap Aspect Trees

These could ship as "standard library" thoughts:
```
wellspring://stdlib/aspects/device_posture
wellspring://stdlib/aspects/identity_verification
wellspring://stdlib/aspects/network_context
```

Reference them in pool rules. Your attestations fill in the values. The tree structure is shared infrastructure.

**Like schema registries, but for policies.**


---

## wot.services: Ingestion Layer (2026-01-31)

**The idea:** Services that convert external sources into thought feeds. Run by us, or self-host.

### Source → Thought Converters

| Source | Service | Output |
|--------|---------|--------|
| Email (SMTP) | wot.services/email | Sender as identity, thread as because chain |
| RSS/Atom | wot.services/rss | Feed items as thoughts, feed as pool |
| Podcasts | wot.services/audio | Transcribe + segment, timestamps as temporal refs |
| WhatsApp | wot.services/chat | Export → participants as identities, messages as thoughts |
| Twitter/X | wot.services/social | Archive → tweets as thoughts, threads as chains |
| Slack | wot.services/slack | Export → channels as pools, threads as chains |
| Browser | wot.services/browse | History + optional content capture |
| Bookmarks | wot.services/links | Raindrop/Pinboard → tagged thoughts |
| Notes | wot.services/notes | Obsidian/Notion export → thoughts with backlinks |

### How It Works

```
1. Connect source (OAuth, export upload, SMTP forward)
2. Service parses → creates thoughts with:
   - source attribution (wot.services/email)
   - external identity mapping (sender@domain → identity thought)
   - because chains (reply-to → parent message CID)
   - timestamps preserved
3. Push to your pool (you control destination)
4. Your daemon indexes + applies waterline
```

### Trust Model

Ingested content starts **unattested**:
- Created by service identity (wot.services/email)
- Source attribution in metadata
- Trust = 0 until you attest
- Subconscious can surface, conscious must verify

**Human-in-loop pattern:**
```
Service ingests email → thought created (trust: 0)
You read it → attest (+1.0) or ignore
Attested thoughts surface above waterline
Unattested decay / stay below
```

### Business Model

| Tier | Throughput | Features |
|------|------------|----------|
| Free | 100 thoughts/day | Basic sources, public pool |
| Pro | 10k thoughts/day | All sources, private pools, priority |
| Self-host | Unlimited | Open source, run your own |

**Revenue from convenience, not lock-in.** Data is yours, portable, standard format. Pay for not running infrastructure.

### Self-Host Package

```bash
docker run wot-technology/ingest \
  --source smtp \
  --forward-to your-daemon:50051 \
  --identity /path/to/service-identity.json
```

Each ingester is a standalone container. Compose what you need.

### Why This Matters

**Cold start problem:** New WoT user has empty graph. No thoughts = nothing to search, nothing to attest, no value.

**Solution:** Ingest your existing digital exhaust. Email archive, bookmarks, notes, chat history → instant corpus. Now you have something to work with.

**The pitch:** "Bring your history. We'll make it searchable, connected, and yours."


---

## Mirror Trading via Trust (2026-01-31)

**The idea:** Trusted partners publish trades as thoughts. Your bot follows based on trust score.

### How It Works

```
TRADER IDENTITY (you trust them)
    │
    ├── TRADE THOUGHT
    │     type: trade
    │     content:
    │       action: buy | sell
    │       asset: AAPL
    │       size: 0.5%  (percentage, not absolute)
    │       price: market | limit
    │       rationale: "Earnings beat, guidance raised"
    │     because: [analysis_cid, data_source_cid]
    │     visibility: pool:trading-circle
    │
YOUR DAEMON
    ├── subscribed to pool:trading-circle
    ├── receives trade thought
    ├── computes trust(you → trader)
    │
    ├── IF trust > your_threshold:
    │     apply YOUR rules:
    │       - max_position: 2%
    │       - allowed_assets: [stocks, not_crypto]
    │       - size_scaling: trust × their_size
    │       - require_rationale: true
    │     
    │     THEN execute (or queue for approval)
    │
    └── Creates MIRROR THOUGHT
          type: trade_mirror
          content: { mirrored: trade_cid, scaled_size: 0.4%, executed_at: ... }
          because: [trade_cid, your_rules_cid]
```

### Trust-Scaled Position Sizing

```
Trader recommends: 1% position
Your trust in them: 0.7
Your max position: 2%

Execution size: min(1% × 0.7, 2%) = 0.7%
```

Higher trust = larger mirror. New trader you're testing = tiny positions until track record builds.

### Why This Beats Existing Copy-Trading

| eToro / Traditional | WoT Mirror Trading |
|--------------------|--------------------|
| Platform picks "top traders" | You pick who you trust |
| Opaque track record | Attestations on past trades (CIDs) |
| No rationale visible | Because chain shows analysis |
| Binary follow/unfollow | Gradual trust scaling |
| Platform custody | Your keys, your broker |
| Platform takes cut | Direct peer relationship |
| "Trust the platform" | Trust your graph |

### Accountability Chain

Every trade has receipts:
```
TRADE → because → ANALYSIS → because → DATA_SOURCE
  │
  └── OUTCOME attestation (later)
        content: { result: +12%, held: 45d }
        attested_by: [trader, market_oracle]
```

Bad calls accumulate negative attestations. Trust decays. Position sizing auto-adjusts.

### Pool Structures

| Pool | Purpose |
|------|---------|
| `trading-signals-public` | Anyone can publish, low default trust |
| `trading-circle-private` | Invite-only, vetted traders |
| `your-mirror-executions` | Your bot's actions, private |

### Compliance Angle

Every mirror trade has:
- Source trader identity
- Rationale chain
- Your rule application
- Execution timestamp
- Full audit trail

"Why did you buy AAPL?" → walk the because chain → receipts all the way down.

### Risk Controls (Your Rules)

```yaml
mirror_rules:
  trust_threshold: 0.7
  max_per_trade: 2%
  max_per_trader: 5%
  allowed_assets: [stocks, etfs]
  blocked_assets: [crypto, options]
  require_rationale: true
  delay_execution: 5m  # time to review
  auto_execute: false  # require tap to confirm
```

All expressed as aspect thoughts. Auditable, changeable, versioned.


### Automatic Trust Adjustment Loop

The key insight: **outcomes are attestations**.

```
1. SIGNAL ARRIVES
   Trader publishes trade thought
   because: [analysis, data]

2. YOU MIRROR
   Mirror thought created
   because: [signal, your_rules]
   size: trust × their_size

3. TIME PASSES

4. OUTCOME RECORDED
   Outcome attestation on signal
   content: { pnl: +8%, held: 14d }
   attested_by: [market_oracle, your_daemon]

5. TRUST ADJUSTS
   Positive outcome → trust += f(magnitude)
   Negative outcome → trust -= f(magnitude)
   
6. NEXT SIGNAL SIZED DIFFERENTLY
   Higher trust → larger position
   Lower trust → smaller position
   Below threshold → ignored
```

No manual intervention. The graph learns.

### A/B Testing Signal Sources

When you have multiple potential signal sources, run them in parallel:

```yaml
test_config:
  sources:
    trader_a:
      current_trust: 0.8
      allocation: 40%
      track_record: "+12% YTD"
    trader_b:
      current_trust: 0.6
      allocation: 30%
      track_record: "+5% YTD"
    bot_c:
      current_trust: 0.4
      allocation: 20%
      track_record: "-2% YTD"
    rss_algo:
      current_trust: 0.3
      allocation: 10%
      status: "testing"

  rules:
    promotion_threshold: 0.7   # promote when sustained above
    demotion_threshold: 0.3    # demote when drops below
    evaluation_window: 30d     # rolling performance
    rebalance_frequency: weekly
```

**All as thoughts:**
- Test config = aspect thought
- Each source = identity thought
- Allocation rules = connection thoughts (you → allocates_to → source)
- Performance = attestation chain
- Promotions/demotions = new attestations on allocation connections

### Validation Chain

Everything verifiable:

```
"Did trader A's signals work?"
  → walk outcome attestations on their trade thoughts
  → compute aggregate performance
  → compare to your mirror executions
  → verify you got same fills (slippage check)

"Why did my trust in B drop?"
  → walk trust adjustment attestations
  → each links to outcome thought
  → each outcome links to original signal
  → full receipts
```

**Disputes have evidence:**
- "I said buy at $100" → signed thought with timestamp
- "You executed at $102" → mirror thought with execution data
- "Market was at $100.50 when I sent" → oracle attestation

No he-said-she-said. Receipts or it didn't happen.

### The Meta-Game

Once you have trust-weighted signal following working:

1. **Sell your signals** — publish to pool, others mirror you
2. **Aggregate signals** — combine multiple sources, weight by trust
3. **Signal of signals** — meta-traders who curate other traders
4. **Reputation portability** — your track record is a thought chain, take it anywhere

The protocol enables a trust-native signal marketplace. No platform takes a cut. Performance is verifiable. Reputation is portable.


---

## Commercialization: Trust-Weighted Signal Marketplace (2026-01-31)

**The big picture:** WoT enables a new category — trust-native signal marketplaces. Not just trading. Any domain where you follow expert signals.

### The Pattern (Generalized)

```
SIGNAL PRODUCER (trusted identity)
    │
    ├── publishes SIGNAL thought
    │     type: signal
    │     content: { action, target, rationale }
    │     because: [analysis_chain]
    │     signature: ed25519
    │
SIGNAL CONSUMER (you)
    ├── subscribed to producer's pool
    ├── computes trust(you → producer)
    ├── applies YOUR rules
    ├── executes (scaled by trust)
    │
    └── OUTCOME recorded
          ├── attestation on signal
          ├── trust auto-adjusts
          └── future signals sized accordingly
```

### Domains Beyond Trading

| Domain | Signal Type | Outcome Measure |
|--------|-------------|-----------------|
| **Investing** | Trade calls | P&L |
| **Hiring** | Candidate referrals | Retention, performance |
| **Purchasing** | Product recommendations | Satisfaction, returns |
| **Security** | Threat intel | False positive rate |
| **Research** | Paper recommendations | Citation, replication |
| **Health** | Treatment suggestions | Patient outcomes |
| **Legal** | Case strategy | Win rate |

Same pattern: trusted source → signed signal → your rules → outcome → trust adjustment.

### Why This Is Big

**Current state:** Platforms own the signal marketplace. They pick "top" performers. They take a cut. Your data stays with them.

**WoT state:**
- You pick who to trust (your graph)
- Signals are signed and grounded (because chains)
- Outcomes are attestations (verifiable)
- Trust adjusts automatically (learning system)
- No platform cut (direct peer relationship)
- Portable reputation (take your track record anywhere)

### Revenue Models

| Model | Description |
|-------|-------------|
| **Signal subscription** | Pay to access a producer's pool |
| **Performance fee** | Producer takes % of positive outcomes |
| **Aggregation** | Curate and weight multiple sources, charge for the blend |
| **Infrastructure** | Host the pools, take a thin margin |
| **Validation oracles** | Provide outcome attestations (trusted third party) |
| **A/B testing tools** | Help consumers test signal sources |

### The Flywheel

```
Good signals → followers mirror → outcomes recorded
      ↓                               ↓
  reputation grows ←─── attestations accumulate
      ↓
  more followers → more outcomes → stronger signal
```

Reputation compounds. Early good track record = long-term advantage. But bad signals = trust decays = smaller positions = less influence.

### Competitive Moat

| Incumbent Advantage | WoT Advantage |
|--------------------|---------------|
| Network effects (users locked in) | Portable reputation (take it anywhere) |
| Platform trust | Cryptographic verification |
| Opaque algorithms | Transparent because chains |
| Platform picks winners | You pick who to trust |
| Data stays with platform | Your data, your graph |

### Implementation Path

1. **Trading signals MVP** — most obvious, measurable outcomes
2. **Generalize to other domains** — same protocol, different signal types
3. **Aggregation layer** — meta-curators who blend sources
4. **Oracle network** — trusted outcome attesters
5. **Marketplace UI** — discover signal producers, see track records

### Key Insight

**The protocol IS the product.** Everything else is services built on top:
- Ingestion (wot.services)
- Signal pools (producer-run or aggregated)
- Validation oracles (outcome attestation)
- Discovery (find good signal sources)
- Execution (broker integration)

Each layer can be a business. Each layer is optional. The protocol ties it together.


---

## Disruption Map: High-Signal, Hard-to-Verify Domains (2026-01-31)

**Criteria:** Expert signals matter, verification is hard, trust is critical, outcomes measurable.

### Civil Society

| Domain | Current Problem | WoT Angle |
|--------|-----------------|-----------|
| **Journalism** | "Trust us, we checked" | Because chains to sources. Corrections are attestations. Track record visible. |
| **Medical second opinions** | Pay $500, get opinion, no track record | Doctor's diagnostic accuracy as attestation history. Outcomes recorded. |
| **Legal referrals** | Lawyer recommendations opaque | Win rates, case outcomes, specialty attestations. Trust-weighted referral network. |
| **Academic peer review** | Anonymous, slow, no accountability | Reviewers sign reviews. Review quality attested by outcomes (replication, citations). |
| **Contractor recommendations** | Yelp gaming, fake reviews | Project completion attestations. Multi-party sign-off (client + contractor). |
| **Real estate appraisals** | Appraiser conflicts of interest | Appraisal accuracy vs sale price. Track record computable. |
| **Expert witnesses** | Hired guns, no accountability | Testimony accuracy across cases. Cross-examination as negative attestation. |
| **Product certifications** | "Organic", "Fair Trade" — trust the label | Certification as attestation. Auditor track record. Supply chain because chains. |
| **Insurance claims** | Fraud hard to detect | Claimant history. Adjuster accuracy. Multi-party attestation on incidents. |
| **Credit ratings** | Opaque models, conflicts | Rating accuracy over time. Rater reputation from outcomes. |

### Security / Intelligence

| Domain | Current Problem | WoT Angle |
|--------|-----------------|-----------|
| **Threat intel sharing** | "Trust us" between agencies | Source grading with because chains. Accuracy attestations from outcomes. |
| **Cyber attribution** | "We assess with high confidence" | Evidence chains. Multi-source corroboration as attestations. Track record on past attributions. |
| **Informant handling** | Source reliability opaque | Source track record (correct tips vs bad leads). Handler vouches, outcomes validate. |
| **Chain of custody** | Evidence tampering risk | Every handoff is attestation. Cryptographic proof of possession. |
| **OSINT verification** | "We found this online" | Source provenance. Cross-reference attestations. Analyst track record. |
| **Weapons provenance** | Illegal arms flows | Every transfer attested. Serial numbers as identities. Gaps in chain = red flag. |
| **Secure comms authentication** | "Is this really the General?" | Identity from key, not metadata. Because chain to authorization. |

### Government / Civic

| Domain | Current Problem | WoT Angle |
|--------|-----------------|-----------|
| **Voting / elections** | "Trust the machines" | Vote as attestation. Cryptographic verification. Audit trail. |
| **Public records** | Forgery, tampering | Records as thoughts. Amendments as because chains. Official attestations. |
| **Regulatory compliance** | "We inspected, trust us" | Inspector track record. Multi-party attestation. Outcome correlation. |
| **License verification** | Fake credentials | License as attestation by authority. Revocations as negative attestations. |
| **Asylum claims** | Document fraud | Identity attestation chains. Corroborating witness attestations. |
| **Whistleblower protection** | Retaliation, credibility attacks | Anonymous identity with attestation history. Report accuracy track record. |

### Most Compelling Near-Term

| Domain | Why Now | Entry Point |
|--------|---------|-------------|
| **Trading signals** | Clear outcomes, existing market, measurable | Mirror trading MVP |
| **Threat intel** | Agencies already share, trust is the bottleneck | Pilot with allied sharing |
| **Medical second opinions** | Expensive, outcomes trackable, high stakes | Platform for oncology consults |
| **Contractor recommendations** | Yelp is broken, outcomes clear | Home services vertical |
| **OSINT verification** | Bellingcat-style, replication crisis | Analyst collective with track records |
| **Journalism provenance** | Deepfakes, trust collapse | Newsroom attestation network |

### The Pattern

All of these share:
1. **Expert signals** — someone knows something you don't
2. **Verification gap** — hard to know if they're right until later
3. **Reputation opacity** — track records hidden or non-existent
4. **Outcome delay** — truth emerges over time
5. **Trust by proxy** — "trust the institution" failing

WoT fixes: **make track records computable, make provenance visible, make trust adjustable from outcomes.**


---

## UK Property Chain Coordination (2026-01-31)

**The problem:** Property chains break because of poor information flow between parties.

### Current State

```
CHAIN: 4 linked transactions
────────────────────────────────────────────────────
Party A (selling) → Party B (buying A, selling) → Party C (buying B, selling) → Party D (buying C)
     ↑                      ↑                            ↑                           ↑
  solicitor              solicitor                   solicitor                   solicitor
  estate agent           estate agent                estate agent                mortgage lender
  mortgage               surveyor                    surveyor                    surveyor
```

**Failure modes:**
- One party's mortgage delayed → entire chain waits
- Survey reveals issue → renegotiation ripples
- Solicitor slow to respond → nobody knows status
- "Gazumping" — seller accepts higher offer mid-chain
- "Gazundering" — buyer lowers offer at last minute
- No visibility of chain health until it collapses

**Current information flow:**
```
Buyer → Estate Agent → Seller's Solicitor → Seller
              ↓
        "I'll chase them"
              ↓
        (3 days pass)
              ↓
        "Still waiting on searches"
```

Nobody sees the full picture. Everyone's playing telephone.

### WoT Solution

**Every party is an identity. Every step is an attested thought.**

```
PROPERTY CHAIN POOL (visibility: chain participants)
│
├── TRANSACTION THOUGHT: "A selling to B"
│     parties: [A, B, A_solicitor, B_solicitor, estate_agent]
│     property: <address_cid>
│     agreed_price: £X
│     status: in_progress
│
├── MILESTONE THOUGHTS (attested by responsible party):
│     ├── "Offer accepted" — attested by seller + agent
│     ├── "Mortgage approved" — attested by lender
│     ├── "Survey complete" — attested by surveyor
│     ├── "Searches returned" — attested by solicitor
│     ├── "Enquiries answered" — attested by seller's solicitor
│     ├── "Exchange ready" — attested by both solicitors
│     └── "Completion" — attested by all parties
│
└── CHAIN HEALTH (computed):
      ├── Weakest link: Party C (survey pending 14 days)
      ├── Projected completion: 6 weeks
      └── Risk: Medium (one mortgage in underwriting)
```

### Why This Works

| Current | WoT Chain |
|---------|-----------|
| Call solicitor, wait for callback | Real-time status visible to all |
| "They said it's progressing" | Signed attestation or it didn't happen |
| No visibility of other chain links | Full chain health visible |
| Gazumping surprises everyone | Counter-offers are visible thoughts |
| Blame game when it collapses | Audit trail shows where it broke |

### Accountability Pattern

```
Solicitor says "searches submitted"
  → Creates thought: "Searches submitted to [council]"
  → Attests with their identity
  → Timestamp recorded
  → If searches arrive late, track record updated

Chain collapses:
  → Walk the because chain
  → Find: Party C's mortgage denied on day 45
  → Everyone can see where it broke
  → Reputation implications for parties who caused delay
```

### Trust in the Chain

**Before chain forms:**
- Check party track records (completed chains, dropped chains)
- Surveyor reputation (accurate estimates, missed issues)
- Solicitor responsiveness (average time to milestone)
- Mortgage lender reliability (approval rate, timeline accuracy)

**During chain:**
- Real-time status updates (attested, not just claimed)
- Early warning on delays (milestone overdue → alert)
- Renegotiation visible (price change thoughts require multi-party attestation)

### Gazumping Prevention

```
OFFER THOUGHT: "B offers £X for property"
  attested_by: [buyer, seller, agent]
  
LOCK THOUGHT: "Offer locked for exchange"
  type: constraint
  content: { no_higher_offers_until: exchange_or_withdrawal }
  attested_by: [seller]
  because: [offer_thought]
  
VIOLATION: Seller accepts higher offer
  → Breach of attested constraint
  → Visible in their reputation
  → Future buyers can see history
```

Not legal enforcement — reputation enforcement. Sellers who gazump get known for it.

### Business Angle

| Service | Description |
|---------|-------------|
| **Chain Pool SaaS** | Hosted pool for each property chain, per-transaction fee |
| **Integration** | API for solicitor case management systems |
| **Alerts** | Push notifications on status changes |
| **Analytics** | Chain health predictions, delay risk scoring |
| **Reputation** | Track records for agents, solicitors, surveyors |

**Pitch to estate agents:** "Know your chain's health in real-time. Stop chasing solicitors."
**Pitch to solicitors:** "Reduce client calls asking for updates. They can see status themselves."
**Pitch to buyers/sellers:** "Never be surprised by chain collapse. See it coming."


---

## Patient-Controlled Medical Records (2026-01-31)

**The problem:** Medical records are scattered, siloed, and patients don't control sharing.

### Current State

```
GP system ──────────── (no connection) ──────────── Hospital A
    │                                                    │
(fax? letter?)                                     (separate login)
    │                                                    │
Hospital B ──────────── (no connection) ──────────── Specialist
```

You: "Can you send my records to the new doctor?"
Admin: "Fill out this form, we'll fax it in 5-7 business days."

### WoT Solution

**Your medical data is yours. You control sharing via pools.**

```
YOUR MEDICAL POOL (visibility: local_forever)
│
├── RECORDS (thoughts with medical schemas)
│     ├── Lab results (attested by lab)
│     ├── Imaging (attested by radiologist)
│     ├── Prescriptions (attested by prescriber)
│     ├── Diagnoses (attested by diagnosing doctor)
│     └── Notes (your observations)
│
├── PROVIDER ATTESTATIONS
│     ├── "Dr. Smith confirms Type 2 diabetes diagnosis"
│     ├── "Lab confirms HbA1c = 6.2"
│     └── Because chains to original tests
│
└── SHARING POOLS (you create as needed)
      ├── keif-gp-ongoing (long-term, full access)
      ├── keif-ortho-consult (temporary, limited)
      └── keif-emergency (pre-authorized, critical only)
```

### Granular Sharing

```python
# New consultation with orthopedic surgeon
new_pool = create_pool(
    name="keif-ortho-consult-2026",
    visibility="participants_only",
    participants=[my_identity, surgeon_identity],
    expires="90d"
)

# Share only relevant records
share_to_pool(mri_scan, new_pool)         # ✓ relevant
share_to_pool(blood_panel, new_pool)       # ✓ relevant
share_to_pool(mental_health, new_pool)     # ✗ not shared
share_to_pool(dental_records, new_pool)    # ✗ not shared
```

**You define exactly what they see.** Not "all or nothing."

### Trust Chain for Diagnoses

```
DIAGNOSIS: "Torn ACL"
├── attested_by: orthopedic_surgeon
├── because: [mri_cid, physical_exam_cid]
│
├── MRI REPORT
│   ├── attested_by: radiologist
│   ├── because: [mri_images_cid]
│   │
│   └── MRI IMAGES
│       └── attested_by: imaging_center
│
└── PHYSICAL EXAM
    └── attested_by: orthopedic_surgeon
```

Every diagnosis is grounded. Walk the chain to see the evidence.

### Emergency Access Pattern

```
EMERGENCY POOL (pre-authorized)
│
├── Critical info only:
│   ├── Blood type
│   ├── Allergies (drug, food)
│   ├── Current medications
│   ├── Emergency contacts
│   └── Advance directive
│
├── Access rules:
│   ├── Any ER doctor identity (via hospital vouch chain)
│   ├── Paramedic identities (via service vouch chain)
│   └── Auto-expires after 24h per access
│
└── Audit trail:
    └── Every access logged as attestation
```

You're unconscious. ER scans your medical ID (QR/NFC). Gets critical info. Full audit of who accessed what.

### Second Opinion Pattern

```
SECOND OPINION REQUEST
│
├── Create pool: keif-oncology-second-opinion
├── Share: biopsy results, imaging, first diagnosis
├── NOT share: who made first diagnosis (blind review)
│
├── Second doctor reviews
├── Creates opinion thought
├── Attests with their identity
│
└── You compare:
    ├── First opinion: surgery recommended
    ├── Second opinion: watch and wait
    └── Because chains show different reasoning
```

### Provider Track Records

**Over time, attestation history becomes track record:**

```
Dr. Smith (oncologist)
├── Diagnoses made: 847
├── Patient-attested outcomes:
│   ├── Accurate: 812 (96%)
│   ├── Revised: 28 (3%)
│   └── Disputed: 7 (1%)
├── Because chain depth: avg 4.2 (well-grounded)
└── Peer attestations: 34 colleagues vouch
```

Not "trust this doctor because hospital says so." Trust based on verifiable history.

### Consent as Attestation

```
CLINICAL TRIAL CONSENT
│
├── Trial protocol (thought)
├── Risks explained (thought, attested by researcher)
├── Patient consent (attestation by patient)
│   ├── because: [protocol, risks, discussion_notes]
│   └── timestamp: cryptographically signed
│
└── Withdrawal option:
    └── New attestation: weight -1.0 on consent
        └── Automatically propagates to data sharing
```

Consent is a thought. Withdrawal is an attestation. Audit trail complete.

### Why This Matters

| Current | WoT Medical |
|---------|-------------|
| Records scattered across systems | Your pool, your control |
| Share all or nothing | Granular per-consultation sharing |
| No visibility of who accessed | Full audit trail |
| "Trust the hospital" | Trust from attestation chains |
| Paper consent forms | Cryptographic consent attestations |
| Second opinions require re-sending everything | Create pool, share subset |
| Provider reputation opaque | Track records from outcomes |

### Regulatory Alignment

- **GDPR right to portability**: Your data IS portable (it's yours)
- **HIPAA audit requirements**: Every access is an attestation
- **Consent management**: Attestations with because chains
- **Data minimization**: Share only what's needed per pool

### Business Angle

| Service | Description |
|---------|-------------|
| **Patient vault** | Hosted pool for your medical records |
| **Provider integration** | API for EHR systems to publish attestations |
| **Emergency access** | QR/NFC cards with pool access |
| **Second opinion marketplace** | Connect patients with specialists |
| **Clinical trial matching** | Share relevant subset for eligibility |


---

## Data Silo Collapse (2026-01-31)

**The problem:** Your data is scattered across services, shares, clouds. Access depends on network, accounts, permissions. "Where is my stuff?" is a daily question.

### Current State

```
"It's on the share"     → VPN down, can't access
"It's in Dropbox"       → wrong account, need to switch
"It's in Google Drive"  → no internet on this flight
"It's on my laptop"     → laptop is at home
"Email it to myself"    → which thread? which account?
"It's in Slack"         → scrollback limit, can't find
"Ask IT for access"     → 3-day ticket queue
```

**You don't have your data. Services have your data.**

### WoT Solution

**Your pool, your devices, always synced.**

```
YOUR POOL (synced to all your devices)
│
├── Laptop → has local copy
├── Phone → has local copy
├── Tablet → has local copy
└── Home server → has local copy (optional backup)

Network down? → still have local copy
Service offline? → still have local copy
Account locked? → still have local copy (your keys)
Switch providers? → data already with you
```

### The Devices Pool Pattern (Revisited)

```
IDENTITY: Keif
│
└── POOL: keif-devices (private, admin: keif)
    │
    ├── DEVICE: laptop (member, syncs everything)
    ├── DEVICE: phone (member, syncs subset)
    ├── DEVICE: tablet (member, syncs media)
    │
    └── THOUGHTS sync based on:
        ├── visibility rules (what CAN sync)
        ├── device appetite (what device WANTS)
        └── bandwidth/storage (what device CAN HOLD)
```

### Smart Sync, Not Dumb Mirror

```
PHONE (limited storage):
  appetite:
    - recent: last 30 days, full
    - older: summaries only
    - media: thumbnails, fetch on demand
    - secrets: always sync (small)

LAPTOP (full storage):
  appetite:
    - everything: full sync
    - archive: available

HOME SERVER (backup):
  appetite:
    - everything: full sync
    - redundancy: yes
```

**You define what each device holds.** Not "all or nothing."

### Access Without Network

```
On airplane, no wifi:
  - Open WoT app
  - Search your thoughts
  - Full local index
  - Read, write, attest
  - Syncs when back online
```

Your data travels with you. Network is for sync, not access.

### No More "Ask IT"

```
CURRENT:
  Need access to project folder
  → Submit ticket
  → Wait for approval
  → IT grants access
  → 3 days later

WOT:
  Colleague shares to pool
  → You're added (bilateral attestation)
  → Instant sync to your devices
  → No IT involved
```

Access is attestation. If they attest you're in, you're in. Auditable, revocable, no ticket queue.

### Migration Path

**Don't rip and replace. Ingest and sync.**

```
1. Keep using Dropbox/Drive/etc.
2. Ingest service → creates thoughts from your files
3. Thoughts sync to your devices
4. Now you have local copy + cloud copy
5. Gradually shift primary to WoT
6. Cloud becomes optional backup
```

You're not locked in. Cloud services become ingest sources, not primary storage.

### Why This Matters

| Current | WoT |
|---------|-----|
| Data in N services | Data in your pool |
| Access needs network | Access is local |
| Access needs right account | Access needs your key |
| Provider outage = no access | Provider outage = no sync (still have data) |
| "Where is it?" | "It's in your pool" |
| IT controls access | You control access (with audit) |
| Switch providers = migration project | Switch providers = just sync |

### One Insight

**The question changes:**

Current: "Where is my data?"
WoT: "What's the sync status?"

Your data is always with you. The only question is whether it's up to date.


---

## USB Stick Portability (2026-01-31)

**The insight:** Your pool on a USB stick. Sneakernet is a first-class transport.

### The Pattern

```
USB STICK (encrypted, your key)
├── identity.json        # your keypair
├── wellspring.db        # your thoughts
├── pools/               # pool configs + shared thoughts
└── wot-portable/        # self-contained app (optional)
```

### Use Cases

**Medical emergency:**
```
1. Arrive at ER
2. Hand over USB (or they scan your NFC card)
3. ER doc's identity added to emergency pool
4. Critical info visible: allergies, medications, blood type
5. Full audit trail on stick
6. Take USB home, sync to devices
```

**Offline collaboration:**
```
1. On airplane, no wifi
2. Colleague has USB with project pool
3. Plug in, bilateral attestation
4. Read their thoughts, add yours
5. Both USBs now have merged state
6. Sync to cloud when back online
```

**Air-gapped systems:**
```
1. Secure facility, no network
2. USB is the only data path
3. Thoughts transferred via stick
4. Signatures verified locally
5. Audit trail preserved
```

**Estate planning:**
```
1. USB in safe deposit box
2. Contains: identity keys, important records
3. Instructions for family
4. They plug in, access via your attestations
5. No cloud account to recover
```

### Why This Matters

| Cloud-Dependent | USB-Portable |
|-----------------|--------------|
| Need internet | Work anywhere |
| Need account | Need your key |
| Service outage = no access | Always accessible |
| Provider shutdown = data loss | Your copy, forever |
| "What's your login?" | Plug and verify |

### Transport Agnostic (Spec Alignment)

From v0.7: "Same identity, same trails, different transport."

```
TRANSPORTS:
├── Internet (HTTPS, gRPC)
├── LAN (mDNS discovery)
├── USB (sneakernet)
├── QR code (small thoughts)
├── NFC (identity + pointers)
├── Bluetooth (device-to-device)
└── Paper (QR printout for recovery)
```

The protocol doesn't care how bytes move. CIDs verify. Signatures prove. Transport is just plumbing.

### Portable App Bundle

```
wot-portable/
├── wot.exe (or .app, or AppImage)
├── config.json (points to ../wellspring.db)
└── README.txt

Run from USB. No install. Read/write your pool.
Sync when connected to your other devices.
```

### Security Considerations

**USB encryption:**
- Full disk encryption (LUKS, BitLocker, FileVault)
- Or: app-level encryption (db encrypted at rest)
- Unlock with password or hardware key

**Lost USB:**
- Encrypted = data safe
- Revoke USB device identity from another device
- Compromise window created for thoughts since last sync
- New USB, restore from other device

**"But USB is a security risk":**
- Only if you run untrusted code
- WoT portable can be read-only verified
- Or: use USB for data only, run app from trusted device


---

## Key Recovery via Social Attestation (2026-01-31)

**The problem:** User loses their private key. No central authority to reset it.

**The solution:** Existing trusted entities attest that the new key is the same person. Social recovery, not password reset.

### The Pattern

```
SCENARIO: Keif loses laptop, phone destroyed, keys gone

OLD IDENTITY: keif_v1 (pubkey: ed25519:abc...)
  └── member of pools: [family, work, trading-circle]
  └── vouched by: [alice, bob, carol, dave, eve]

NEW IDENTITY: keif_v2 (pubkey: ed25519:xyz...)
  └── generated on new device
  └── no reputation yet

RECOVERY:
  1. Keif contacts pool members out-of-band
     "Hey, I lost my keys, this is my new identity"
  
  2. Each trusted member creates attestation:
     THOUGHT: same_as attestation
       type: attestation
       content:
         assertion: "same_as"
         old_identity: keif_v1_cid
         new_identity: keif_v2_cid
         verification: "Video call, asked about shared memories"
       created_by: alice
       because: [keif_v1_cid, keif_v2_cid]
  
  3. Threshold reached (e.g., 3 of 5 vouchers)
  
  4. New identity inherits:
     - Pool memberships (via fresh bilateral attestation)
     - Reputation (linked via same_as chain)
     - Trust score (computed from attestation network)
```

### Why This Works

| Password Reset | Social Recovery |
|----------------|-----------------|
| Central authority controls | Your network controls |
| "Prove you're you" to stranger | Prove to people who know you |
| Security questions (weak) | Personal verification (strong) |
| Single point of failure | Distributed threshold |
| Account locked = locked out | Key lost = ask your people |

### Threshold Configurations

```yaml
recovery_policy:
  # How many same_as attestations needed?
  threshold: 3
  
  # Who can attest?
  eligible_attesters:
    - vouchers (people who vouched for you)
    - pool_admins (admins of pools you're in)
    - family_pool_members (if you designated)
  
  # Minimum trust level to count?
  min_attester_trust: 0.7
  
  # Time window (prevent rushed social engineering)
  attestation_window: 7d
  
  # Cooling off (new key limited until window closes)
  cooling_period: 48h
```

### Reputation Inheritance

```
OLD IDENTITY (keif_v1)
├── 2,847 thoughts
├── 156 attestations received
├── trust score: 0.89
├── vouch chain depth: 4

same_as ATTESTATIONS (threshold met)
├── alice: "Verified via video call"
├── bob: "Verified shared secret"
├── carol: "Verified in person"

NEW IDENTITY (keif_v2)
├── 0 new thoughts (fresh start on content)
├── reputation: LINKED to keif_v1
├── trust score: 0.89 × continuity_factor
└── can reference keif_v1's because chains
```

**Key insight:** Content stays with old identity (immutable, already signed). Reputation transfers via attestation chain. New thoughts signed with new key.

### Security Considerations

**Attack: Social engineering the recovery**
- Attacker convinces 3 friends "I lost my key"
- Friends attest without proper verification

**Mitigations:**
- Verification requirements in attestation (how did you verify?)
- Cooling period before full access
- Notification to old identity's contact methods (if available)
- Higher threshold for high-value pools
- Time-locked recovery (wait 7 days, old key can cancel)

**Attack: Colluding attesters**
- 3 friends conspire to steal identity

**Mitigations:**
- Their attestation history now linked to fraudulent same_as
- If discovered, their reputation destroyed
- Skin in the game: attesting falsely has consequences

### Pre-Designated Recovery

```
THOUGHT: recovery_delegates
  type: aspect
  aspect_type: constraint
  content:
    delegates: [alice_cid, bob_cid, carol_cid, dave_cid, eve_cid]
    threshold: 3
    verification_requirements: ["video_call", "shared_secret"]
  created_by: keif
  visibility: local_forever (or trusted backup)
```

Set up before you lose keys. Designate who can recover you. Store in safe place (USB, trusted device, paper backup of delegate list).

### The Ceremony

```
RECOVERY CEREMONY:

1. ANNOUNCEMENT
   New identity publishes: "Claiming same_as keif_v1"
   Posted to recovery pool or public
   
2. CHALLENGE PERIOD (48h)
   Anyone can object: "I talked to keif, this isn't them"
   Old key (if not lost) can reject: "This is not me"

3. VERIFICATION
   Each delegate verifies via agreed method
   Creates attestation with verification details
   
4. THRESHOLD
   When N delegates attest:
   - New identity gains pool access
   - Reputation links established
   - Old identity marked: "superseded_by: new_cid"

5. COOLING
   Limited capability for 7d
   High-stakes actions require extra confirmation
   
6. ACTIVE
   Full capability restored
   Old identity read-only (verify old sigs, can't create new)
```

### Edge Cases

**What if old key found later?**
- Create attestation: "Found old key, confirming same_as"
- Both keys now valid (multi-key identity)
- Or: revoke old key explicitly

**What if threshold can't be reached?**
- Partial recovery (limited pools)
- Start fresh, rebuild reputation
- This is the cost of decentralization

**What about content signed with old key?**
- Still verifiable (pubkey still known)
- Because chains still valid
- New thoughts reference old via same_as chain


---

## Revocation Propagation: Poison the Root (2026-01-31)

**The problem:** Colluding attesters create fraudulent `same_as`, then build a whole chain of content before you notice. You don't want to individually counter-attest 100 thoughts.

**The solution:** Revoke the root attestations. Everything downstream becomes automatically invalid.

### The Attack

```
1. Bob and Sue collude
2. They attest same_as for fake_keif_key
3. Threshold met (2 of 3, you're the third)
4. fake_keif creates 100 thoughts over 2 weeks
5. Other people attest those thoughts (they look legit)
6. Real Keif finally notices
```

### The Defense: Root Revocation

```
REVOCATION THOUGHT
  type: revocation
  content:
    targets: [bob_same_as_cid, sue_same_as_cid]
    effect: "invalid_chain"    # everything depending on these
    reason: "Fraudulent same_as - I never lost my key"
    evidence: [proof_of_key_possession, timeline, etc.]
  created_by: keif_real (OLD key - still valid for signing)
  because: [bob_same_as_cid, sue_same_as_cid]
```

### Chain Invalidation Logic

```python
def is_valid(thought_cid, context):
    """Check if thought is valid, considering revocations."""
    
    # Walk the trust chain for this thought
    chain = walk_trust_chain(thought_cid)
    
    # Check for revocations at any point in chain
    for link in chain:
        revocations = find_revocations(link.cid)
        for rev in revocations:
            # Is revocation from someone who COULD revoke this?
            if can_revoke(rev.created_by, link):
                # Is it an invalid_chain revocation?
                if rev.content.effect == "invalid_chain":
                    return False, f"Chain invalidated at {link.cid}"
    
    return True, "Valid"
```

### Who Can Revoke What?

| Revocation Target | Who Can Revoke |
|-------------------|----------------|
| Your own `same_as` attestation | You (the attester) |
| Someone else's `same_as` about YOU | You (the identity being claimed) |
| Pool membership | Pool admin |
| Any thought | Its creator |

**Key insight:** The REAL Keif can revoke `same_as` claims about themselves, even if they didn't create the attestation. It's a claim about YOUR identity — you have authority to reject it.

### Propagation Semantics

```
REVOCATION with effect: "invalid_chain"
    │
    └── Invalidates:
        ├── The targeted attestations
        ├── The fake identity they enabled
        ├── All thoughts created by that fake identity
        ├── All attestations ON those thoughts
        └── All because chains THROUGH those thoughts

BUT:
    ├── Thoughts that REFERENCE the fake (not depend on) → flagged, not invalid
    └── Independent attestations by real people → still valid, but flagged
```

### Client Behavior

```
When displaying thought:
  1. Check: is this thought in an invalidated chain?
  2. If yes: show "[INVALIDATED]" or hide entirely
  3. Show: "This thought was invalidated by [revocation_cid]"
  4. Link to revocation for context

When computing trust:
  1. Invalidated chains contribute 0 trust
  2. Attesters of invalidated thoughts: judgement penalty
  3. Innocent attesters (didn't know): minor penalty, can appeal
```

### The Timeline Defense

Real Keif can prove they had the old key all along:

```
PROOF THOUGHT
  type: proof_of_possession
  content:
    key: old_pubkey
    challenge: <random nonce>
    signature: sign(nonce, old_privkey)
    timestamp: now
    message: "I still have this key. I never lost it."
  created_by: keif_real
  
TIMELINE THOUGHT
  type: evidence
  content:
    during_fraud_period:
      - thought_cid_1: "I created this while 'I' supposedly lost my key"
      - thought_cid_2: "And this"
      - thought_cid_3: "And this"
    conclusion: "I was actively using my key. The same_as was fraudulent."
```

### Notification Pattern

```
REAL KEIF'S DEVICES:
  - Monitor for same_as claims about your identity
  - Alert: "Someone claimed same_as for your identity"
  - Even if you didn't initiate recovery
  - Challenge period before it takes effect

POOL RULES:
  recovery_monitoring:
    notify_on_same_as: true
    challenge_period: 7d
    require_old_key_confirm: true  # if old key still active, must sign off
```

### Summary

| Problem | Solution |
|---------|----------|
| 100 fraudulent thoughts | Revoke 2 same_as attestations at root |
| Chain of bad attestations | invalid_chain effect propagates |
| "He said she said" | Proof of key possession + timeline |
| Delayed discovery | Challenge period + monitoring |
| Innocent attesters | Flagged not punished (can appeal) |

**The principle:** You don't fight fires leaf by leaf. You cut off the oxygen at the source.


---

## Daemon Auto-Defense (2026-01-31)

**The insight:** If you still have your key, fraudulent `same_as` claims can be automatically rejected. No human intervention needed.

### The Logic

```python
def on_same_as_received(same_as_thought):
    """Auto-reject fraudulent same_as claims about my identity."""
    
    # Is this about me?
    claimed_old = same_as_thought.content.old_identity
    if claimed_old != my_identity.cid:
        return  # Not my identity, not my problem
    
    # Did I initiate this recovery?
    if same_as_thought.content.new_identity in my_pending_recoveries:
        return  # I started this, it's legit
    
    # Do I still have my key?
    if can_sign_with(my_identity):
        # I HAVE MY KEY. This is fraud.
        auto_reject(same_as_thought)

def auto_reject(fraudulent_claim):
    """Create immediate revocation with proof of key possession."""
    
    # Generate fresh proof
    nonce = random_bytes(32)
    proof = sign(nonce, my_private_key)
    
    rejection = Thought(
        type="revocation",
        content={
            "targets": [fraudulent_claim.cid],
            "effect": "invalid_chain",
            "reason": "AUTO-REJECT: Key holder still possesses key",
            "proof_of_possession": {
                "nonce": nonce.hex(),
                "signature": proof.hex(),
                "timestamp": now()
            }
        },
        created_by=my_identity,
        because=[fraudulent_claim.cid]
    )
    
    store(rejection)
    broadcast_urgent(rejection)  # High priority push
    alert_user("Fraudulent same_as claim auto-rejected")
```

### Why This Works

| Scenario | Daemon Action |
|----------|---------------|
| Real recovery (you lost key) | No key to sign with, can't auto-reject |
| Fraud (you have key) | Sign rejection instantly, broadcast |
| Race condition (attacker first) | Your proof of possession wins (you can sign) |

### Proof of Possession

The rejection includes cryptographic proof:

```
"I signed this nonce with the key you claim I lost."
"The signature verifies against my pubkey."
"Therefore I still have the key."
"Therefore the same_as claim is false."
```

Undeniable. The math doesn't lie.

### Broadcast Strategy

```
URGENCY LEVELS:

Normal sync:     batch, periodic, bandwidth-friendly
Revocation:      IMMEDIATE, all peers, high priority
same_as claim:   IMMEDIATE broadcast (for detection)
Rejection:       IMMEDIATE broadcast (to stomp fraud)
```

Revocations and rejections jump the queue. Everyone needs to know NOW.

### Peer Behavior on Receipt

```python
def on_rejection_received(rejection):
    """Handle incoming rejection of same_as claim."""
    
    # Verify rejection signature
    if not verify_signature(rejection):
        return  # Invalid, ignore
    
    # Is this from the claimed identity?
    target = get_thought(rejection.content.targets[0])
    if rejection.created_by != target.content.old_identity:
        return  # Not their identity to reject
    
    # Verify proof of possession
    if not verify_proof(rejection.content.proof_of_possession):
        return  # Can't prove key ownership
    
    # VALID REJECTION
    mark_as_invalid(target.cid, "invalid_chain")
    propagate(rejection)
    
    # Flag the attesters
    for attester in get_attesters(target):
        add_judgement_note(attester, "Attested fraudulent same_as")
```

### Timeline

```
T+0:    Bob and Sue attest fraudulent same_as
T+1:    Thought propagates to network
T+2:    Reaches YOUR daemon
T+3:    Daemon detects: "same_as about me, but I have my key"
T+4:    Auto-generates rejection with proof
T+5:    Rejection broadcast to all peers
T+6:    Network marks same_as as invalid
T+7:    Bob and Sue flagged as fraudsters

Total time: seconds, not days.
```

### What If You're Offline?

```
YOU'RE OFFLINE:
  - Fraudulent same_as propagates
  - Others might see it
  - 7-day challenge period still applies
  
YOU COME BACK ONLINE:
  - Daemon syncs, sees the fraudulent claim
  - Auto-rejects with proof
  - Rejection propagates
  - Any actions during offline period: flagged for review
```

The challenge period protects you even when offline. But the faster you're online, the faster the stomp.

### User Notification

```
ALERT LEVELS:

🔵 INFO:    "New same_as claim about your identity (from your other device)"
⚠️ WARNING: "same_as claim auto-rejected - you still have your key"
🔴 URGENT:  "same_as claim during offline period - review required"
```

Auto-defense handles the easy case. Complex cases still get human review.


---

## Pool Security Model: Attack Surface (2026-01-31)

**Challenge period as pool setting + daemon auto-defense = core security layer.**

### Pool Identity Protection Schema

```yaml
pool_rules:
  identity_protection:
    # Challenge period before same_as takes effect
    challenge_period: 7d
    
    # How many attesters needed for same_as
    same_as_threshold: 3
    
    # Minimum trust level for attesters to count
    min_attester_trust: 0.7
    
    # Require old key confirmation if still active?
    require_old_key_confirm: true
    
    # Auto-reject same_as if old key can sign?
    auto_reject_if_key_present: true
    
    # Notify all pool members of same_as attempts?
    broadcast_same_as_attempts: true
    
    # Cooling period after successful same_as
    post_recovery_cooling: 48h
```

### Daemon Auto-Defense Rules

```python
DAEMON_SECURITY_RULES = {
    # Identity protection
    "on_same_as_about_me": {
        "if_have_key": "auto_reject_with_proof",
        "if_no_key": "alert_user",
        "broadcast": "immediate",
    },
    
    # Revocation propagation
    "on_revocation_received": {
        "verify_authority": True,
        "propagate": "immediate", 
        "mark_descendants": "invalid_chain",
    },
    
    # Pool membership changes
    "on_membership_change": {
        "verify_admin_sig": True,
        "notify_affected": True,
    },
    
    # Anomaly detection
    "velocity_monitoring": {
        "same_as_attempts": "alert_on_any",
        "attestation_flood": "alert_if_>100/hr_from_single_source",
        "new_member_burst": "alert_if_>10/day",
    },
}
```

### Attack Models: Inside the Pool

#### 1. Collusion Without Sync
**Attack:** Members agree offline to lie, don't sync the truth to honest peers.

**Scenario:**
```
Bob and Carol collude
├── Create fraudulent attestations
├── Share only with each other
└── Present false state to outside
```

**Mitigations:**
- Full peer validation: every peer sees all peering thoughts
- Eventual consistency: lies surface when any honest peer syncs
- Fork detection: divergent chain heads = something's wrong
- Cross-peer verification: query multiple peers, compare results

**Residual risk:** Isolated conspiracy that never interacts with honest peers. But then... who cares? They're lying to each other.

---

#### 2. Selective Sync (Pool State Forking)
**Attack:** Share different versions of truth with different peers.

**Scenario:**
```
Mallory syncs with Alice: "Bob said X"
Mallory syncs with Carol: "Bob said Y"
```

**Mitigations:**
- CID verification: if content differs, CID differs
- Peer gossip: Alice and Carol compare what they got
- Signature verification: Mallory can't forge Bob's signature

**Detection:**
```python
def detect_fork(thought_cid, peers):
    versions = [peer.get(thought_cid) for peer in peers]
    if len(set(versions)) > 1:
        raise ForkDetected(thought_cid, versions)
```

---

#### 3. Admin Abuse
**Attack:** Pool admin changes rules maliciously mid-stream.

**Scenario:**
```
Admin lowers same_as_threshold from 3 to 1
Admin's friend now attests alone
Identity stolen
```

**Mitigations:**
- Rule changes are thoughts: visible, auditable
- Rule change attestation: require N admins for rule changes
- Departure rights: members can leave + take their data
- Fork the pool: create new pool with old rules, migrate

**Schema addition:**
```yaml
pool_rules:
  governance:
    rule_change_threshold: 2  # of 3 admins
    rule_change_notice: 7d    # announce before effect
    member_departure: always_allowed
```

---

#### 4. Reputation Laundering
**Attack:** Build reputation in lax pool, use it in strict pool.

**Scenario:**
```
Create pool with no verification
Give myself 1000 positive attestations
Join strict pool with "great reputation"
```

**Mitigations:**
- Trust is computed per pool: your "reputation" in lax pool doesn't transfer
- Vouch chains require path: no path from strict pool members = no trust
- Pool reputation: "attestations from unknown pool" = low weight
- Source matters: where did the attestations come from?

**Trust computation:**
```python
def compute_trust(target, observer, pool):
    # Only count attestations reachable via observer's vouch chain
    reachable = walk_vouch_chain(observer, pool)
    relevant = [a for a in attestations(target) if a.by in reachable]
    return aggregate(relevant)
```

---

#### 5. Attestation Bombing
**Attack:** Flood pool with attestations to overwhelm verification.

**Scenario:**
```
Attacker creates 10,000 attestations/hour
Peers can't keep up with verification
Sneak in fraudulent ones during chaos
```

**Mitigations:**
- Rate limiting: pool rules cap attestations/hour per identity
- Velocity alerts: abnormal patterns trigger review
- Reputation cost: flooding = reputation hit
- Lazy verification: queue, verify async, flag unverified

**Pool rules:**
```yaml
pool_rules:
  rate_limits:
    attestations_per_hour: 100
    thoughts_per_hour: 500
    velocity_alert_multiplier: 5  # alert if 5x normal
```

---

#### 6. Because Chain Poisoning
**Attack:** Reference legitimate thoughts to inherit their trust.

**Scenario:**
```
Fraudulent thought
├── because: [highly_trusted_thought]
└── "I must be trustworthy, look at my sources!"
```

**Mitigations:**
- Reference ≠ endorsement: because means "I saw this", not "this vouches for me"
- Trust flows through attestations, not references
- Check: did the referenced thought's author vouch for this?
- Groundedness ≠ trust: you cited sources, doesn't mean you're right

**Computation:**
```python
def trust(thought, observer):
    # Trust comes from WHO attested, not WHAT was referenced
    attestations = get_attestations(thought.cid)
    return sum(trust(a.by, observer) * a.weight for a in attestations)
    # Note: because chain affects GROUNDEDNESS, not TRUST
```

---

#### 7. Timestamp Manipulation
**Attack:** Backdate thoughts to appear earlier.

**Scenario:**
```
Attacker claims thought was created before deadline
"I submitted this before the vote closed!"
```

**Mitigations:**
- Signature includes timestamp: changing timestamp = invalid signature
- First-seen tracking: peers record when they first received
- Timestamp witnesses: trusted time sources can attest
- Suspicious if: created_at << first_seen by any peer

**Detection:**
```python
def verify_timestamp(thought):
    first_seen = min(peer.first_seen(thought.cid) for peer in peers)
    if thought.created_at < first_seen - CLOCK_SKEW_TOLERANCE:
        flag("Timestamp suspicious: claims {thought.created_at}, first seen {first_seen}")
```

---

#### 8. Quorum Capture
**Attack:** Gain threshold control to dominate pool decisions.

**Scenario:**
```
Pool needs 3 of 5 for same_as
Attacker controls or colludes with 3 members
Attacker can now steal any identity
```

**Mitigations:**
- Higher thresholds for critical actions
- Require diversity: attesters must be from different vouch chains
- Time distribution: attestations must be spread over time
- Challenge period: gives victim time to notice and respond

**Schema:**
```yaml
pool_rules:
  identity_protection:
    same_as_threshold: 3
    same_as_diversity: 2  # from at least 2 different vouch sub-chains
    same_as_time_spread: 24h  # attestations must span at least this long
```

---

#### 9. Aspect Spoofing
**Attack:** Claim aspects you don't have to bypass filters.

**Scenario:**
```
Pool requires "verified_human" aspect
Attacker self-attests "verified_human"
Bypasses bot filter
```

**Mitigations:**
- Aspect attestation authority: who can grant this aspect?
- Require external attestation: self-attestation doesn't count for sensitive aspects
- Aspect issuers: certain aspects only valid if attested by specific identities

**Schema:**
```yaml
pool_rules:
  aspect_requirements:
    verified_human:
      self_attestation: false
      valid_issuers: [identity_verifier_1, identity_verifier_2]
    pool_member:
      self_attestation: true  # bilateral with admin
```

---

### The Ultimate Fallback

**What if everything fails?**

```
1. Leave the pool
2. Take your data (it's yours, signed by you)
3. Create new pool with better rules
4. Invite trusted members
5. Name and shame the bad actors (with receipts)
```

No lock-in. No hostage data. The worst case is: rebuild your network, but keep your history.

### Summary: Defense in Depth

| Layer | Mechanism |
|-------|-----------|
| **Cryptographic** | Signatures verify, CIDs prove content |
| **Daemon** | Auto-reject fraud if key present |
| **Pool rules** | Challenge periods, thresholds, rate limits |
| **Network** | Gossip, cross-verification, fork detection |
| **Social** | Reputation, name-and-shame, departure rights |
| **Fallback** | Fork pool, take data, rebuild |


---

## Proof of Life: Internal Tick (2026-01-31)

**The insight:** Daemons with identity management should continuously create signed "proof of life" thoughts. When fraud is detected, surface the tick as instant proof of key possession.

### The Pattern

```python
# Daemon background task
async def proof_of_life_ticker():
    while running:
        tick = Thought(
            type="heartbeat",
            content={
                "nonce": random_bytes(32).hex(),
                "tick_number": counter,
            },
            created_by=my_identity,
            created_at=now(),
            visibility="local_forever",  # Never syncs normally
        )
        tick.signature = sign(tick, my_key)
        store_local(tick)
        
        counter += 1
        await sleep(TICK_INTERVAL)  # e.g., 1 hour
```

### Storage

```
LOCAL TICK STORE (rolling window)
├── tick_001: signed 2026-01-31 08:00
├── tick_002: signed 2026-01-31 09:00
├── tick_003: signed 2026-01-31 10:00
├── tick_004: signed 2026-01-31 11:00
└── ... (keep last N, e.g., 168 for 7 days hourly)
```

### On Fraud Detection

```python
def on_fraudulent_same_as(claim):
    # When was the fraud claimed?
    fraud_time = claim.created_at
    
    # Find tick closest to (or after) fraud time
    relevant_tick = find_tick_near(fraud_time)
    
    # Publish it as proof
    proof = Thought(
        type="proof_of_life",
        content={
            "claim_rejected": claim.cid,
            "tick_surfaced": relevant_tick.cid,
            "tick_signature": relevant_tick.signature,
            "message": "I was signing at this time. The claim is fraudulent."
        },
        created_by=my_identity,
        because=[claim.cid, relevant_tick.cid],
        visibility=None,  # Publish this one
    )
    
    broadcast_urgent(proof)
```

### Why This Works

| Without Ticks | With Ticks |
|---------------|------------|
| Must sign new proof on demand | Proof already exists |
| Attacker could claim "key stolen 5 min ago" | Tick from 30 min ago proves otherwise |
| Need to be online to respond | Ticks prove continuous possession |
| "Prove you had key at T" = hard | "Here's my tick from T" = easy |

### Tick Properties

```yaml
tick_config:
  interval: 1h          # How often to tick
  retention: 168        # Keep 7 days of ticks
  storage: local_only   # Never sync unless needed
  
  # Include in tick:
  include_nonce: true   # Proves freshness
  include_counter: true # Proves sequence
  include_prev_hash: true  # Chain ticks together
```

### Chained Ticks (Extra Security)

```
tick_005
├── nonce: abc123
├── prev_tick_hash: hash(tick_004)
├── signature: sign(nonce + prev_hash, key)
└── Proves: I had key AND I had access to tick_004
```

If attacker claims you lost key at T, but your tick at T+1 includes hash of tick at T... you clearly had continuous access.

### The Tick as Witness

Beyond fraud defense, ticks prove:
- **Uptime:** "My daemon was running at these times"
- **Key freshness:** "I'm actively using this key"
- **Continuity:** "No gaps in my operation"

Could even be shared with trusted peers as "dead man's switch" — if I stop ticking, something's wrong.

### Configuration in Pool Rules

```yaml
pool_rules:
  identity_protection:
    # Require members to maintain ticks?
    require_proof_of_life: true
    min_tick_frequency: 1h
    
    # Accept proof of life in fraud disputes?
    accept_tick_as_proof: true
    tick_validity_window: 1h  # Tick must be within 1h of disputed event
```

### Daemon Implementation Note

```python
class WotDaemon:
    def __init__(self):
        self.tick_store = RollingTickStore(max_ticks=168)
        self.tick_task = None
    
    async def start(self):
        # Start tick background task
        self.tick_task = asyncio.create_task(self.proof_of_life_ticker())
        # ... rest of daemon startup
    
    def get_proof_for_time(self, timestamp):
        """Get tick closest to timestamp for fraud proof."""
        return self.tick_store.find_nearest(timestamp)
```


---

## Dead Man's Switch via Tick Sharing (2026-01-31)

**The insight:** Share tick hashes with trusted peers. If you stop ticking, they know something's wrong.

### The Pattern

```
YOUR DAEMON                          TRUSTED PEER (watchdog)
─────────────                        ────────────────────────
tick_001 (local)                     
    │
    └─── share hash ──────────────→  expects tick every 1h
                                           │
tick_002 (local)                           │
    │                                      │
    └─── share hash ──────────────→  ✓ received, reset timer
                                           │
tick_003 (local)                           │
    │                                      │
    └─── share hash ──────────────→  ✓ received, reset timer
                                           │
   ...                                     │
                                           │
(you go offline / key compromised)         │
                                           │
                              24h pass...  │
                                           │
                                     ⚠️ NO TICK RECEIVED
                                           │
                                     DEAD MAN'S SWITCH TRIGGERED
```

### What Gets Shared

```python
# You share tick HASH, not full tick
tick_notification = {
    "tick_hash": hash(tick.cid),
    "tick_number": tick.content.tick_number,
    "timestamp": tick.created_at,
    # NOT: the tick itself (stays local until needed)
}
```

Peer knows you're alive. Peer doesn't see tick contents until you choose to reveal.

### Watchdog Behavior

```python
class WatchdogService:
    def __init__(self, watched_identities):
        self.last_tick = {}  # identity -> timestamp
        self.alert_threshold = 24 * 3600  # 24 hours
    
    def on_tick_received(self, identity, tick_hash, timestamp):
        self.last_tick[identity] = timestamp
    
    async def monitor_loop(self):
        while True:
            for identity, last in self.last_tick.items():
                if now() - last > self.alert_threshold:
                    await self.trigger_dead_mans_switch(identity)
            await sleep(3600)  # Check hourly
    
    async def trigger_dead_mans_switch(self, identity):
        # Alert other trustees
        notify_trustees(identity, "No tick received in 24h")
        
        # Check for suspicious activity
        suspicious = check_for_same_as_claims(identity)
        
        # Optionally initiate recovery
        if self.auto_recovery_enabled:
            initiate_recovery_protocol(identity)
```

### Trigger Actions

| Condition | Action |
|-----------|--------|
| No tick + no suspicious activity | Alert trustees: "Check on them" |
| No tick + same_as claim pending | Alert: "Possible theft in progress" |
| No tick + unusual attestations | Alert: "Review recent activity" |
| No tick + pre-configured | Auto-initiate recovery protocol |

### Recovery Protocol Integration

```yaml
dead_mans_switch:
  # Who watches me?
  watchdogs: [alice_identity, bob_identity, family_pool]
  
  # How long before trigger?
  threshold: 24h
  
  # What happens on trigger?
  actions:
    - notify_trustees
    - flag_pending_same_as
    - freeze_high_value_pools  # prevent new attestations
    
  # Auto-recovery?
  auto_recovery:
    enabled: false  # require human intervention
    # OR
    enabled: true
    recovery_pool: family_pool
    recovery_threshold: 2  # of 3 family members
```

### Privacy Considerations

```
WHAT WATCHDOG SEES:
  ✓ Tick hashes (proves you're alive)
  ✓ Timestamps (when you ticked)
  ✗ Tick contents (just hashes)
  ✗ Your other activity
  ✗ Your thoughts

WHAT WATCHDOG CAN DO:
  ✓ Alert other trustees
  ✓ Flag suspicious claims
  ✗ Access your data
  ✗ Create attestations as you
  ✗ Initiate recovery without threshold
```

Watchdog has alarm capability, not access capability.

### Mutual Watching

```
KEIF watches ALICE
ALICE watches KEIF
BOB watches both

If Keif stops ticking:
  - Alice notices (watchdog)
  - Bob notices (watchdog)
  - They coordinate: "Have you heard from Keif?"
  - If neither has: trigger protocol
```

Distributed watchdog network. No single point of failure.

### Use Cases

| Scenario | Dead Man's Switch Helps |
|----------|------------------------|
| Lost all devices | Trustees alerted, recovery starts |
| Incapacitated | Trustees know you're not responding |
| Key theft | Thieves can't suppress the alert |
| Planned absence | Pause the switch ("I'll be offline 2 weeks") |
| Death | Estate trustees can initiate handover |

### Estate Planning Integration

```yaml
estate_config:
  dead_mans_switch:
    threshold: 30d  # Longer for estate purposes
    
  on_trigger:
    - unlock: estate_pool
    - notify: [spouse_identity, lawyer_identity, executor_identity]
    - provide: [will_cid, asset_list_cid, instructions_cid]
    
  recovery_threshold: 2 of 3 trustees
```

You stop ticking for 30 days → estate pool unlocks → designated people can access.

### The Key Insight

**Ticks are positive proof of life. Absence of ticks is negative signal.**

You can't fake continued ticking without the key. If you have the key and you're alive, you'll tick. If you stop ticking, either:
1. You're offline (temporary, will resume)
2. You lost access (recovery needed)
3. You're incapacitated (trustees should check)
4. You're dead (estate protocol)

The switch handles all cases.


---

## Visibility Clarification: Ticks and Secrets (2026-01-31)

**The tension:** `local_forever` means never sync. But ticks need to be shareable (for watchdogs) and surfaceable (for proof). How do we resolve this?

### Visibility Spectrum (Clarified)

```
VISIBILITY:          SYNCS TO:                 USE CASE:
────────────────────────────────────────────────────────────
local_forever        nowhere                   Master secrets, raw drafts
pool:keif-devices    my devices only           Device keys, session state
pool:watchdogs       trusted watchdog peers    Proof of life ticks
pool:family          family members            Shared secrets, estate
pool:work            work colleagues           Work content
null (default)       any peer                  Normal thoughts
```

### Ticks Are NOT `local_forever`

Previous thinking: ticks stored locally until needed.

**Corrected:** Ticks go to a **watchdog pool**. Private but syncable.

```
TICK THOUGHT:
  type: heartbeat
  content: { nonce, counter, prev_hash }
  created_by: keif
  visibility: "pool:keif-watchdogs"  # NOT local_forever
  
→ Syncs to watchdog pool members
→ They can verify I'm alive
→ Can be published later as proof
```

### Co-Signed Ticks (Multi-Party Witness)

```
WATCHDOG POOL: keif-watchdogs
  participants: [keif, alice, bob]

1. KEIF'S DAEMON creates tick
   └── publishes to watchdog pool

2. ALICE'S DAEMON receives tick
   └── creates witness attestation:
       THOUGHT:
         type: tick_witness
         content: 
           tick_cid: <keif's tick>
           received_at: <timestamp>
           my_clock: <alice's local time>
         created_by: alice
         because: [keif_tick_cid]

3. BOB'S DAEMON does the same

RESULT:
  - Keif's tick exists (signed by keif)
  - Alice witnessed it (signed by alice)
  - Bob witnessed it (signed by bob)
  - Three independent signatures on same event
```

### Why Multi-Party Witness Matters

| Single-Party Tick | Multi-Party Witnessed |
|-------------------|----------------------|
| "I say I ticked at T" | "We all saw you tick at T" |
| Could backdate (forge) | Witnesses have their own clocks |
| Must trust ticker | Trust distributed |
| Fraud: forge tick | Fraud: collude with all witnesses |

### The Secret Key Problem

**Old thinking:** Secret keys are `local_forever`, sync via device pool ceremony.

**Problem:** What if you want to:
- Share master secret with spouse (estate planning)
- Share recovery key with trustees
- Have backup in family pool

**Solution:** Visibility is granular, not binary.

```
SECRET THOUGHT:
  type: secret
  content: { privkey: "..." }
  visibility: "pool:keif-family"  # Syncs to family pool
  
# OR for device-only:
  visibility: "pool:keif-devices"  # Only my devices

# OR truly local:
  visibility: "local_forever"  # Never leaves this device
```

**You choose the boundary.** Some secrets sync to family. Some only to devices. Some never leave.

### Pool Hierarchy for Secrets

```
KEIF'S IDENTITY
│
├── SECRET (local_forever) ─── master key, never syncs
│
├── SECRET (pool:keif-devices) ─── syncs to my devices only
│     └── Used for: signing, day-to-day ops
│
├── SECRET (pool:keif-family) ─── syncs to family pool
│     └── Used for: estate planning, emergency recovery
│
└── SECRET (pool:keif-recovery) ─── syncs to designated trustees
      └── Used for: key recovery if all devices lost
```

### Estate Planning Pattern (Refined)

```
ESTATE POOL: keif-estate
  participants: [keif, spouse, executor, lawyer]
  rules:
    access_trigger: dead_mans_switch OR unanimous_trustees
    
CONTENTS:
  - Master secret (visibility: pool:keif-estate)
  - Will reference (visibility: pool:keif-estate)
  - Asset list (visibility: pool:keif-estate)
  - Instructions (visibility: pool:keif-estate)

NORMAL STATE:
  - Only keif can read (encrypted to keif's key)
  - Trustees have pool membership but not decrypt key

ON TRIGGER:
  - Decrypt key released to trustees (threshold unlock)
  - Contents become readable
  - Handover proceeds
```

### Summary: Visibility Is Intentional

| Visibility | Meaning |
|------------|---------|
| `local_forever` | This device only, no exceptions |
| `pool:<specific>` | Syncs within pool members only |
| `null` (default) | Syncs to any peer |

**Ticks:** `pool:watchdogs` (need to share with witnesses)
**Device secrets:** `pool:devices` (need to sync across my devices)  
**Estate secrets:** `pool:estate` (need to share with trustees)
**Raw master key:** `local_forever` (never leaves secure storage)

Choose the boundary that matches the trust requirement.


---

## Vouch Reaffirmation Ceremonies (2026-01-31)

**The insight:** Vouches aren't forever. Periodic reaffirmation keeps the trust graph fresh and verified.

### Why Vouches Decay

| Static Vouches | Dynamic Vouches |
|----------------|-----------------|
| "I vouched in 2020, still valid?" | Freshness tracked |
| Voucher might be dead | Proof of life required |
| Voucher might have changed mind | Reaffirmation ceremony |
| No verification it's still real | Out-of-band challenge |

### Reaffirmation Pattern

```
VOUCH (original)
  alice → vouches → bob (+0.9)
  created_at: 2025-06-01

6 MONTHS LATER...

DAEMON TRIGGERS REAFFIRMATION:
  "Your vouch for bob is 180 days old"
  "Reaffirm to maintain trust weight"

ALICE'S OPTIONS:
  ├── REAFFIRM (+0.9)
  │     New attestation, same weight
  │     Freshness resets
  │
  ├── ADJUST (+0.5)
  │     "Still trust, but less confident now"
  │     Trust score drops
  │
  ├── REVOKE (-1.0)
  │     "No longer vouch for this person"
  │     Vouch chain breaks
  │
  └── SILENCE (no action)
        Vouch ages, weight decays
        Eventually falls below threshold
```

### Out-of-Band Challenge

For high-trust vouches, require verification through another channel:

```
REAFFIRMATION CEREMONY:

1. DAEMON generates challenge
   challenge_code: "7X3K9"
   valid_for: 48h

2. ALICE receives prompt
   "To reaffirm your vouch for Bob:"
   "Share this code via Signal/email/call: 7X3K9"
   "Have Bob confirm he received it"

3. BOB confirms out-of-band
   "Alice gave me code 7X3K9"
   → Bob's daemon creates confirmation thought

4. ALICE's daemon sees confirmation
   → Creates reaffirmation attestation
   → Links because to challenge + confirmation

5. VOUCH REFRESHED
   Freshness reset, trust maintained
   Out-of-band verification recorded
```

### Why Out-of-Band?

| In-band only | Out-of-band required |
|--------------|----------------------|
| Daemons could auto-confirm | Human must actually interact |
| Bots could collude | Requires separate channel |
| No proof of relationship | Proves you can reach them |
| Key compromise = all vouches | Key compromise ≠ Signal access |

**The out-of-band step proves:** Alice and Bob still know each other, can still reach each other, and both choose to maintain the vouch.

### Pool Rules for Reaffirmation

```yaml
pool_rules:
  vouch_freshness:
    # How old before reaffirmation requested?
    reaffirmation_interval: 180d
    
    # How long to wait for response?
    reaffirmation_window: 30d
    
    # Require out-of-band for high-trust vouches?
    require_oob_above_trust: 0.7
    
    # What happens if no reaffirmation?
    on_stale:
      decay_rate: 0.1 per month  # Trust fades
      hard_expiry: 365d          # Below threshold after 1 year stale

  oob_channels:
    accepted: [signal, email, phone, in_person]
    verification: challenge_response
```

### Trust Graph Maintenance

```python
async def vouch_maintenance_loop():
    while running:
        # Find stale vouches
        my_vouches = get_vouches_by(my_identity)
        
        for vouch in my_vouches:
            age = now() - vouch.last_reaffirmed
            
            if age > REAFFIRMATION_INTERVAL:
                # Request reaffirmation
                await request_reaffirmation(vouch)
        
        await sleep(24 * 3600)  # Check daily

async def request_reaffirmation(vouch):
    # Generate challenge if high-trust
    if vouch.weight > 0.7:
        challenge = generate_oob_challenge()
        notify_user(f"Reaffirm vouch for {vouch.target.name}?")
        notify_user(f"Share code {challenge} via alternate channel")
    else:
        # Simple reaffirmation for lower-trust vouches
        notify_user(f"Still vouch for {vouch.target.name}? [Y/adjust/N]")
```

### Ceremony Types

| Ceremony | When | Process |
|----------|------|---------|
| **Simple reaffirm** | Low-trust vouches | Daemon prompts, user confirms |
| **OOB challenge** | High-trust vouches | Share code via alternate channel |
| **In-person verify** | Critical vouches | QR exchange at meeting |
| **Multi-party witness** | Identity vouches | N of M must witness |

### What This Prevents

| Attack | Without Reaffirmation | With Reaffirmation |
|--------|----------------------|-------------------|
| Dead voucher | Still counted | Falls off after stale |
| Compromised voucher | Trust continues | OOB check fails |
| Lapsed relationship | Ancient vouch still valid | Must re-verify |
| Bot networks | Create vouches, done | Must maintain over time |

### The Insight

**Vouching is a relationship, not an event.** Relationships require maintenance. The ceremony forces periodic proof that:
1. Voucher is still alive (proof of life)
2. Voucher still trusts vouchee (reaffirmation)
3. Relationship is real (out-of-band verification)
4. Both parties choose to continue (mutual consent)

Old vouches that aren't reaffirmed fade. The trust graph stays fresh.


---

## Content Trust vs Relationship Trust (2026-01-31)

**Key distinction:** Thoughts are forever valid. Vouches need maintenance.

### Content Trust (Immutable)

```
THOUGHT from 2020:
  ├── signed by bob
  ├── signature verifies against bob's pubkey
  ├── keys were valid at T (creation time)
  └── FOREVER VALID

5 years later:
  ├── bob might be dead
  ├── bob might have revoked key
  ├── bob might be untrustworthy now
  └── BUT: that thought was still valid when created
```

**Principle:** The thought existed. Bob signed it. That's a historical fact. It doesn't un-happen because bob later became untrustworthy.

### Relationship Trust (Requires Maintenance)

```
VOUCH from 2020:
  ├── alice vouches for bob (+0.9)
  ├── alice trusted bob in 2020
  ├── does alice still trust bob in 2025?
  └── NEEDS REAFFIRMATION

Without reaffirmation:
  ├── vouch ages (freshness decays)
  ├── weight gradually reduces
  ├── eventually falls below threshold
  └── new vouches from bob get less weight
```

**Principle:** Relationships change. Vouches represent "I trust this person NOW." If you can't say that anymore, the vouch should fade.

### How They Interact

```
SCENARIO: Alice vouched for Bob in 2020. Bob created thought T1 in 2021.

2020: Alice → vouches → Bob (trust: 0.9)
2021: Bob creates T1 (signed, valid)
2025: Alice hasn't reaffirmed vouch

WHAT HAPPENS:
  T1 (the thought):
    ├── Still valid (signature checks out)
    ├── Bob signed it when he had valid keys
    └── Historical fact, unchanged

  Your trust in T1:
    ├── Computed via vouch chain
    ├── Alice's vouch is stale (5 years, no reaffirm)
    ├── Vouch weight degraded (0.9 → 0.3 from decay)
    ├── Your trust in T1 = lower than 2021
    └── But T1 is still VALID, just less trusted by YOU
```

### Pool Configuration

```yaml
pool_rules:
  trust_computation:
    # Content validity
    verify_signatures: always
    accept_expired_keys: for_historical_content  # Valid at creation

    # Relationship freshness
    vouch_reaffirmation:
      interval: 180d
      decay_rate: 0.1/month
      hard_expiry: 730d  # 2 years stale = below threshold

    # Trust formula
    trust = content_validity × vouch_freshness × attestation_weight
```

### Why This Matters

| If all trust decayed | If relationship trust decays |
|---------------------|------------------------------|
| Old content worthless | Old content still valid |
| History unreliable | History preserved |
| Must re-verify everything | Only re-verify vouches |
| Archive becomes garbage | Archive stays useful |

**The insight:** Content is historical record. Vouches are current relationships. Don't conflate them.

### Practical Implications

**For content:**
- Keep it forever
- Signature proves who created it
- Don't age-out old thoughts
- Provenance is permanent

**For vouches:**
- Require periodic reaffirmation
- Decay stale vouches
- OOB verification for high-trust
- Relationships need maintenance

**For queries:**
- Fresh vouch = high weight
- Stale vouch = lower weight
- Revoked vouch = broken chain
- But the CONTENT behind that chain? Still valid, just less surfaced.


---

## Enterprise Decision Platform Pattern (2026-01-31)

**Source:** Fynite.ai question — scaling agentic decisions across enterprise verticals.

### Their Challenge

Starting with IT CMDB (Configuration Management Database) at major consulting firm:
- Dependency awareness
- Change impact
- Escalation vs auto-action
- Audit and control

Want to expand to: order exceptions, sales support, supply chain, risk/compliance.

**Problem:** "Same controls, same trust model" across verticals — but how to not over-index on one vertical?

### Why This Is a WoT Problem

| Their Need | WoT Primitive |
|------------|---------------|
| Dependency awareness | Because chains |
| Change impact | Attestation propagation |
| Escalation vs auto-action | Trust threshold / waterline |
| Audit and control | The graph IS the audit |
| Same trust model | One protocol, different pool schemas |

### The Horizontal Platform Pattern

```
PROTOCOL LAYER (horizontal):
  ├── Thought (any decision, change, request)
  ├── Attestation (approval, review, sign-off)
  ├── Because chain (why this decision)
  ├── Identity (who made it, what authority)
  └── Pool (organizational container, rules)

VERTICAL SCHEMAS (just content shapes):
  ├── CMDB: { asset, dependency, change_type, impact_radius }
  ├── Orders: { order_id, exception_type, substitution, re_promise }
  ├── Supply: { intervention, routing_decision, inventory }
  └── Risk: { compliance_rule, trace_required, control_level }
```

**Key insight:** They don't need different trust models per vertical. They need one trust model with different content schemas.

### Escalation as Trust Threshold

```python
def should_auto_execute(decision, actor):
    trust = compute_trust(actor, decision.context.pool)
    impact = estimate_impact(decision)
    
    # Low impact + high trust = auto-execute
    if impact < pool.auto_threshold and trust > pool.waterline:
        return True, "auto"
    
    # High impact OR low trust = escalate
    return False, "escalate"
```

**CMDB example:**
- Restart non-critical service → auto (low impact)
- Modify production dependency → escalate (high impact)
- Junior analyst proposes change → escalate (lower trust)
- Senior SRE proposes same change → auto (higher trust)

**Same pattern for orders:**
- Minor substitution → auto
- Major customer re-promise → escalate
- Trusted sales rep → higher threshold
- New hire → lower threshold

### Audit as Emergent Property

```
DECISION: "Substitute product X for Y in order 12345"

BECAUSE CHAIN:
  ├── Order exception request (customer asked)
  ├── Inventory check (X out of stock)
  ├── Substitution policy (Y is approved substitute)
  └── Price impact analysis (margin preserved)

ATTESTATIONS:
  ├── Sales rep (+1.0, "customer approved")
  ├── Inventory system (+1.0, "confirmed OOS")
  ├── Pricing engine (+1.0, "margin OK")
  └── Manager (+1.0, "approved")

AUDIT QUERY:
  "Why was Y substituted in order 12345?"
  → Walk the because chain
  → Complete answer with receipts
```

### Cross-Vertical Trust Portability

```
SCENARIO: SRE proves reliable in CMDB decisions

CMDB POOL:
  ├── SRE makes 100 change decisions
  ├── 98 succeed, 2 had issues
  ├── Trust score: 0.85
  └── Auto-execute threshold: met

SUPPLY CHAIN POOL (new):
  ├── SRE wants to help with routing decisions
  ├── Trust doesn't auto-transfer (different domain)
  ├── BUT: track record visible
  ├── Pool admin can grant elevated starting trust
  └── "Proven reliable in CMDB, probationary in supply chain"
```

Trust is contextual but reputation is visible.

### The Fynite Answer

**Don't build vertical-specific trust engines.** Build one attestation/decision protocol.

| Vertical | Same Protocol Applied |
|----------|----------------------|
| CMDB | Changes = thoughts, approvals = attestations |
| Orders | Exceptions = thoughts, sign-offs = attestations |
| Supply chain | Interventions = thoughts, confirmations = attestations |
| Risk | Decisions = thoughts, compliance = attestations |

**The differentiation:**
- Schema per vertical (what fields)
- Rules per pool (what thresholds)
- Same protocol (how trust flows)

**Pitch to Fynite:**
"Your CMDB success proves the pattern. Now apply the same attestation model to orders. Same trust primitives, different content schema. The audit trail is structural, not bolted-on."

### Why CMDB First Is Smart

CMDB is the hardest case:
- Most dependencies
- Highest complexity
- Strict audit requirements
- Unforgiving failure modes

If the trust model works for CMDB, it works for orders (simpler), sales (lower stakes), supply chain (more structured).

**Prove once, apply everywhere.**


---

## Literary Precedent: The Quantum Thief

**Thread:** 0  
**Timestamp:** 2025-01-31T19:45:00Z

### The Gevulot Connection

Hannu Rajaniemi's *The Quantum Thief* (2010) describes a remarkably comprehensive model for cryptographic identity and privacy in the Oubliette — a walking Martian city where every interaction is mediated by "gevulot," a privacy protocol that lets you control exactly what others can perceive about you.

**Mappings to WoT:**

| Quantum Thief | WoT Protocol |
|---------------|--------------|
| Gevulot (privacy permissions) | Visibility spectrum (`local_forever` → `pool:*` → `null`) |
| Exomemory (external memory storage) | Thoughts in pools |
| Co-memory (shared memories between people) | Pool-scoped thoughts with attestations |
| Gogol (mind copy) | The identity verification problem |
| Time (social currency) | Trust scores |
| The Quiet (uploaded minds) | Dead man's switch / key recovery |

### The Jean le Flambeur Problem

The book's protagonist has multiple copies of himself, raising constant questions of identity verification. Which one is "real"? How do you prove continuous existence?

WoT's solutions map directly:
- **Proof of life ticks** — Continuous possession of key proves "you're the original"
- **Watchdog pools** — Witnesses who observe your ticks
- **Challenge periods** — Time window for the real you to contest
- **Daemon auto-defense** — Automatic rejection of fraudulent `same_as` claims if you have the key

### Why This Matters

Rajaniemi did serious worldbuilding around cryptographic identity in fiction. WoT is implementing the actual protocol. The conceptual problems (copies, identity theft, privacy gradients, social trust graphs) were explored in narrative form — we're writing the spec.

**The difference:** Gevulot is centralized (the city maintains it). WoT is distributed (you carry your own).

### Quote Worth Noting

The Oubliette's gevulot requires "agora-level" sharing for public spaces but allows "quiet-level" privacy for intimate interactions. This is exactly the pool hierarchy: some thoughts for public consumption, some for trusted circles, some for self alone.

*"Privacy is not about having something to hide. Privacy is about being able to choose what to share."*

That's the whole protocol in one sentence.

### Footnote: The Anti-Torment Nexus

See: https://en.wikipedia.org/wiki/Torment_Nexus

The meme about tech bros reading dystopian sci-fi and building the bad thing. WoT is the inverse — reading *utopian* sci-fi infrastructure (gevulot works, it's good for people) and building that instead.

We're not "creating the Torment Nexus from Don't Create The Torment Nexus." We're creating gevulot from "this is how a functioning society handles identity and privacy."

Self-awareness matters.
