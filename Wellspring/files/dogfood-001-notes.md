# Dogfood 001: Bootstrap Edge Testing

**File:** `wellspring-dogfood-001.jsonl`
**Date:** 2026-01-30
**Thoughts:** 16

---

## What's in the file

### Schema Stack (lines 1-7)
```
bootstrap_terminal_v1  ← human-readable, self-evident
    ↓ because
primitives_v1          ← string, int, float, bool, bytes, array, map, option, cid
    ↓ because
meta_schema_v1         ← how to read type definitions
    ↓ because
schema_thought_v1      ← the one primitive
schema_identity_v1     ← participant who can sign
schema_basic_v1        ← simple content
schema_connection_v1   ← typed relationship
schema_attestation_v1  ← signed belief
```

### Identities (lines 8-9)
- `keif_identity` — sovereign, self-referential (created_by = self)
- `claude_identity` — managed, parent = keif, created_by keif

### Real Thoughts (lines 10-12)
1. Core insight: "Memory is not storage, memory is traversal history"
2. Merkle DAG properties (claude, because → thought 1)
3. Self-describing principle (keif, because → thoughts 1 & 2)

### Connections (line 13)
- thought_002 `derives_from` thought_001

### Attestations (lines 14-15)
- keif attests thought_002 +1.0 (with content anchor!)
- keif attests connection_001 +1.0

---

## Bootstrap Edges Hit

### ✅ Self-describing chain works
- Bootstrap terminal is genuinely readable by human
- Each layer references the layer below via `schema_cid`
- Each layer's `because` points to what it depends on
- Test vector in bootstrap terminal (SHA-256 of "hello") is verifiable

### ✅ Identity self-reference works
- `keif_identity` has `created_by: cid:keif_identity`
- Bootstraps from nothing (because: [])
- This is the "terminal" for identity trust

### ✅ Managed identity chain works
- Claude's `parent: cid:keif_identity`
- Claude's `created_by: cid:keif_identity`
- Claude's `because: [cid:keif_identity]`
- Trust derives from Keif

### ✅ Because chains as trails
- thought_003.because → [thought_001, thought_002]
- Walking backward from 003: 003 → 002 → 001, 003 → 001
- The trail is implicit in the structure

### ✅ Content selectors in because
- attestation_001 uses anchor with exact/prefix/suffix
- References *specific text* in v0.5 spec
- Demonstrates partial-thought referencing

### ⚠️ Edge: BOOTSTRAP created_by
- Bootstrap layers use `created_by: "BOOTSTRAP"` (string literal)
- This breaks the "all CIDs" rule
- Options:
  1. Special-case BOOTSTRAP as terminal constant
  2. Create a "genesis identity" thought
  3. Leave as design decision (self-evident doesn't need attribution)

### ⚠️ Edge: CID placeholders
- All CIDs are `cid:human_readable_name`
- Real implementation needs actual SHA-256 hashes
- But placeholders make debugging readable
- Consider: keep human-readable aliases alongside real CIDs?

### ⚠️ Edge: Signature placeholders
- All signatures are placeholder strings
- Real implementation needs Ed25519 signing
- Bootstrap signatures are special-cased as "self-evident"

### ⚠️ Edge: schema_cid on bootstrap terminal
- Bootstrap terminal has NO schema_cid (it IS the terminal)
- Should this be explicit? `schema_cid: null` vs absent field?

---

## Questions Surfaced

1. **Genesis identity problem**: Who creates the first identity? Currently self-referential, but what signs it?
   - Answer: The identity signs itself. Pubkey in content, signature proves possession of private key.
   - Chicken-egg resolved: pubkey doesn't need external attestation, it's self-proving.

2. **Bootstrap versioning**: If bootstrap_terminal_v1 changes, everything above changes CID.
   - This is probably correct behaviour (breaking change = new chain)
   - But migration story matters

3. **Schema evolution**: New field added to basic thought schema?
   - Create schema_basic_v2
   - Old thoughts still reference schema_basic_v1
   - New thoughts reference v2
   - Reader needs both schemas available

4. **because as array vs single**: Currently array, but most thoughts have 0-2 causes.
   - Array is more general
   - ContentRef structure handles partial references
   - Keep as array

5. **Content selector verification**: How do we verify anchor text actually exists in target?
   - segment_cid is cryptographic proof
   - anchor is human recovery
   - In jsonl, we can't verify without fetching target
   - Local index should cache this

---

## Next Steps

1. **Add actual CID computation**
   - Write Python/Rust that hashes content → real CIDs
   - Update file with computed CIDs
   - Verify self-consistency

2. **Add signature verification**
   - Generate keypair for Keif identity
   - Sign thoughts with private key
   - Verify signatures

3. **Test trail walking**
   - Write code that walks because chains
   - Verify reachability
   - Compute simple salience

4. **Test attestation discovery**
   - Query: "all attestations on thought_002"
   - Should find attestation_001

5. **Add more thought types**
   - Pool thought
   - Trail bookmark thought
   - Aspect thought

---

*First dogfood complete. The bootstrap chain is coherent. Self-description works. Because chains form trails. Content selectors enable partial reference. Main gaps: real crypto, real CIDs, genesis identity ceremony.*
