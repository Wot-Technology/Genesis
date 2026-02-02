# Wellspring Eternal

**A Traversal-Based Model for Persistent Memory**

*Version 0.2 — January 2026*

---

## Abstract

Wellspring Eternal is a memory architecture for humans and artificial agents based on a single insight: **memory is not storage, memory is traversal history**.

Rather than treating recall as retrieval from a database, Wellspring models cognition as walking paths through a graph of thoughts. What surfaces to conscious attention isn't what's "important" in some absolute sense—it's what's **reachable from the current context** and **coherent enough to complete**.

The system requires only two primitives: **Bubbles** (thoughts) and **Chains** (relationships with attestations). Everything else—identity, trust, importance, confidence, understanding, forgetting—emerges from the graph structure, walk history, and cryptographic attestations.

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

Attestation {
  by:         identity_bubble_id      // who is attesting
  at:         timestamp               // when
  belief:     float [-1.0 to 1.0]     // strength and direction
  signature:  sig                     // cryptographic proof
}
```

**Properties**:

- **Directional**: from → to is different from to → from
- **Typed**: the relation affects how understanding propagates
- **Signed**: chains must be signed by their creator (if capable)
- **Attested**: accumulates signed beliefs over time
- **Append-only**: attestations accumulate, never overwrite

**Relation types**:

| Relation | Meaning | Propagation Effect |
|----------|---------|-------------------|
| `supports` | Evidence for | Confidence flows forward |
| `contradicts` | Tension with | Tension flows both ways |
| `continues` | Sequence/thread | Heat flows forward |
| `derives_from` | Source/provenance | Provenance flows backward |
| `vouches` | Trust endorsement | Trust flows forward |

### Attestation

A signed belief about a chain, grounded in reasoning.

```
Attestation {
  by:        identity_bubble_id      // who is attesting
  at:        timestamp               // when
  belief:    float [-1.0 to 1.0]     // strength and direction
  because:   [chain_id]              // grounds for this belief
  signature: sig                     // cryptographic proof
}
```

**The `because` field is critical**: Every attestation is grounded. "I believe this" is never floating — it points to the chains that led to that belief.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  UNGROUNDED (old model)                                 │
│  "I believe A→B with strength 0.8"                      │
│  Why? Who knows.                                        │
│                                                         │
│  GROUNDED (Wellspring)                                  │
│  "I believe A→B with strength 0.8                       │
│   BECAUSE I walked chains [C, D, E]                     │
│   and they closed the loop for me"                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Causal structure**:

```
       Chain X: A supports B
                  │
       Attestation: belief +0.8
                  │
               because
                  │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
  Chain C    Chain D    Chain E
 (evidence) (evidence) (traversal)
```

**This enables**:

| Question | Answer via |
|----------|-----------|
| "Why do you believe this?" | attestation.because → chains |
| "What changed your mind?" | diff attestations' because fields |
| "Is this well-founded?" | recurse into because chains |
| "We disagree — why?" | compare our because chains |

**Mind change becomes traceable**:

```
Jan:  attest +0.8 because [evidence_A, evidence_B]
Jun:  attest +0.3 because [counter_evidence_C]  
Sep:  attest -0.5 because [refutation_D, expert_E]

Full intellectual history. Each shift grounded.
"Show me how my thinking evolved" → attestation timeline with because chains
```

**Forgetting is also grounded**:

```
{
  by: keif
  at: 2025-06-01
  belief: 0.0
  because: [chain_to_burnout, chain_to_new_priority]
}

"I let this go BECAUSE burnout + new priorities"

Later: "Why did I drop this?" → because → full context
```

### Attestation Semantics

Attestations are signed beliefs about chains, grounded in reasoning. They capture:

- **Who**: identity making the attestation (must have signing capability)
- **When**: timestamp of attestation
- **What**: belief strength from -1.0 (disavow) to +1.0 (endorse)
- **Why**: chain_ids that ground this belief (the `because` field)
- **Proof**: cryptographic signature

**The Belief Spectrum**:

```
+1.0  "I fully endorse this"
 ...
+0.5  "I somewhat believe this"
 ...
 0.0  "I'm not holding this right now" ← DORMANT/FORGOTTEN
 ...
-0.5  "I doubt this"
 ...
-1.0  "I actively disavow this"
```

**Zero is not negative. Zero is dormant.** The thought sleeps. It can wake.

**Mind changes are data, not corrections**:

```
Timeline of attestations on a chain:

  Jan 1:   attest +0.9 because [initial_evidence]
           "I'm confident based on this evidence"
           
  Feb 16:  attest +0.3 because [counter_evidence]
           "Less sure after seeing this"
           
  Mar 1:   attest -0.8 because [refutation, expert_opinion]
           "I now believe this was wrong because..."

Nothing deleted. Full history preserved.
Current belief = latest attestation.
The FACT that you changed your mind is information.
The REASON you changed is information.
```

---

## Identity Model

Identity is not a separate primitive. Identity is a bubble that can sign.

### Identity as Bubble

```
Identity Bubble {
  content: {
    type:     sovereign | delegated | record | external
    pubkey:   key | null              // null for non-signing types
    label:    string                  // human-readable, not authoritative
    parent:   identity_bubble_id | null  // for delegated identities
    metadata: { ... }                 // type-specific data
  }
  created_by: self | parent           // self-signed or parent-signed
  signature:  sig | null
}
```

### Identity Types

```
┌─────────────────────────────────────────────────────────┐
│  SOVEREIGN                                              │
│  ─────────                                              │
│  Humans, persistent agents, organizations               │
│                                                         │
│  • Owns keypair, persists and rotates keys              │
│  • Signs own bubbles and chains                         │
│  • Creates attestations                                 │
│  • Vouches for other identities                         │
│  • Full participant in web of trust                     │
│  • Self-signed identity bubble                          │
│                                                         │
│  Example: Keif Gwinn, BuyMaterials (org), Claude (agent)│
│                                                         │
├─────────────────────────────────────────────────────────┤
│  DELEGATED                                              │
│  ─────────                                              │
│  Sessions, API tokens, service accounts, acting agents  │
│                                                         │
│  • Key derived from or vouched by sovereign             │
│  • Can sign (authority delegated from parent)           │
│  • Can attest (within delegated scope)                  │
│  • Trust flows from parent                              │
│  • Revocable by parent                                  │
│  • Limited scope and/or TTL                             │
│                                                         │
│  Example: "Claude (Keif's session)", "RoboGeoff API"    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  RECORD                                                 │
│  ──────                                                 │
│  Import jobs, log sources, data migrations              │
│                                                         │
│  • No signing capability                                │
│  • Cannot attest                                        │
│  • Trust = 0 until vouched by signing identity          │
│  • Represents "this content came from this process"     │
│                                                         │
│  Example: "Legacy ERP Import 2025-06-01"                │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  EXTERNAL                                               │
│  ────────                                               │
│  Web sources, APIs, third-party systems                 │
│                                                         │
│  • No signing capability                                │
│  • Cannot attest                                        │
│  • Trust via reputation model (historical accuracy)     │
│  • Represents "this content claims to be from here"     │
│                                                         │
│  Example: "https://buildingproducts.co.uk", "Reuters"   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Identity Capability Matrix

| Type | Has Key | Can Sign | Can Attest | Trust Source |
|------|---------|----------|------------|--------------|
| Sovereign | ✓ | ✓ | ✓ | Web of trust |
| Delegated | ✓ | ✓ | Scoped | Parent vouches |
| Record | ✗ | ✗ | ✗ | Must be vouched |
| External | ✗ | ✗ | ✗ | Reputation chain |

### Delegation as Authority

Delegated identities carry authority from their parent:

```
┌──────────────┐
│    Keif      │ (sovereign)
│  can: *      │
└──────┬───────┘
       │ vouches (scope: "act on BuyMaterials", ttl: "session")
       ▼
┌──────────────┐
│Claude Session│ (delegated)
│ can: sign,   │
│ attest,      │
│ create       │
└──────┬───────┘
       │ vouches (scope: "merchant queries", ttl: "24h")
       ▼
┌──────────────┐
│  RoboGeoff   │ (delegated)
│  can: sign,  │
│  create      │
│  (no attest) │
└──────────────┘
```

**Authority flows down, trust flows up**:
- Delegated identity can only grant ≤ what it has
- Observer trusts delegated identity ≤ trust in parent

### Key Rotation

Sovereign identities rotate keys by vouching their successor:

```
┌─────────────────┐         ┌─────────────────┐
│  keif_key_2024  │──vouches──►│  keif_key_2025  │
│  (retired)      │         │  (active)       │
└─────────────────┘         └─────────────────┘

Attestation: { belief: 1.0, note: "key rotation" }

• Old key signs: "This new key is me"
• Chain of custody preserved
• Historical signatures still verify against old key
• New content signed with new key
```

### Pseudonymity

Anonymity is a visibility choice, not a system property. The chain always exists.

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  PUBLIC POOL                     KEIF'S PRIVATE POOL     │
│                                                          │
│  ┌──────────────┐                ┌──────────────┐        │
│  │ throwaway_99 │◄───vouches─────│     Keif     │        │
│  │ (delegated)  │   (hidden)     │  (sovereign) │        │
│  └──────────────┘                └──────────────┘        │
│         │                                                │
│         │ created_by                                     │
│         ▼                                                │
│  ┌──────────────┐                                        │
│  │ "hot take on │                                        │
│  │  local news" │                                        │
│  └──────────────┘                                        │
│                                                          │
│  Public sees: throwaway_99 said X                        │
│  Keif can prove: that was me (reveal vouch chain)        │
│  System knows: chain exists, even if not revealed        │
│                                                          │
│  Anonymity = visibility choice on the vouch chain        │
│  Traceability = structural property, always present      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Trust Model

Trust emerges from the graph structure. It is not assigned—it is computed.

### Trust is Computed, Not Stored

There is no `trust` field on any primitive. Trust is always derived at query time from:

1. **Vouches chains** between identities
2. **Attestation history** on those chains
3. **Because chains** grounding those attestations
4. **Recursion** through the reasoning graph

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  TRUST IS A FUNCTION, NOT A VALUE                       │
│                                                         │
│  trust(source, observer, context, time) =               │
│    f(vouches_chains, attestations, because_chains)      │
│                                                         │
│  Same source can have different trust:                  │
│    - from different observers                           │
│    - in different contexts                              │
│    - at different times                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Web of Trust

Trust between sovereign identities flows through vouches chains:

```
trust_wot(source, observer) =

  // Find all paths of vouches chains from observer to source
  paths = find_vouch_paths(observer → source)
  
  if no paths:
    return 0  // no trust relationship
  
  for each path P:
    path_trust = 1.0
    
    for each vouch_chain in P:
      // Get latest attestation on this vouch
      attest = latest_attestation(vouch_chain)
      
      // How well-grounded is this vouch?
      grounding = groundedness(attest.because)
      
      path_trust *= attest.belief × grounding
    
    // Decay by distance
    path_trust *= (decay_factor ^ path_length)
    
  return max(all path_trusts)  // strongest path
```

### Groundedness

How well-founded is an attestation? Recurse into its `because` chains:

```
groundedness(because_chains) =

  if because_chains is empty:
    return base_groundedness  // ungrounded attestation, low
    
  for each chain_id in because_chains:
    chain = get_chain(chain_id)
    
    // Is this evidence chain itself attested?
    chain_attestations = chain.attestations
    
    if no attestations:
      chain_ground = 0.1  // unattested evidence
    else:
      // Recurse: how grounded are the attestations on the evidence?
      chain_ground = avg(
        attest.belief × groundedness(attest.because)
        for attest in chain_attestations
      )
    
    grounds.append(chain_ground)
    
  return avg(grounds)
```

### Trust Recursion Termination

The recursion must terminate. Natural termination points:

| Termination | Groundedness |
|-------------|--------------|
| Self-attested by sovereign you directly trust | High (trust anchor) |
| Empty `because` (ungrounded assertion) | Low (0.1 - 0.3) |
| Circular reference (A because B because A) | Detect and cap |
| Depth limit exceeded | Use value at limit |
| External source with reputation | Use reputation score |

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  TRUST ANCHORS                                          │
│                                                         │
│  The recursion has to bottom out somewhere:             │
│                                                         │
│  • Direct vouch from someone you trust (observer)       │
│  • Verified publication (signed, timestamped)           │
│  • External source with established reputation          │
│  • Self-attestation by observer (you trust yourself)    │
│                                                         │
│  These are the bedrock. Everything else derives.        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Trust by Identity Type

```
trust(identity, observer) =

  switch identity.type:
  
    sovereign:
      // Web of trust via vouches chains
      return wot_trust(identity, observer)
      
    delegated:
      // Parent's trust, discounted by delegation depth
      parent_trust = trust(identity.parent, observer)
      return parent_trust × delegation_factor × scope_match
      
    record:
      // Zero inherent trust - sum of vouches
      vouches = find_chains(to: identity, relation: vouches)
      return max(
        attest.belief × trust(attest.by, observer)
        for vouch in vouches
        for attest in vouch.attestations
      )
      
    external:
      // Reputation model - historical accuracy
      return reputation(identity, observer)
```

### Reputation for External Sources

External sources (websites, APIs, publications) build reputation through historical accuracy:

```
reputation(source, observer) =
  
  claims = bubbles where created_by = source
  
  verified = claims where (
    ∃ chain: claim ← supports ← other_bubble
    where trust(other_bubble.created_by, observer) > threshold
  )
  
  contradicted = claims where (
    ∃ chain: claim ← contradicts ← other_bubble  
    where trust(other_bubble.created_by, observer) > threshold
  )
  
  return (verified - contradicted) / total_claims
```

---

## Confidence Model

Confidence in a bubble emerges from backchaining through trusted attestations.

### Backchain Termination

Every bubble can be traced back through `derives_from` chains:

```
THOUGHT ← derives_from ← THOUGHT ← derives_from ← ???

Where does the chain terminate?

  → SIGNED BUBBLE: trust = creator's trust score
  → UNSIGNED BUBBLE: trust = vouching chain strength
  → EXTERNAL SOURCE: trust = source reputation
  
Nothing terminates in void. Everything is weighable.
```

### Confidence Calculation

```
confidence(bubble, observer) =

  // Find all backchain paths (via derives_from)
  paths = backchain_paths(bubble)
  
  for each path P:
    
    path_confidence = 1.0
    
    for each chain C in P:
      
      // Find attestations from trusted sources
      relevant = C.attestations.filter(
        a => trust(a.by, observer) > threshold
      )
      
      if no relevant attestations:
        chain_confidence = 0.1  // unattested penalty
      else:
        // Weight attestation belief by trust in attester
        chain_confidence = weighted_avg(
          a.belief × trust(a.by, observer)
          for a in relevant
        )
      
      path_confidence *= chain_confidence
    
    // Discount by path length
    path_confidence /= path_length(P)
  
  return aggregate(all path_confidences)
```

### Confidence is Per-Observer

Different observers have different trust relationships, therefore different confidence in the same bubble:

```
Bubble: "Cosmos DB scales well for this use case"

Chain: technical_analysis → supports → claim
Attestations:
  - Keif, +0.8, 2025-06-01
  - Sarah, -0.3, 2025-09-01  (hit scaling issues)
  - Keif, +0.4, 2025-09-15   (revised after Sarah's input)

Observer: Keif
  trusts self highly, trusts Sarah highly
  confidence = considers both attestations

Observer: External auditor
  trusts Keif somewhat, doesn't know Sarah
  confidence = weighted toward Keif's attestations
  
Observer: Competitor
  trusts neither
  confidence = low regardless of attestations
```

---

## Emergent Properties

Everything beyond Bubbles and Chains is derived, not stored.

### Level

The epistemic status of a bubble emerges from traversal completeness and attestation state:

```
THOUGHT
  └── Bubble with incomplete edges
      Chains exist but haven't been walked both ways
      Low attestation coverage
      "I have this thought, haven't worked it through"

IDEA  
  └── Bubble with completed edges
      Key chains walked forward AND backward
      Self-attested (creator believes coherence)
      "I understand this, can explain it either direction"

CONSTRUCT
  └── Closed subgraph of completed ideas
      Multiple ideas, inter-connections also complete
      Attested as coherent by creator
      "These form a whole I can navigate freely"

PUBLICATION
  └── Construct + frozen attestation record
      Formally attested, signed, scoped to audience
      "I stand behind this, here is my path"
```

**Level emerges from**:
- Traversal completeness (walks)
- Attestation presence (someone vouches for coherence)
- Explicit publication act (scoped sharing)

### Salience

What surfaces to attention. The waterline position.

```
salience(bubble, context, observer) = 
  
  reachability(bubble, context)    // path exists from attention
  × coherence(bubble, observer)    // traversal completeness
  × confidence(bubble, observer)   // backchain trust
  × heat(bubble, observer)         // recency
  ─────────────────────────────────────────────────────────
  open_edges(bubble, observer) + 1 // unfinished = tension
```

### Understanding

Understanding is completed traversal. Walking to a thought and back.

```
understands(observer, bubble) = 
  ∀ chain ∈ edges(bubble):
    walked(chain, observer, forward) ∧ 
    walked(chain, observer, backward)
```

### Forgetting

Forgetting is epistemic, not structural. It's an attestation of zero, not deletion or unreachability.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Old thinking:  Forgetting = can't reach it             │
│  Wellspring:    Forgetting = belief set to dormant      │
│                                                         │
│  The bubble exists     ✓ always                         │
│  The chain exists      ✓ always                         │
│  The history exists    ✓ complete                       │
│                                                         │
│  Forgotten = latest attestation is 0.0                  │
│  The thought sleeps. It can wake.                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Explicit forgetting vs natural decay**:

| Mode | Mechanism | Attestation | Salience |
|------|-----------|-------------|----------|
| Explicit forget | "I'm done with this" | Attest 0.0 | Zero - won't surface |
| Natural decay | Time passes, not touched | Unchanged | Decays via heat factor |
| Active disbelief | "This is wrong" | Attest negative | Can still surface (tension) |

**Decay vs Forget distinction**:
- **Decay**: Still believe, just not attending. Last attestation valid, heat fades.
- **Forget**: Actively setting belief to dormant. Attestation of 0.0.

**Revival is just another attestation**:

```
Timeline:
  2025-01: attest +0.8  "I believe this"
  2025-06: attest  0.0  "Letting this go for now"
  2026-01: attest +0.6  "Actually, revisiting this..."

Nothing lost. Sleep and wake are both recorded.
WHEN you forgot is data. WHEN you revived is data.
WHY (via chains to context) is data.
```

**Salience formula respects belief state**:

```
salience(bubble, context, observer) =

  belief = latest_attestation(bubble, observer).belief
  
  if belief == 0:
    return 0  // explicitly dormant, won't surface
    
  reachability × coherence × abs(belief) × heat
  ─────────────────────────────────────────────
           open_edges + 1

// Note: negative belief CAN surface
// "This thing I disavow keeps coming up"
// Tension wants resolution
```

---

## Pools and Sharing

### Pool

An ownership and visibility boundary.

```
Pool {
  id:       pool_id
  owner:    identity_bubble_id
  type:     private | shared | public
  members:  [(identity, capabilities)]
}
```

Every bubble exists in exactly one pool. Chains can cross pools (with permission). Attestations follow the chain's visibility.

### Sharing as Traversal Export

When sharing a publication, you're not sending conclusions. You're sending a traversable subgraph with your attestations:

```
Publication Export {
  subgraph:     [bubble_ids]
  chains:       [chain_ids with attestations]
  entry_point:  bubble_id
  my_traversal: [ordered walks]
  my_closures:  [where coherence emerged for me]
}
```

**Recipient receives**:
- Bubbles: visible but untraversed *for them*
- Chains: visible with your attestations
- Your path: visible as *a* path, not *their* understanding

**Recipient options**:

| Action | Meaning |
|--------|---------|
| Trust | Accept your attestations as proxy (fast, risky) |
| Verify | Walk it themselves, form own attestations |
| Reject | Your path doesn't close for them |
| Extend | Add their own bubbles, chains, attestations |

**Key principle**: Attestations transfer. Understanding doesn't. You still have to walk.

---

## Human and Agent Symmetry

The same model serves both human cognition and agent context management.

### For Humans

| Concept | Wellspring Implementation |
|---------|---------------------------|
| Conscious thought | Bubbles above waterline |
| Thinking | Walking chains |
| "Almost getting it" | Traversal in progress, loops unclosed |
| "Aha!" moment | Loop closes, coherence achieved |
| Belief | Attestation on chains |
| Changing your mind | New attestation, history preserved |
| Forgetting | Attestation of 0.0 (dormant, can revive) |
| Remembering | New attestation reviving dormant belief |
| Trusting a source | Vouches chain + historical accuracy |
| Nagging thought | Negative attestation surfacing (tension) |

### For Agents

| Concept | Wellspring Implementation |
|---------|---------------------------|
| Context loading | Find reachable + confident subgraph |
| "I believe X" | Attestations on supporting chains |
| "I'm not sure" | Low confidence, few attestations |
| "I no longer think X" | Attestation of 0.0 on chain |
| Learning | New bubbles + chains from conversation |
| Correction | New attestation with lower/negative belief |
| "Why do you think that?" | TRACE returns attestation chain |
| Authority to act | Delegation chain from sovereign |

### Shared Substrate

```
┌─────────────────────────────────────────────────────────┐
│                    WELLSPRING GRAPH                     │
│         (bubbles, chains, attestations, pools)          │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │  HUMAN  │   │  AGENT  │   │  QUERY  │
   │  VIEW   │   │ CONTEXT │   │   API   │
   └─────────┘   └─────────┘   └─────────┘
   
   Waterline UI   Tiered load   FIND/TRACE
   Manual walks   Auto walks    Attestation
   Own attests    Own attests   History
```

Human and agent can:
- See each other's attestations (transparency)
- Challenge attestations (disagreement is data)
- Build confidence collaboratively (mutual attestation)
- Maintain separate beliefs (per-observer attestations)

---

## Query Semantics

Three query families operating on the traversal graph.

### FIND — What exists?

```
FIND bubbles ABOUT "pricing"
FIND ideas WHERE confidence > 0.7
FIND chains WHERE attestation.by = keif AND belief < 0
FIND constructs BY keif SINCE 2025-01-01
```

### TRACE — How was this understood?

```
TRACE idea:"X"
  → returns backchain paths
  → shows attestations at each step
  → shows where confidence comes from

TRACE bubble:"X" ATTESTATIONS
  → returns all attestations
  → shows belief changes over time
  → shows who attested what when
```

### TEMPORAL — How has belief evolved?

```
SNAPSHOT idea:"X" AS_OF 2025-06-01
  → state of bubble and attestations at that time

HISTORY chain:"A→B"
  → all attestations over time
  → belief trajectory

DIFF construct:"Y" BETWEEN 2025-01 AND 2026-01
  → what attestations changed
  → who changed their mind
```

---

## Implementation Notes

### Storage Requirements

| Component | Characteristics | Suitable Engines |
|-----------|-----------------|------------------|
| Bubbles | Immutable, content-addressed | Document store, IPFS |
| Chains | Append-only attestations | Event-sourced store |
| Signatures | Verification needed | Any (sig is data) |
| Trust graph | Graph traversal | Graph DB or materialized |
| Salience | Hot, per-observer | Redis/Garnet sorted sets |
| Semantic | Similarity search | Vector index |

### Cryptographic Requirements

- Keypair generation for sovereign identities
- Signature creation for bubbles, chains, attestations
- Signature verification on read
- Key rotation chain validation

### CRDT Properties

Natural conflict-free replication:
- Bubbles: immutable, content-addressed → no conflict
- Chains: identified by endpoints + creator → no conflict
- Attestations: append-only, by different identities → set union
- Trust: computed, not stored → no conflict

---

## Summary

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  WELLSPRING ETERNAL                                     │
│                                                         │
│  "Water remembers every path it has taken"              │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Two primitives:                                        │
│    BUBBLE — content + creator (always attributed)       │
│    CHAIN  — relationship + signed attestations          │
│                                                         │
│  Four identity types:                                   │
│    Sovereign  — owns keys, full participant             │
│    Delegated  — derived authority, limited scope        │
│    Record     — no keys, trust via vouching             │
│    External   — no keys, trust via reputation           │
│                                                         │
│  Everything else emerges:                               │
│    Identity    ← bubble containing pubkey               │
│    Trust       ← computed from vouches + groundedness   │
│    Delegation  ← scoped vouches from parent             │
│    Provenance  ← signatures + derives_from chains       │
│    Belief      ← signed attestation on chain            │
│    Grounding   ← because field → reasoning chain        │
│    Mind change ← new attestation, history preserved     │
│    Forgetting  ← attestation of 0 (dormant, not gone)   │
│    Confidence  ← backchain through grounded attestations│
│    Level       ← traversal completeness + attestation   │
│    Salience    ← reachability × confidence × heat       │
│                                                         │
│  Properties:                                            │
│    Nothing anonymous    — everything has creator        │
│    Nothing deleted      — attestations append           │
│    Nothing truly forgotten — dormant, can wake          │
│    Everything weighable — trust always computable       │
│    Everything auditable — signatures all the way down   │
│    Pseudonymity possible — visibility ≠ traceability    │
│                                                         │
│  For humans:  Cognition as graph traversal              │
│  For agents:  Context as trusted reachable subgraph     │
│  For both:    Same water, same well, different walks    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

*Wellspring Eternal — v0.2*  
*Keif Gwinn & Claude, January 2026*
