# WoT Pool Sync: RBSR Integration

**Specification sketch for v0.11+**

---

## Overview

Pool synchronization uses Range-Based Set Reconciliation (RBSR) to efficiently discover differences between peers. This replaces or supplements bloom filter approaches with a logarithmic-round-trip protocol resistant to adversarial manipulation.

RBSR answers: "What thoughts do you have that I don't, and vice versa?"

The BGP-inspired peering layer answers: "Which pools, what permissions, which substrates?"

---

## 1. Sync Item Model

Each syncable item is a **thought** represented as a tuple:

```
SyncItem = (timestamp: u64, cid: CID)
```

**Ordering:**
1. Primary sort: `timestamp` ascending (Unix millis)
2. Secondary sort: `cid` lexicographic (for timestamp ties)

**Rationale:**
- Timestamp clustering: Thoughts created together likely sync together
- CID is already a content hash, guaranteed unique
- Deterministic ordering across all peers

**Note:** The `timestamp` is the thought's `created_at`, not when it was received. This is intrinsic to the thought, not metadata.

---

## 2. Fingerprint Function

### 2.1 Base Fingerprint

For a set of items `{(t₁, cid₁), (t₂, cid₂), ...}`:

```
fp = truncate(SHA256(
  sum(cid_i mod 2²⁵⁶) ||    // additive hash of CIDs
  varint(count) ||           // number of items
  varint(sum(t_i) mod 2⁶⁴)   // timestamp checksum (optional hardening)
), 16)
```

**Properties:**
- Incremental: Can add/remove items in O(1)
- Tree-friendly: Subtraction works (for range queries)
- 16 bytes = 128 bits (collision probability negligible for honest sets)
- Count inclusion prevents some attack classes

### 2.2 Extended Fingerprint (Optional)

For pools where attestation weight matters:

```
fp_extended = truncate(SHA256(
  sum(cid_i mod 2²⁵⁶) ||
  varint(count) ||
  varint(sum(attestation_count_i) mod 2⁶⁴)
), 16)
```

This catches cases where the same thoughts exist but attestation counts differ — indicating the peer may have attestations we don't.

---

## 3. Tree Storage

### 3.1 Structure

B+ tree with branching factor 32-64 (tunable per implementation):

```
                    [root: fp_all, count_all]
                   /                         \
    [fp_left, count_left]          [fp_right, count_right]
         /        \                      /          \
   [leaf: items]  [leaf]            [leaf]      [leaf: items]
```

Each internal node caches:
- `fp`: Fingerprint of all items in subtree
- `count`: Number of items in subtree

Leaf nodes store actual `(timestamp, cid)` tuples.

### 3.2 Operations

| Operation | Complexity |
|-----------|------------|
| Insert item | O(log n) |
| Remove item | O(log n) |
| Range fingerprint | O(log n) |
| Range enumerate | O(log n + k) where k = items in range |

### 3.3 Implementation Note

Tree structure is **not** part of the protocol. Implementations may use:
- B+ tree (recommended)
- Skip list
- Sorted vector (for small/static sets)
- LSM tree with periodic compaction

Peers with different storage backends interoperate freely.

---

## 4. Wire Protocol

### 4.1 Message Types

```
enum SyncMessage {
  // Initiator → Responder
  Initiate {
    pool_cid: CID,
    ranges: Vec<RangeFingerprint>,
  },

  // Responder → Initiator (or vice versa in subsequent rounds)
  Reconcile {
    pool_cid: CID,
    ranges: Vec<RangeResponse>,
  },

  // Either direction
  Items {
    pool_cid: CID,
    thoughts: Vec<ThoughtEnvelope>,
  },

  // Terminal
  Done {
    pool_cid: CID,
  },
}

struct RangeFingerprint {
  upper_bound: Bound,      // exclusive upper bound
  fingerprint: [u8; 16],
}

struct Bound {
  timestamp: u64,          // delta-encoded on wire
  cid_prefix: Vec<u8>,     // truncated to minimum disambiguating length
}

enum RangeResponse {
  // Fingerprints match — range is synced
  Skip,

  // Fingerprints differ — here are sub-ranges
  Split {
    ranges: Vec<RangeFingerprint>,
  },

  // Range is small — here are the actual items
  Items {
    cids: Vec<CID>,
  },
}
```

### 4.2 Bound Encoding (Wire Efficiency)

Bounds are delta-encoded:

```
First bound:  (1000, "4a8a769a1b2c3d4e...")
Second bound: (1002, "351c5e86...")
Third bound:  (1002, "3560d9c4...")
Fourth bound: (1003, "beabef25...")

Wire encoding:
(1000, "")           // full timestamp, no prefix needed (first)
(+2, "")             // delta=2, timestamps differ so no prefix
(+0, "3560")         // delta=0, need prefix to disambiguate from previous
(+1, "")             // delta=1, timestamps differ
```

CID prefixes truncated to minimum length that separates from predecessor.

### 4.3 Frame Size Limits

Optional. If network transport has message limits:

```
struct SyncConfig {
  frame_size_limit: Option<usize>,  // e.g., 64KB
  branching_factor: u8,              // e.g., 16
  item_threshold: u16,               // below this, send items directly
}
```

When frame limit reached, remaining ranges queued for next round.

---

## 5. Protocol Flow

### 5.1 Full Sync

```
Peer A                                    Peer B
------                                    ------
Initiate(pool, [full_range_fp])
                          ──────────────►
                                          Compare fingerprints
                                          Split into sub-ranges
                          ◄──────────────
                                          Reconcile(pool, [range_fps...])
Compare fingerprints
Matching ranges: skip
Non-matching: split or enumerate
Items(pool, [thoughts I have you don't])
Reconcile(pool, [more_ranges...])
                          ──────────────►
                                          ...recurse...
                          ◄──────────────
                                          Items(pool, [thoughts you need])
                                          Done(pool)
Done(pool)
                          ──────────────►
```

### 5.2 Partial Sync (Recent Only)

```
// Sync only thoughts from last 24 hours
Initiate(pool, [
  RangeFingerprint {
    upper_bound: Bound::MAX,
    fingerprint: fp_of_range(now - 24h, MAX),
  }
])
```

Unspecified ranges implicitly skipped.

### 5.3 Incremental Sync

Peers track `last_sync_timestamp` per pool per peer:

```
// Resume from where we left off
Initiate(pool, [
  RangeFingerprint {
    upper_bound: Bound::MAX,
    fingerprint: fp_of_range(last_sync_timestamp, MAX),
  }
])
```

Combined with gossip: "Here's what's new since you last asked."

---

## 6. Integration with Peering

### 6.1 Peering Configuration

```yaml
type: "peer/config"
content:
  peer_identity: <identity_cid>
  pools:
    - pool: <pool_cid>
      direction: "bidirectional"  # or "pull" or "push"
      sync:
        method: "rbsr"
        interval: 300              # seconds between syncs
        partial:
          mode: "recent"
          window: 86400            # 24h in seconds
      bandwidth:
        max_bytes_per_second: 1048576
        burst_allowance: 5242880
  substrates:
    - type: "tcp"
      priority: 1
      endpoints: ["peer.example.com:1729"]
    - type: "quic"
      priority: 2
      endpoints: ["peer.example.com:1729"]
    - type: "sneakernet"
      priority: 99
      export_path: "/mnt/usb/wot-sync"
```

### 6.2 Permission Scoping

RBSR operates within permission boundaries:

1. **Pool membership required:** Only sync pools where both peers have access
2. **Grant-point-forward:** Only sync thoughts created after permission was granted
3. **Schema filtering:** Optional restriction to specific thought types

```
// Sync request includes permission proof
Initiate {
  pool_cid: <pool>,
  permission_proof: <attestation_chain_proving_membership>,
  ranges: [...],
}
```

Responder validates proof before responding.

### 6.3 Trust-Weighted Sync Priority

When bandwidth-constrained, prioritize ranges containing:
- Higher-salience thoughts
- Thoughts from more-trusted identities
- More recent thoughts

Implementation hint: Maintain separate trees for different trust tiers, sync high-trust first.

---

## 7. Attestation Sync

Attestations are thoughts. They sync via the same mechanism.

**Challenge:** An attestation references a target thought. If you receive an attestation before its target, you can't fully validate it.

**Solution:** Dependency ordering in Items messages:

```
Items {
  pool_cid: <pool>,
  thoughts: [
    <target_thought>,      // dependencies first
    <attestation>,         // attestations after their targets
  ],
}
```

Or: Accept attestations for unknown targets, validate when target arrives.

---

## 8. Conflict with Immutability

WoT thoughts are immutable. There are no update conflicts — same CID = same content.

**What can differ:**
- Which thoughts exist (RBSR handles this)
- Attestation counts (extended fingerprint catches this)
- Connection metadata (sync connections separately? or as thoughts?)

**Connections as thoughts:** If connections are separate sync items, they follow same RBSR pattern with their own tree.

---

## 9. Fingerprint Security

### 9.1 Threat Model

Malicious actor inserts crafted thoughts that cause fingerprint collision, preventing legitimate thoughts from syncing.

**Mitigations:**

1. **Count inclusion:** Fingerprint includes item count. Attacker must match count exactly.

2. **Timestamp inclusion:** Fingerprint includes timestamp sum. Harder to craft.

3. **Range randomization:** Implementations MAY randomize split points:
   ```
   split_point = median ± random_offset
   ```
   If attacker's crafted items span a random boundary, attack fails.

4. **Periodic full enumeration:** Occasionally enumerate small ranges fully instead of fingerprinting, catching any masked items.

### 9.2 When to Worry

- Open pools where anyone can post: Higher risk
- Closed pools with trusted members: Lower risk
- Agent swarms with adversarial participants: Higher risk

For high-risk pools, consider ECMH fingerprints (slower but cryptographically secure).

---

## 10. Implementation Checklist

### 10.1 Required

- [ ] SyncItem model (timestamp, cid)
- [ ] Fingerprint function (additive + count + SHA256)
- [ ] Tree storage with cached fingerprints
- [ ] Range query: fingerprint of [lower, upper)
- [ ] Wire protocol: Initiate, Reconcile, Items, Done
- [ ] Bound encoding (delta + prefix truncation)

### 10.2 Recommended

- [ ] Frame size limits
- [ ] Partial sync (time ranges)
- [ ] Incremental sync (resume from last)
- [ ] Permission validation on sync requests
- [ ] Dependency ordering in Items

### 10.3 Optional

- [ ] Extended fingerprint (attestation counts)
- [ ] Trust-weighted prioritization
- [ ] Range randomization (security hardening)
- [ ] ECMH fingerprints (high-security mode)
- [ ] Multiple substrate support

---

## 11. Comparison: RBSR vs Previous Approach

| Aspect | Rotating Bloom | RBSR |
|--------|---------------|------|
| Rounds | 1 (but linear size) | O(log n) rounds, O(d) data |
| False positives | Yes | No |
| Adversarial resistance | Poor | Good (non-rigid) |
| Partial sync | Rebuild filter | Natural (specify ranges) |
| Concurrent modification | Must lock or rebuild | Stateless, always valid |
| Implementation | Simple | Medium |
| Proven scale | Unknown | 10M+ (Nostr/strfry) |

**Recommendation:** RBSR as primary sync method. Bloom filters acceptable for resource-constrained scenarios with trusted peers.

---

## 12. Example: Two Nodes Syncing

```
Node A has: [t=100 cid=aaa], [t=200 cid=bbb], [t=300 cid=ccc]
Node B has: [t=100 cid=aaa], [t=250 cid=ddd], [t=300 cid=ccc]

Round 1:
A → B: Initiate(pool, [{bound=MAX, fp=fp(aaa,bbb,ccc)}])
B: fp(aaa,ddd,ccc) ≠ fp(aaa,bbb,ccc), split at t=200
B → A: Reconcile(pool, [
  {bound=(200,""), fp=fp(aaa)},      // early range
  {bound=MAX, fp=fp(ddd,ccc)}         // late range
])

Round 2:
A: fp(aaa) = fp(aaa) ✓ skip early range
A: fp(bbb,ccc) ≠ fp(ddd,ccc), range is small, enumerate
A → B: Reconcile(pool, [
  Skip,                               // early range confirmed
  Items{cids=[bbb,ccc]}               // late range enumerated
])
A → B: Items(pool, [thought_bbb])     // A has bbb, B doesn't

Round 3:
B: Has ccc, missing bbb (received). Has ddd, A doesn't.
B → A: Items(pool, [thought_ddd])
B → A: Done(pool)

A: Receives ddd, adds to store.
A → B: Done(pool)

Both now have: [aaa, bbb, ccc, ddd]
```

Total: 3 rounds, transferred only the 2 differing thoughts.

---

## 13. References

- Aljoscha Meyer, "Range-Based Set Reconciliation" (arXiv:2212.13567)
- Doug Hoyte, "Negentropy" (github.com/hoytech/negentropy)
- Negentropy Protocol Spec v1
- WoT Spec v0.10 (pool governance, peering concepts)

---

## 14. Open Questions

1. **Connection sync:** Sync connections as separate items or bundled with thoughts?

2. **Blob sync:** Large blobs need chunked transfer. RBSR for blob CID discovery, then separate blob fetch protocol?

3. **Cross-pool references:** Thought in Pool A references thought in Pool B. Sync Pool A, discover dangling reference. Trigger Pool B sync? Or leave as "known unknown"?

4. **Revocation propagation:** Rework chains that invalidate thoughts. Sync the rework, then what? Keep invalidated thought? Prune? Flag?

5. **Real-time + batch:** RBSR for batch catchup, gossip for real-time. How do they interleave? Dedupe?
