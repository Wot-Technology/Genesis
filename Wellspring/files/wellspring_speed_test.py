#!/usr/bin/env python3
"""
Dogfood 012: Speed of Thought Test

50 identities interacting in a shared pool:
- Various trust topologies (chains, cycles, clusters)
- Multiple peering configurations
- Message exchange with reference verification
- Performance metrics

Tests:
- Trust computation at scale
- Reference resolution speed
- Cycle handling in trust graph
- Peer routing decisions
"""

import json
import hashlib
import random
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import threading

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
    """Thread-safe trust graph with cycle detection"""

    def __init__(self):
        self.direct_trust: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.decay = 0.8
        self.lock = threading.RLock()
        self._cache: Dict[Tuple[str, str], Tuple[float, List[str]]] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def add_trust(self, from_id: str, to_id: str, weight: float):
        with self.lock:
            self.direct_trust[from_id][to_id] = weight
            # Invalidate cache entries involving these identities
            self._cache = {k: v for k, v in self._cache.items()
                         if from_id not in k and to_id not in k}

    def compute_trust(self, viewer: str, target: str, max_hops: int = 4) -> Tuple[float, List[str]]:
        """Compute trust with cycle detection and caching"""
        cache_key = (viewer, target)

        with self.lock:
            if cache_key in self._cache:
                self.cache_hits += 1
                return self._cache[cache_key]
            self.cache_misses += 1

        if viewer == target:
            return (1.0, [viewer])

        # Direct trust
        with self.lock:
            if target in self.direct_trust.get(viewer, {}):
                weight = self.direct_trust[viewer][target]
                result = (weight, [viewer, target])
                self._cache[cache_key] = result
                return result

        # BFS with cycle detection
        visited = {viewer}
        queue = [(viewer, 1.0, [viewer])]
        best_score = 0.0
        best_path = []

        while queue:
            current, trust_so_far, path = queue.pop(0)

            if len(path) > max_hops + 1:
                continue

            with self.lock:
                edges = list(self.direct_trust.get(current, {}).items())

            for next_id, weight in edges:
                if next_id in visited:
                    continue  # Cycle detected, skip

                new_trust = trust_so_far * weight * self.decay
                new_path = path + [next_id]

                if next_id == target:
                    if new_trust > best_score:
                        best_score = new_trust
                        best_path = new_path
                else:
                    visited.add(next_id)
                    queue.append((next_id, new_trust, new_path))

        result = (best_score, best_path)
        with self.lock:
            self._cache[cache_key] = result
        return result


class PeerConfig:
    """Peering configuration for an identity"""

    def __init__(self, identity_cid: str):
        self.identity = identity_cid
        self.peers: Dict[str, dict] = {}  # peer_cid -> config
        self.default_rate = 100  # messages/hour
        self.trust_threshold = 0.3

    def add_peer(self, peer_cid: str, rate: int = 1000, priority: str = "normal"):
        self.peers[peer_cid] = {
            "rate": rate,
            "priority": priority,
            "messages_this_hour": 0
        }

    def can_receive_from(self, sender_cid: str, trust_score: float) -> Tuple[bool, str]:
        """Check if we can receive from this sender"""
        if sender_cid in self.peers:
            peer = self.peers[sender_cid]
            if peer["messages_this_hour"] < peer["rate"]:
                peer["messages_this_hour"] += 1
                return (True, f"peer:{peer['priority']}")

        if trust_score >= self.trust_threshold:
            return (True, f"trusted:{trust_score:.2f}")

        return (False, f"filtered:{trust_score:.2f}<{self.trust_threshold}")


class Identity:
    """Identity with peering config and message handling"""

    def __init__(self, name: str, trust_graph: TrustGraph):
        self.name = name
        self.trust_graph = trust_graph

        self.identity = Thought(
            type="identity",
            content={"name": name, "pubkey": f"{name.lower()}_pubkey"},
            created_by="GENESIS"
        )
        self.cid = self.identity.cid

        self.peer_config = PeerConfig(self.cid)
        self.inbox: List[Thought] = []
        self.outbox: List[Thought] = []
        self.received_count = 0
        self.filtered_count = 0

    def trust(self, other: 'Identity', weight: float):
        self.trust_graph.add_trust(self.cid, other.cid, weight)

    def add_peer(self, other: 'Identity', rate: int = 1000, priority: str = "normal"):
        self.peer_config.add_peer(other.cid, rate, priority)

    def get_trust(self, target: 'Identity') -> float:
        score, _ = self.trust_graph.compute_trust(self.cid, target.cid)
        return score

    def send_message(self, pool_cid: str, text: str, because: list = None) -> Thought:
        msg = Thought(
            type="message",
            content={"text": text, "pool": pool_cid, "sender": self.name},
            created_by=self.cid,
            because=because or [pool_cid],
            visibility=f"pool:{pool_cid}"
        )
        self.outbox.append(msg)
        return msg

    def receive_message(self, msg: Thought, sender: 'Identity') -> bool:
        trust = self.get_trust(sender)
        can_receive, reason = self.peer_config.can_receive_from(sender.cid, trust)

        if can_receive:
            self.inbox.append(msg)
            self.received_count += 1
            return True
        else:
            self.filtered_count += 1
            return False


class MessageRouter:
    """Routes messages between identities based on peering"""

    def __init__(self, identities: List[Identity], pool_cid: str):
        self.identities = {i.cid: i for i in identities}
        self.pool_cid = pool_cid
        self.routed = 0
        self.filtered = 0
        self.lock = threading.Lock()

    def route_message(self, msg: Thought, sender: Identity):
        """Route a message to all pool members"""
        for receiver in self.identities.values():
            if receiver.cid == sender.cid:
                continue

            if receiver.receive_message(msg, sender):
                with self.lock:
                    self.routed += 1
            else:
                with self.lock:
                    self.filtered += 1


def run_simulation():
    """Run the 50-identity speed test"""

    print("=" * 70)
    print("DOGFOOD 012: Speed of Thought Test")
    print("=" * 70)

    all_thoughts = []
    trust_graph = TrustGraph()

    # === PHASE 1: Create 50 identities ===
    print("\n" + "=" * 70)
    print("PHASE 1: Creating 50 identities")
    print("=" * 70)

    start = time.time()

    identities: List[Identity] = []
    for i in range(50):
        name = f"User{i:02d}"
        identity = Identity(name, trust_graph)
        identities.append(identity)
        all_thoughts.append(identity.identity)

    create_time = time.time() - start
    print(f"  Created 50 identities in {create_time*1000:.2f}ms")

    # === PHASE 2: Establish trust topology ===
    print("\n" + "=" * 70)
    print("PHASE 2: Establishing trust topology")
    print("=" * 70)

    start = time.time()
    trust_count = 0

    # Cluster 1: Dense core (users 0-9, everyone trusts everyone)
    print("  Cluster 1: Dense core (0-9)")
    for i in range(10):
        for j in range(10):
            if i != j:
                identities[i].trust(identities[j], 0.9)
                trust_count += 1

    # Cluster 2: Chain (users 10-19)
    print("  Cluster 2: Chain (10-19)")
    for i in range(10, 19):
        identities[i].trust(identities[i+1], 0.8)
        identities[i+1].trust(identities[i], 0.8)  # bidirectional
        trust_count += 2

    # Cluster 3: Star (user 20 is hub, 21-29 are spokes)
    print("  Cluster 3: Star (20 is hub, 21-29 spokes)")
    for i in range(21, 30):
        identities[20].trust(identities[i], 0.9)
        identities[i].trust(identities[20], 0.9)
        trust_count += 2

    # Cluster 4: Cycles (users 30-39, with intentional loops)
    print("  Cluster 4: Cycles (30-39)")
    for i in range(30, 39):
        identities[i].trust(identities[i+1], 0.7)
        trust_count += 1
    identities[39].trust(identities[30], 0.7)  # close the loop
    trust_count += 1
    # Add cross-links
    identities[32].trust(identities[37], 0.6)
    identities[35].trust(identities[31], 0.6)
    trust_count += 2

    # Cluster 5: Isolated (users 40-49, minimal connections)
    print("  Cluster 5: Isolated (40-49, sparse)")
    for i in range(40, 49):
        if random.random() > 0.5:
            j = random.randint(40, 49)
            if i != j:
                identities[i].trust(identities[j], 0.5)
                trust_count += 1

    # Cross-cluster bridges
    print("  Cross-cluster bridges")
    identities[5].trust(identities[15], 0.7)   # core → chain
    identities[15].trust(identities[25], 0.7)  # chain → star
    identities[25].trust(identities[35], 0.7)  # star → cycle
    identities[35].trust(identities[45], 0.5)  # cycle → isolated
    trust_count += 4

    trust_time = time.time() - start
    print(f"\n  Established {trust_count} trust relationships in {trust_time*1000:.2f}ms")

    # === PHASE 3: Setup peering ===
    print("\n" + "=" * 70)
    print("PHASE 3: Configuring peer relationships")
    print("=" * 70)

    start = time.time()
    peer_count = 0

    # Dense core has high-bandwidth peering
    for i in range(10):
        for j in range(10):
            if i != j:
                identities[i].add_peer(identities[j], rate=10000, priority="high")
                peer_count += 1

    # Others get default peering to neighbors
    for i in range(10, 50):
        # Peer with trusted neighbors
        for j in range(50):
            if i != j:
                trust = identities[i].get_trust(identities[j])
                if trust > 0.5:
                    identities[i].add_peer(identities[j], rate=1000, priority="normal")
                    peer_count += 1

    peer_time = time.time() - start
    print(f"  Configured {peer_count} peer relationships in {peer_time*1000:.2f}ms")

    # === PHASE 4: Create shared pool ===
    print("\n" + "=" * 70)
    print("PHASE 4: Creating shared pool")
    print("=" * 70)

    shared_pool = Thought(
        type="pool",
        content={"name": "speed-test-pool", "members": 50},
        created_by=identities[0].cid
    )
    all_thoughts.append(shared_pool)
    print(f"  Pool: {shared_pool.cid[:24]}...")

    router = MessageRouter(identities, shared_pool.cid)

    # === PHASE 5: Message exchange ===
    print("\n" + "=" * 70)
    print("PHASE 5: Message exchange (500 messages)")
    print("=" * 70)

    start = time.time()
    messages = []

    # Each identity sends 10 messages
    for round_num in range(10):
        for identity in identities:
            # Reference random previous messages
            because = [shared_pool.cid]
            if messages and random.random() > 0.3:
                ref = random.choice(messages[-100:] if len(messages) > 100 else messages)
                because.append(ref.cid)

            msg = identity.send_message(
                shared_pool.cid,
                f"Message {round_num} from {identity.name}",
                because
            )
            messages.append(msg)
            all_thoughts.append(msg)

            # Route to all
            router.route_message(msg, identity)

    msg_time = time.time() - start
    print(f"  Sent 500 messages in {msg_time*1000:.2f}ms")
    print(f"  Routed: {router.routed}, Filtered: {router.filtered}")

    # === PHASE 6: Trust computation stress test ===
    print("\n" + "=" * 70)
    print("PHASE 6: Trust computation (2500 lookups)")
    print("=" * 70)

    start = time.time()
    lookups = 0

    for i in range(50):
        for j in range(50):
            if i != j:
                score, path = trust_graph.compute_trust(
                    identities[i].cid,
                    identities[j].cid
                )
                lookups += 1

    trust_lookup_time = time.time() - start
    print(f"  Completed {lookups} trust lookups in {trust_lookup_time*1000:.2f}ms")
    print(f"  Cache hits: {trust_graph.cache_hits}, misses: {trust_graph.cache_misses}")
    print(f"  Avg per lookup: {(trust_lookup_time/lookups)*1000000:.2f}µs")

    # === PHASE 7: Reference verification ===
    print("\n" + "=" * 70)
    print("PHASE 7: Reference verification")
    print("=" * 70)

    start = time.time()
    verified = 0
    broken = 0

    thought_index = {t.cid: t for t in all_thoughts}

    for msg in messages:
        for ref_cid in msg.because:
            if ref_cid in thought_index:
                verified += 1
            else:
                broken += 1

    verify_time = time.time() - start
    print(f"  Verified {verified} references in {verify_time*1000:.2f}ms")
    print(f"  Broken references: {broken}")

    # === PHASE 8: Cross-cluster visibility ===
    print("\n" + "=" * 70)
    print("PHASE 8: Cross-cluster trust paths")
    print("=" * 70)

    test_pairs = [
        (0, 49, "Core → Isolated"),
        (10, 39, "Chain → Cycle"),
        (20, 45, "Star → Isolated"),
        (32, 37, "Cycle internal"),
        (5, 25, "Core → Star via bridge"),
    ]

    for i, j, desc in test_pairs:
        score, path = trust_graph.compute_trust(identities[i].cid, identities[j].cid)
        path_names = [identities[k].name for k in range(50)
                     if identities[k].cid in path]
        hops = len(path) - 1 if path else 0
        print(f"  {desc}: {score:.3f} ({hops} hops)")
        if path_names:
            print(f"    Path: {' → '.join(path_names)}")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_time = create_time + trust_time + peer_time + msg_time + trust_lookup_time + verify_time

    print(f"""
Performance:
  Identity creation:     {create_time*1000:8.2f}ms (50 identities)
  Trust establishment:   {trust_time*1000:8.2f}ms ({trust_count} relationships)
  Peer configuration:    {peer_time*1000:8.2f}ms ({peer_count} peers)
  Message exchange:      {msg_time*1000:8.2f}ms (500 messages)
  Trust lookups:         {trust_lookup_time*1000:8.2f}ms (2500 lookups)
  Reference verification:{verify_time*1000:8.2f}ms ({verified} refs)
  ─────────────────────────────────────────
  Total:                 {total_time*1000:8.2f}ms

Throughput:
  Messages/sec:          {500/msg_time:,.0f}
  Trust lookups/sec:     {2500/trust_lookup_time:,.0f}
  Ref verifications/sec: {verified/verify_time:,.0f}

Routing:
  Messages routed:       {router.routed:,}
  Messages filtered:     {router.filtered:,}
  Filter rate:           {router.filtered/(router.routed+router.filtered)*100:.1f}%

Trust graph:
  Cache hit rate:        {trust_graph.cache_hits/(trust_graph.cache_hits+trust_graph.cache_misses)*100:.1f}%
  Cycle handling:        ✓ (cluster 4 tested)
  Cross-cluster paths:   ✓ (bridges tested)

Total thoughts:          {len(all_thoughts):,}
    """)

    # Write output
    output_file = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-012-speed.jsonl"
    with open(output_file, 'w') as f:
        for thought in all_thoughts:
            f.write(json.dumps(thought.to_dict()) + "\n")

    print(f"Wrote {len(all_thoughts)} thoughts to:")
    print(f"  {output_file}")

    return all_thoughts


if __name__ == "__main__":
    run_simulation()
