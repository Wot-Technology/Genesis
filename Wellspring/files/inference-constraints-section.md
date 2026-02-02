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
  // Can't be both

DISJOINT: child, adult
  // Age-based, one or other
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

**For WOT decisions:**

```
DECISION: friday-dinner
  constraints:
    min_options_satisfying(everyone-can-eat): 1
    // At least one option must pass dietary requirements
```

### Equivalence (Same-As)

Identity resolution across representations:

```
CHAIN: "Keef" → same_as → "Keif"
  attestation: { by: keif, +1.0 }
  // Typo correction

CHAIN: keif@gmail.com → same_as → keif@buymaterials.co.uk
  attestation: { by: keif, +1.0 }
  // Same person, different contexts

CHAIN: external:nandos-manchester → same_as → google_places:ChIJ...
  attestation: { by: agent, +0.9 }
  // Entity resolution across sources
```

**Properties:**
- Symmetric: A same_as B → B same_as A
- Transitive: A same_as B, B same_as C → A same_as C
- Attestations on one apply to all equivalents

---

### Composite Expressions

Aspects can be composed from other aspects using set operations.

#### Expression Types

```
INTERSECTION (AND)
  All components must be satisfied

UNION (OR)
  Any component satisfies

COMPLEMENT (NOT)
  Satisfied iff component is NOT satisfied
```

#### Evaluation Modes

**Must (min/max semantics)**

For hard requirements. Weakest link determines outcome.

```
mode: must

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
  weight: +0.9 (is fast food)
  result: -0.9  // fails complement
```

**Prefer (weighted semantics)**

For soft preferences. Balanced consideration.

```
mode: prefer

weighted_intersection:
  nice-evening = romantic × 0.4 + good-food × 0.4 + convenient × 0.2
  weights: [+0.7, +0.9, +0.3]
  result: (0.7×0.4) + (0.9×0.4) + (0.3×0.2) = 0.70

weighted_union:
  entertaining = live-music × 0.5 + good-cocktails × 0.3 + dancing × 0.2
  // Same calculation, but conceptually "any of these helps"
```

#### Composite Aspect Definition

```
ASPECT: family-friendly
  type: composite
  mode: must
  expression: intersection_of
    - kid-friendly
    - affordable  
    - has-parking
  // All three required. Min semantics.

ASPECT: date-worthy
  type: composite
  mode: prefer
  expression: weighted_of
    - romantic: 0.4
    - good-food: 0.4
    - not-too-loud: 0.2
  // Weighted average. Soft preference.

ASPECT: accessible
  type: composite
  mode: must
  expression: union_of
    - wheelchair-ramp
    - ground-floor
    - has-lift
  // Any one suffices. Max semantics.
```

---

### Decision Evaluation

Composite expressions enable two-phase decision evaluation:

```
DECISION: friday-dinner

must:
  intersection_of:
    - everyone-can-eat      // dietary
    - within-budget         // £25pp max  
    - someone-can-drive     // logistics
  mode: must
  // ANY component -1.0 = option eliminated

prefer:
  weighted_of:
    - kids-happy: 0.35
    - good-food: 0.30
    - easy-parking: 0.20
    - quick-service: 0.15
  mode: prefer
  // Weighted ranking of survivors

EVALUATION PIPELINE:

1. FILTER: Apply must constraints (min semantics)
   nandos:      must = min(+0.8, +0.9, +0.7) = +0.7  ✓
   wagamama:    must = min(+0.9, +0.8, +0.6) = +0.6  ✓
   local-pub:   must = min(-1.0, +0.9, +0.8) = -1.0  ✗ (sarah veto)
   
2. RANK: Apply prefer weights to survivors
   nandos:      prefer = 0.82
   wagamama:    prefer = 0.71
   
3. RESULT: nandos wins (highest prefer among must-passing)
```

---

### Open World Assumption

Wellspring operates under open world assumption:

```
OPEN WORLD

Absence of attestation ≠ belief of 0.0
Absence of attestation = no information

keif has not attested on wagamama/parking
  ≠ keif believes wagamama has bad parking
  = keif hasn't expressed a view

IMPLICATIONS:
- Can't infer negatives from silence
- Must explicitly attest 0.0 to mark "dormant"
- Must explicitly attest -1.0 to mark "disbelieve"
- Unknown stays unknown until observed
```

This differs from closed-world databases where missing row = false.

---

### Inference Summary

```
┌─────────────────────────────────────────────────────────┐
│ INFERENCE RULES                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Relation Characteristics                                │
│   transitive, symmetric, inverse, functional            │
│   Declared per relation. Enables auto-inference.        │
│                                                         │
│ Property Chains                                         │
│   works_in_country = works_at → headquartered_in        │
│   Computed on query, not stored.                        │
│                                                         │
│ Disjointness                                            │
│   vegetarian ⊥ contains_meat                            │
│   System flags contradictions.                          │
│                                                         │
│ Cardinality                                             │
│   min/max counts on relations                           │
│   Enforced on write, queryable.                         │
│                                                         │
│ Equivalence                                             │
│   same_as: symmetric, transitive                        │
│   Attestations transfer across equivalents.             │
│                                                         │
│ Composite Expressions                                   │
│   intersection (AND), union (OR), complement (NOT)      │
│   mode: must (min/max) | prefer (weighted)              │
│                                                         │
│ Open World                                              │
│   Absence ≠ false. Unknown stays unknown.               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
