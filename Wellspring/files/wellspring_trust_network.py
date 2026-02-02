#!/usr/bin/env python3
"""
Dogfood 011: Trust Network Dynamics

5 identities with varying trust relationships:
- A trusts B directly (1.0)
- B trusts C directly (1.0)
- B trusts E directly (0.8)
- C trusts E directly (0.8)
- D is new entrant, granted access by A
- A's trust of E is purely transitive

Shared pool where all operate. E starts selling crypto.
C and D downrate. A's appetite threshold filters E out.

Tests:
- Vouch chains and transitive trust
- Trust degradation from bad behavior
- Appetite-based filtering
- How downrating propagates through network
"""

import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Tuple
from collections import defaultdict

def compute_cid(content: dict) -> str:
    canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return f"baf_{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"

@dataclass
class Thought:
    type: str
    content: dict
    created_by: str
    because: list = field(default_factory=list)
    visibility: Optional[str] = None
    cid: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.cid:
            self.cid = compute_cid({
                "type": self.type,
                "content": self.content,
                "created_by": self.created_by,
                "because": self.because
            })

    def to_dict(self) -> dict:
        d = {
            "cid": self.cid,
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
            "because": self.because,
            "created_at": self.created_at
        }
        if self.visibility:
            d["visibility"] = self.visibility
        return d


class TrustGraph:
    """
    Computes trust scores from attestations.
    Each identity computes trust from THEIR perspective.
    """

    def __init__(self):
        # direct_trust[from_id][to_id] = weight
        self.direct_trust: Dict[str, Dict[str, float]] = defaultdict(dict)
        # vouch decay per hop
        self.decay = 0.8

    def add_trust(self, from_id: str, to_id: str, weight: float):
        """Record a direct trust attestation"""
        self.direct_trust[from_id][to_id] = weight

    def compute_trust(self, viewer: str, target: str, max_hops: int = 3) -> Tuple[float, List[str]]:
        """
        Compute trust score from viewer's perspective.
        Returns (score, path) where path shows how trust was derived.
        """
        if viewer == target:
            return (1.0, [viewer])

        # Direct trust
        if target in self.direct_trust.get(viewer, {}):
            weight = self.direct_trust[viewer][target]
            return (weight, [viewer, target])

        # BFS for transitive trust
        visited = {viewer}
        queue = [(viewer, 1.0, [viewer])]  # (current, accumulated_trust, path)
        best_score = 0.0
        best_path = []

        while queue:
            current, trust_so_far, path = queue.pop(0)

            if len(path) > max_hops + 1:
                continue

            for next_id, weight in self.direct_trust.get(current, {}).items():
                if next_id in visited:
                    continue

                new_trust = trust_so_far * weight * self.decay
                new_path = path + [next_id]

                if next_id == target:
                    if new_trust > best_score:
                        best_score = new_trust
                        best_path = new_path
                else:
                    visited.add(next_id)
                    queue.append((next_id, new_trust, new_path))

        return (best_score, best_path)


class Identity:
    """Represents one identity with their own trust view and config"""

    def __init__(self, name: str, trust_graph: TrustGraph):
        self.name = name
        self.trust_graph = trust_graph
        self.thoughts: List[Thought] = []

        # Create identity thought
        self.identity = Thought(
            type="identity",
            content={"name": name, "pubkey": f"{name.lower()}_pubkey"},
            created_by="GENESIS"
        )
        self.thoughts.append(self.identity)
        self.cid = self.identity.cid

        # Create devices pool
        self.devices_pool = Thought(
            type="pool",
            content={"name": f"{name.lower()}-devices", "admin": self.cid},
            created_by=self.cid,
            because=[self.cid]
        )
        self.thoughts.append(self.devices_pool)

        # Default appetite
        self.trust_threshold = 0.3  # minimum trust to surface
        self.index_threshold = 0.5  # minimum trust to auto-index

    def trust(self, other: 'Identity', weight: float) -> Thought:
        """Create trust attestation for another identity"""
        attestation = Thought(
            type="attestation",
            content={
                "aspect_type": "trust",
                "on": other.cid,
                "weight": weight,
                "statement": f"{self.name} trusts {other.name}"
            },
            created_by=self.cid,
            because=[self.cid, other.cid]
        )
        self.thoughts.append(attestation)
        self.trust_graph.add_trust(self.cid, other.cid, weight)
        return attestation

    def get_trust(self, target: 'Identity') -> Tuple[float, List[str]]:
        """Get trust score for target from this identity's perspective"""
        return self.trust_graph.compute_trust(self.cid, target.cid)

    def create_message(self, pool_cid: str, text: str, because: list = None) -> Thought:
        """Create a message in a pool"""
        msg = Thought(
            type="message",
            content={"text": text, "pool": pool_cid},
            created_by=self.cid,
            because=because or [pool_cid],
            visibility=f"pool:{pool_cid}"
        )
        self.thoughts.append(msg)
        return msg

    def would_surface(self, author: 'Identity') -> Tuple[bool, float, str]:
        """Check if this identity would surface content from author"""
        trust, path = self.get_trust(author)
        if trust >= self.index_threshold:
            return (True, trust, f"indexed (trust {trust:.2f} via {' → '.join(path)})")
        elif trust >= self.trust_threshold:
            return (True, trust, f"buffered (trust {trust:.2f} via {' → '.join(path)})")
        else:
            return (False, trust, f"filtered (trust {trust:.2f} < threshold {self.trust_threshold})")


def run_simulation():
    """Run the trust network simulation"""

    print("=" * 70)
    print("DOGFOOD 011: Trust Network Dynamics")
    print("=" * 70)

    all_thoughts = []
    trust_graph = TrustGraph()

    # === PHASE 1: Create identities ===
    print("\n" + "=" * 70)
    print("PHASE 1: Create identities")
    print("=" * 70)

    A = Identity("Alice", trust_graph)
    B = Identity("Bob", trust_graph)
    C = Identity("Carol", trust_graph)
    D = Identity("Dave", trust_graph)
    E = Identity("Eve", trust_graph)

    identities = [A, B, C, D, E]
    for i in identities:
        all_thoughts.extend(i.thoughts)
        print(f"  {i.name}: {i.cid[:20]}...")

    # === PHASE 2: Establish trust relationships ===
    print("\n" + "=" * 70)
    print("PHASE 2: Establish trust relationships")
    print("=" * 70)

    # A trusts B directly
    t1 = A.trust(B, 1.0)
    print(f"  A → B: 1.0 (direct)")
    all_thoughts.append(t1)

    # B trusts C directly
    t2 = B.trust(C, 1.0)
    print(f"  B → C: 1.0 (direct)")
    all_thoughts.append(t2)

    # B trusts E directly (slightly lower)
    t3 = B.trust(E, 0.8)
    print(f"  B → E: 0.8 (direct)")
    all_thoughts.append(t3)

    # C trusts E directly
    t4 = C.trust(E, 0.8)
    print(f"  C → E: 0.8 (direct)")
    all_thoughts.append(t4)

    # A grants D access (trusts D)
    t5 = A.trust(D, 0.7)
    print(f"  A → D: 0.7 (new entrant, granted)")
    all_thoughts.append(t5)

    # D trusts A back (bilateral)
    t6 = D.trust(A, 1.0)
    print(f"  D → A: 1.0 (reciprocal)")
    all_thoughts.append(t6)

    # === PHASE 3: Show initial trust map ===
    print("\n" + "=" * 70)
    print("PHASE 3: Trust map (from A's perspective)")
    print("=" * 70)

    print("\n  A's view of the network:")
    for target in [B, C, D, E]:
        trust, path = A.get_trust(target)
        path_names = []
        for cid in path:
            for i in identities:
                if i.cid == cid:
                    path_names.append(i.name)
                    break
        print(f"    → {target.name}: {trust:.3f} via {' → '.join(path_names)}")

    # === PHASE 4: Create shared pool ===
    print("\n" + "=" * 70)
    print("PHASE 4: Create shared discussion pool")
    print("=" * 70)

    shared_pool = Thought(
        type="pool",
        content={
            "name": "friends-chat",
            "purpose": "Shared discussion",
            "admin": A.cid,
            "visibility": "private"
        },
        created_by=A.cid,
        because=[A.cid]
    )
    all_thoughts.append(shared_pool)
    print(f"  Shared pool: {shared_pool.cid[:20]}...")

    # Everyone joins (simplified - skip bilateral attestation for brevity)
    print(f"  All 5 identities join the pool")

    # === PHASE 5: Normal conversation ===
    print("\n" + "=" * 70)
    print("PHASE 5: Normal conversation")
    print("=" * 70)

    msgs = []

    m1 = A.create_message(shared_pool.cid, "Hey everyone, welcome to the new network!")
    msgs.append(("A", m1))
    print(f"  Alice: {m1.content['text']}")

    m2 = B.create_message(shared_pool.cid, "This is great! Love the decentralized vibe.", [m1.cid])
    msgs.append(("B", m2))
    print(f"  Bob: {m2.content['text']}")

    m3 = C.create_message(shared_pool.cid, "Yeah, the trust chains make sense.", [m2.cid])
    msgs.append(("C", m3))
    print(f"  Carol: {m3.content['text']}")

    m4 = D.create_message(shared_pool.cid, "New here, but glad to be included!", [m3.cid])
    msgs.append(("D", m4))
    print(f"  Dave: {m4.content['text']}")

    m5 = E.create_message(shared_pool.cid, "Hey all! Excited about this platform.", [m4.cid])
    msgs.append(("E", m5))
    print(f"  Eve: {m5.content['text']}")

    for _, m in msgs:
        all_thoughts.append(m)

    # === PHASE 6: E starts selling crypto ===
    print("\n" + "=" * 70)
    print("PHASE 6: Eve starts selling crypto 🚨")
    print("=" * 70)

    spam_msgs = []
    for i in range(5):
        spam = E.create_message(
            shared_pool.cid,
            f"🚀 AMAZING OPPORTUNITY! Buy $SCAMCOIN now! 1000x gains! #{i+1}",
            [shared_pool.cid]
        )
        spam_msgs.append(spam)
        all_thoughts.append(spam)

    print(f"  Eve sends 5 crypto spam messages")

    # === PHASE 7: C and D downrate E ===
    print("\n" + "=" * 70)
    print("PHASE 7: Carol and Dave downrate Eve")
    print("=" * 70)

    # C downrates E
    c_downrate = Thought(
        type="attestation",
        content={
            "aspect_type": "trust",
            "on": E.cid,
            "weight": -0.5,
            "statement": "Spam behavior, downrating",
            "previous_weight": 0.8
        },
        created_by=C.cid,
        because=[C.cid, E.cid, spam_msgs[0].cid]  # grounded in spam
    )
    all_thoughts.append(c_downrate)
    trust_graph.add_trust(C.cid, E.cid, -0.5)
    print(f"  Carol: E dropped from 0.8 → -0.5")

    # D downrates E
    d_downrate = Thought(
        type="attestation",
        content={
            "aspect_type": "trust",
            "on": E.cid,
            "weight": 0.0,
            "statement": "Don't trust crypto shills"
        },
        created_by=D.cid,
        because=[D.cid, E.cid, spam_msgs[0].cid]
    )
    all_thoughts.append(d_downrate)
    trust_graph.add_trust(D.cid, E.cid, 0.0)
    print(f"  Dave: E set to 0.0")

    # B's trust unchanged (maybe they like crypto?)
    print(f"  Bob: still trusts E at 0.8 (hasn't downrated)")

    # === PHASE 8: Updated trust map ===
    print("\n" + "=" * 70)
    print("PHASE 8: Updated trust map (from A's perspective)")
    print("=" * 70)

    print("\n  A's view AFTER downrates:")
    for target in [B, C, D, E]:
        trust, path = A.get_trust(target)
        path_names = []
        for cid in path:
            for i in identities:
                if i.cid == cid:
                    path_names.append(i.name)
                    break
        status = "✓ surfaces" if trust >= A.trust_threshold else "✗ filtered"
        print(f"    → {target.name}: {trust:.3f} via {' → '.join(path_names)} [{status}]")

    # === PHASE 9: Surfacing simulation ===
    print("\n" + "=" * 70)
    print("PHASE 9: What does each identity see?")
    print("=" * 70)

    print("\n  For Eve's crypto spam:")
    for viewer in [A, B, C, D]:
        surfaces, trust, reason = viewer.would_surface(E)
        symbol = "✓" if surfaces else "✗"
        print(f"    {viewer.name}: {symbol} {reason}")

    # === PHASE 10: A's appetite blocks E ===
    print("\n" + "=" * 70)
    print("PHASE 10: A's appetite configuration")
    print("=" * 70)

    # A's appetite aspect
    a_appetite = Thought(
        type="aspect",
        content={
            "aspect_type": "appetite",
            "trust_threshold": 0.3,
            "index_threshold": 0.5,
            "note": "Only surface content from trust > 0.3"
        },
        created_by=A.cid,
        because=[A.cid],
        visibility=f"pool:{A.devices_pool.cid}"
    )
    all_thoughts.append(a_appetite)

    trust_e, path_e = A.get_trust(E)
    print(f"""
  A's configuration:
    trust_threshold: 0.3 (minimum to see)
    index_threshold: 0.5 (minimum to auto-index)

  A's trust for E: {trust_e:.3f}
    (path: A → B → E, decayed through Bob's vouch)

  Result: E's content {"surfaces" if trust_e >= A.trust_threshold else "FILTERED"}
    """)

    # === SUMMARY ===
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"""
Trust network:
  A → B (1.0) → C (1.0)
        ↘
         E (0.8) ← C (was 0.8, now -0.5)
  A → D (0.7, new entrant)

After E spams crypto:
  - C downrates E: 0.8 → -0.5
  - D downrates E: → 0.0
  - B still trusts E: 0.8 (hasn't seen/cared)

A's transitive trust for E:
  - Via B → E: 1.0 × 0.8 × 0.8 = 0.512
  - But A's threshold is 0.3, so E still surfaces for A
  - (In real network, A might weight C's downrate into path computation)

Key insight:
  Transitive trust computes from YOUR direct attestations.
  Others' downrates only affect you if you trust their judgement.
  A trusts B. B still trusts E. So A still has transitive trust for E.

  For E to be filtered from A's view:
    - A would need to directly downrate E, OR
    - B would need to downrate E, OR
    - A's path computation would need to incorporate C's rating

This shows the tension:
  Trust is subjective. Your view depends on YOUR attestations.
  Propagating others' ratings is opt-in via vouch chains.

Total thoughts: {len(all_thoughts)}
    """)

    # Write output
    output_file = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-011-trust-network.jsonl"
    with open(output_file, 'w') as f:
        for thought in all_thoughts:
            f.write(json.dumps(thought.to_dict()) + "\n")

    print(f"Wrote {len(all_thoughts)} thoughts to:")
    print(f"  {output_file}")

    return all_thoughts


if __name__ == "__main__":
    run_simulation()
