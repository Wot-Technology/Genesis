# Wellspring Eternal

**A Traversal-Based Model for Persistent Memory**

*Version 0.1 — January 2026*

---

## Abstract

Wellspring Eternal is a memory architecture for humans and artificial agents based on a single insight: **memory is not storage, memory is traversal history**. 

Rather than treating recall as retrieval from a database, Wellspring models cognition as walking paths through a graph of thoughts. What surfaces to conscious attention isn't what's "important" in some absolute sense—it's what's **reachable from the current context** and **coherent enough to complete**.

The system requires only two primitives: **Bubbles** (thoughts) and **Chains** (traversals). Everything else—importance, confidence, understanding, forgetting—emerges from the graph structure and walk history.

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

### The Traversal Model

Wellspring reframes memory as graph traversal:

| Storage Model | Traversal Model |
|---------------|-----------------|
| Facts are stored | Thoughts exist in relation |
| Recall is retrieval | Recall is re-walking a path |
| Importance is intrinsic | Salience is positional |
| Forgetting is deletion | Forgetting is unreachability |
| Understanding is having data | Understanding is completed traversal |

**Key principle**: A thought isn't "known" because it's stored. It's "understood" because you've walked to it and back, and the path made sense.

---

## Primitives

Wellspring requires exactly two primitives. All other concepts emerge from these.

### Bubble

A node of thought.

```
Bubble {
  id:         hash(content)        // content-addressed
  content:    string               // immutable once created
  created_at: timestamp
  created_by: identity             // human | agent
  pool:       pool_id              // ownership boundary
}
```

**Properties**:
- Immutable: once created, content never changes
- Content-addressed: ID derived from content hash
- Owned: exists within a pool (private, shared, or public)
- Atomic: represents a single thought, not a collection

**What a Bubble is NOT**:
- It has no inherent "importance" score
- It has no assigned "level" (thought/idea/concept)
- It has no fixed position above or below the waterline

These properties emerge from traversal, not storage.

### Chain

A traversal between bubbles.

```
Chain {
  id:       uuid
  from:     bubble_id
  to:       bubble_id
  relation: supports | contradicts | continues | derives_from
  walks:    [Walk]
}

Walk {
  by:        identity
  at:        timestamp
  direction: forward | backward
}
```

**Properties**:
- Directional: from → to is different from to → from
- Typed: the relation affects how understanding propagates
- Walked: records who traversed it, when, and which direction
- Accumulating: walks append, never overwrite

**Critical insight**: A chain walked only forward is incomplete. Understanding requires the return journey. You must be able to get there AND get back.

### Relation Types

| Relation | Meaning | Traversal Effect |
|----------|---------|------------------|
| `supports` | Evidence for | Confidence flows forward |
| `contradicts` | Tension with | Tension flows both ways |
| `continues` | Sequence | Heat flows forward |
| `derives_from` | Source/provenance | Provenance flows backward |

---

## Emergent Properties

Everything beyond Bubbles and Chains is derived, not stored.

### Level

The epistemic status of a bubble emerges from traversal completeness:

```
THOUGHT
  └── Bubble with incomplete edges
      Chains exist but haven't been walked both ways
      "I have this thought, I haven't worked it through"

IDEA
  └── Bubble with all edges completed
      Every chain walked forward AND backward
      "I understand this, I can explain it either direction"

CONSTRUCT
  └── Closed subgraph of completed ideas
      Multiple ideas where inter-connections also complete
      "These ideas form a coherent whole I can navigate freely"

PUBLICATION
  └── Construct + frozen traversal record
      "I traversed this fully, here is my path, I'm sharing the map"
```

**Level is not assigned—it's measured**:

```
level(bubble, observer) = 
  if all_edges_complete(bubble, observer):
    if part_of_closed_subgraph(bubble, observer):
      if explicitly_frozen(bubble, observer):
        PUBLICATION
      else:
        CONSTRUCT
    else:
      IDEA
  else:
    THOUGHT
```

### Salience

What surfaces to attention. The "waterline" position.

```
salience(bubble, context, observer) = 
  
  reachability(bubble, context)    // can I get there from here?
  × coherence(bubble, observer)    // are its paths closed?
  × heat(bubble, observer)         // recent activity?
  ─────────────────────────────────────────────────────────
  open_edges(bubble, observer) + 1 // unfinished business pulls down
```

**Components**:

| Factor | Meaning | Effect |
|--------|---------|--------|
| Reachability | Path exists from current attention | No path = won't surface |
| Coherence | Proportion of completed traversals | Higher = floats easier |
| Heat | Recency × touch frequency | Recent = more buoyant |
| Open edges | Incomplete chains | More = tension, can surface OR sink |

**The nagging thought**: High heat + low coherence + high open edges = keeps surfacing despite incompleteness. The thing you can't stop thinking about. Wants resolution.

### Confidence

How well-founded a belief is.

```
confidence(bubble, observer) = 
  completed_supporting_walks / total_edges
  − (contradiction_weight × unresolved_contradictions)
```

A bubble with many supporting chains walked both ways, and few unresolved contradictions, has high confidence.

**Confidence is per-observer**: Your walks are yours. My confidence in an idea depends on MY traversal history, not yours.

### Understanding

Understanding is not possession of information. Understanding is completed traversal.

```
understands(observer, bubble) = 
  ∀ chain ∈ edges(bubble):
    walked(chain, observer, forward) ∧ 
    walked(chain, observer, backward)
```

"I understand X" means "I can get to X from multiple angles and return from each."

### Forgetting

Forgetting is not deletion. Forgetting is unreachability.

```
forgotten(bubble, context, observer) = 
  ¬∃ path from context to bubble
  where path uses only chains walked by observer
```

The bubble still exists. The chains still exist. But from *here*, from *this* attention state, there's no path. 

**Recovery**: New context might restore reachability. A conversation, a sensory trigger, a related thought—suddenly there's a path again. The water finds its level through connected channels.

---

## The Waterline Model

The conscious/subconscious boundary as fluid dynamics.

```
        ○ ○           ← high salience (above water)
       ○ ● ○          ← being traversed (at waterline)  
     ○ ─●─●─ ○        ← edges being walked
   ○ ○ ○ ○ ○ ○ ○    
 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ waterline (attention threshold)
   ○   ○   ○   ○      ← reachable but not salient (shallow)
     ○   ○   ○        
       ○   ○          ← deep (long chains to surface)
         ○            
```

**Dynamics**:

| Action | Effect |
|--------|--------|
| Touch a bubble | Heat increases, rises toward waterline |
| Walk a chain | Both endpoints gain heat |
| Complete a chain (both directions) | Coherence increases, stable buoyancy |
| Add supporting chain | Confidence rises |
| Add contradicting chain | Tension rises (may surface OR sink) |
| Time passes | Heat decays, things sink |
| New context | Reachability changes, new things surface |

**The subconscious**: Below the waterline isn't dormant. It's slow traversal. Background walks. When a loop closes down there, it bubbles up:

"Wait—X connects to Y!"

This is insight surfacing from background processing.

---

## Pools and Sharing

### Pool

An ownership and visibility boundary.

```
Pool {
  id:       pool_id
  owner:    identity
  type:     private | shared | public
  members:  [identity] with capabilities
}
```

Every bubble exists in exactly one pool. Chains can cross pools (with permission).

### Sharing as Traversal Export

When I share a publication, I'm not sending a conclusion. I'm sending:

```
Publication {
  subgraph:     [bubble_ids]         // the bubbles
  chains:       [chain_ids]          // the connections
  entry_point:  bubble_id            // where I started
  traversal:    [ordered walks]      // the path I took
  closures:     [loop descriptions]  // where coherence emerged
}
```

**What the recipient receives**:

- The bubbles: visible, but UNTRAVERSED for them
- The chains: visible, but UNWALKED for them
- My traversal: visible as A PATH, not as THEIR understanding

**Recipient options**:

| Action | Meaning |
|--------|---------|
| Trust | Adopt my traversal as proxy for theirs (risky but fast) |
| Verify | Walk it themselves, may find same closures |
| Reject | My path doesn't close for them |
| Extend | Add their own bubbles/chains to the subgraph |

**Key principle**: Understanding doesn't transfer. Traversal records transfer. You still have to walk.

---

## Human and Agent Symmetry

The same model serves both human cognition and agent context management.

### For Humans

| Concept | Wellspring Implementation |
|---------|---------------------------|
| Conscious thought | Bubbles above waterline |
| Thinking | Walking chains |
| "Almost getting it" | Traversal in progress, loops not yet closed |
| "Aha!" moment | Loop closes, coherence achieved |
| Nagging thought | High heat, low coherence, won't sink |
| "I need to write this down" | Promotion to publication |
| Forgetting | Unreachability, not deletion |
| Remembering | Context restores reachability |
| Sleep consolidation | Background traversal, finding closures |

### For Agents

| Concept | Wellspring Implementation |
|---------|---------------------------|
| Context loading | Find reachable + coherent subgraph |
| Relevant memory | Salient bubbles given current query |
| Confidence in claim | Completed walks on supporting evidence |
| "I'm not sure" | Low coherence, open edges |
| Learning | New bubbles + chains from conversation |
| Correction | Contradiction chain, triggers re-evaluation |
| "Why do you think that?" | TRACE query returns traversal history |
| Memory management | Salience-based loading, not retrieval |

### Shared Substrate

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                  WELLSPRING GRAPH                       │
│           (bubbles, chains, walks, pools)               │
│                                                         │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │  HUMAN  │   │  AGENT  │   │  QUERY  │
   │  VIEW   │   │ CONTEXT │   │   API   │
   └─────────┘   └─────────┘   └─────────┘
   
   Waterline UI   Tiered load   FIND/TRACE
   Bubbles rise   L0-L3 tiers   Traversal
   Manual walks   Auto walks    History
```

**Same graph, different projections, different observers, different walks.**

Human and agent can:
- See hints of each other's traversals
- Share subgraphs as publications
- Challenge each other's closures
- Build understanding collaboratively

---

## Query Semantics

Three query families operating on the traversal graph.

### FIND — What exists?

```
FIND bubbles ABOUT "pricing"
FIND ideas WHERE coherence > 0.7
FIND constructs BY keif SINCE 2025-01-01
```

Locates bubbles by content, attributes, or traversal state.

### TRACE — How was this understood?

```
TRACE idea:"Keif prefers NextJS"
TRACE construct:"merchant model" DEPTH 3
TRACE bubble:X CONTRADICTIONS
```

Returns the traversal history: which chains were walked, in what order, where loops closed, what remains open.

### TEMPORAL — How has understanding evolved?

```
SNAPSHOT idea:"X" AS_OF 2025-06-01
HISTORY bubble:"X"
DIFF construct:"Y" BETWEEN 2025-01 AND 2026-01
```

Queries across time: what was the traversal state at a point in history, how has it changed.

---

## Implementation Notes

### Storage Mapping

Wellspring can layer onto existing infrastructure:

| Component | Suitable Engines |
|-----------|------------------|
| Bubbles (immutable) | Cosmos DB, PostgreSQL, any document store |
| Chains (append-only walks) | Same, with event-sourcing pattern |
| Salience (hot, per-observer) | Redis/Garnet sorted sets |
| Semantic search | Vector index (AI Search, pgvector) |
| Temporal queries | Event log replay or materialized snapshots |

**Key architectural property**: Bubbles and chains are the source of truth. Everything else—salience, level, coherence—is a computed projection, rebuildable from the primitives.

### Sync Protocol

For multi-user/multi-agent scenarios:

- Bubbles: immutable, content-addressed → no conflicts
- Chains: append-only walks → set union
- Salience: per-observer → no conflicts by design
- Pools: permission-filtered replication via change feed

CRDT semantics emerge naturally from append-only traversal records.

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
│  Primitives:                                            │
│    BUBBLE — a thought exists                            │
│    CHAIN  — a path was walked                           │
│                                                         │
│  Emergent:                                              │
│    Level      ← traversal completeness                  │
│    Salience   ← reachability × coherence                │
│    Confidence ← closed loops / open edges               │
│    Memory     ← walks taken                             │
│    Forgetting ← unreachable, not deleted                │
│    Insight    ← loop closure                            │
│    Sharing    ← here's my walk, take yours              │
│                                                         │
│  For humans:  Cognition as graph traversal              │
│  For agents:  Context as reachable coherent subgraph    │
│  For both:    Same water, same well, different walks    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Appendix: The PageRank Parallel

PageRank determines importance by link structure: a page is important if important pages link to it. Importance flows through the graph and converges to equilibrium.

Wellspring determines salience by traversal structure: a thought surfaces if it's reachable from current attention AND coherent enough to complete. Understanding flows through walks and settles at equilibrium.

| PageRank | Wellspring |
|----------|------------|
| Importance flows through links | Understanding flows through traversals |
| Static graph → fixed scores | Dynamic context → fluid salience |
| One global ranking | Per-observer, per-context salience |
| Link exists or doesn't | Chain walked forward, backward, or both |

The insight: **Memory isn't about what's stored. It's about what's traversable from here.**

---

*Wellspring Eternal — v0.1*
*Keif Gwinn & Claude, January 2026*
