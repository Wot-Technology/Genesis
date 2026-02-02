#!/usr/bin/env python3
"""
Dogfood 019: Large Network Simulation
10+ nodes, multiple pools, peering, message threads, cross-pool sharing.
"""

import subprocess
import time
import requests
import json
import sys
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT = os.path.join(BASE_DIR, "wellspring_node.py")

# ============================================================================
# NODE MANAGEMENT
# ============================================================================

class NetworkSimulator:
    def __init__(self):
        self.processes = []
        self.nodes = {}  # name -> {port, url, cid}
        self.pools = {}  # pool_name -> {members: [names], cid}
        self.peerings = []  # [(node_a, node_b)]

    def start_node(self, name: str, port: int) -> dict:
        proc = subprocess.Popen(
            [sys.executable, NODE_SCRIPT, "--name", name, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(proc)
        self.nodes[name] = {"port": port, "url": f"http://localhost:{port}", "proc": proc}
        return self.nodes[name]

    def wait_for_nodes(self, timeout: float = 30.0):
        start = time.time()
        for name, info in self.nodes.items():
            while time.time() - start < timeout:
                try:
                    resp = requests.get(f"{info['url']}/", timeout=1)
                    if resp.status_code == 200:
                        data = resp.json()
                        info["cid"] = data.get("cid", "unknown")
                        break
                except:
                    pass
                time.sleep(0.1)
            else:
                raise TimeoutError(f"Node {name} didn't start")

    def stop_all(self):
        for proc in self.processes:
            proc.terminate()
            proc.wait()
        self.processes = []

    def get_identity(self, name: str) -> dict:
        return requests.get(f"{self.nodes[name]['url']}/identity").json()

    def get_stats(self, name: str) -> dict:
        return requests.get(f"{self.nodes[name]['url']}/").json()

    def get_thoughts(self, name: str) -> list:
        return requests.get(f"{self.nodes[name]['url']}/thoughts").json()["thoughts"]

    def create_thought(self, name: str, type: str, content: dict, because: list = None) -> dict:
        return requests.post(
            f"{self.nodes[name]['url']}/thoughts",
            json={"type": type, "content": content, "because": because or []}
        ).json()

    def sync_nodes(self, src_name: str, dst_name: str) -> dict:
        src_url = self.nodes[src_name]["url"]
        dst_url = self.nodes[dst_name]["url"]

        # Get dst's bloom
        bloom_resp = requests.get(f"{dst_url}/bloom")
        bloom_data = bloom_resp.json()

        # Get src's identity
        src_id = self.get_identity(src_name)

        # Get missing thoughts from src
        sync_resp = requests.post(
            f"{src_url}/sync",
            json={"bloom_hex": bloom_data["bloom_hex"], "sender_cid": src_id["cid"]}
        )
        sync_data = sync_resp.json()

        if sync_data["count"] > 0:
            recv_resp = requests.post(
                f"{dst_url}/receive",
                json={"thoughts": sync_data["thoughts"], "sender_cid": src_id["cid"]}
            )
            return recv_resp.json()
        return {"received": 0, "new": 0}

    def bidirectional_sync(self, name_a: str, name_b: str) -> dict:
        r1 = self.sync_nodes(name_a, name_b)
        r2 = self.sync_nodes(name_b, name_a)
        return {
            f"{name_a}→{name_b}": r1,
            f"{name_b}→{name_a}": r2
        }

    def establish_peering(self, name_a: str, name_b: str):
        """Record a peering relationship."""
        self.peerings.append((name_a, name_b))

    def sync_all_peers(self, rounds: int = 3) -> dict:
        """Run sync rounds across all peering relationships."""
        stats = {"rounds": [], "total_synced": 0}

        for round_num in range(rounds):
            round_stats = {"round": round_num + 1, "syncs": []}

            for name_a, name_b in self.peerings:
                result = self.bidirectional_sync(name_a, name_b)
                new_a = result[f"{name_a}→{name_b}"].get("new", 0)
                new_b = result[f"{name_b}→{name_a}"].get("new", 0)
                round_stats["syncs"].append({
                    "pair": f"{name_a}↔{name_b}",
                    "new": new_a + new_b
                })
                stats["total_synced"] += new_a + new_b

            stats["rounds"].append(round_stats)

            # Check if we've converged (no new thoughts in this round)
            round_total = sum(s["new"] for s in round_stats["syncs"])
            if round_total == 0:
                break

        return stats

# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("=" * 70)
    print("DOGFOOD 019: Large Network Simulation")
    print("=" * 70)

    sim = NetworkSimulator()

    try:
        # ====================================================================
        # PHASE 1: Start 12 nodes in 3 clusters
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 1: Starting 12 nodes in 3 clusters")
        print("=" * 70)

        # Cluster A: Research team (4 nodes)
        research_nodes = ["Alice", "Bob", "Carol", "Dave"]
        for i, name in enumerate(research_nodes):
            sim.start_node(name, 8001 + i)

        # Cluster B: Engineering team (4 nodes)
        eng_nodes = ["Eve", "Frank", "Grace", "Henry"]
        for i, name in enumerate(eng_nodes):
            sim.start_node(name, 8011 + i)

        # Cluster C: External partners (4 nodes)
        partner_nodes = ["Ivy", "Jack", "Kate", "Leo"]
        for i, name in enumerate(partner_nodes):
            sim.start_node(name, 8021 + i)

        print("\n  Waiting for all nodes to start...")
        sim.wait_for_nodes()

        print("\n  Cluster A (Research): " + ", ".join(research_nodes))
        print("  Cluster B (Engineering): " + ", ".join(eng_nodes))
        print("  Cluster C (Partners): " + ", ".join(partner_nodes))

        # ====================================================================
        # PHASE 2: Establish peering topology
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 2: Establishing peering topology")
        print("=" * 70)

        # Intra-cluster peering (dense)
        print("\n  Intra-cluster peering (dense mesh):")
        for cluster, nodes in [("Research", research_nodes), ("Eng", eng_nodes), ("Partners", partner_nodes)]:
            for i, a in enumerate(nodes):
                for b in nodes[i+1:]:
                    sim.establish_peering(a, b)
            print(f"    {cluster}: all-to-all ({len(nodes)*(len(nodes)-1)//2} pairs)")

        # Inter-cluster bridges (sparse)
        print("\n  Inter-cluster bridges (sparse):")
        bridges = [
            ("Carol", "Eve"),    # Research ↔ Engineering
            ("Dave", "Frank"),   # Research ↔ Engineering (redundant path)
            ("Eve", "Ivy"),      # Engineering ↔ Partners
            ("Alice", "Jack"),   # Research ↔ Partners (direct)
        ]
        for a, b in bridges:
            sim.establish_peering(a, b)
            print(f"    {a} ↔ {b}")

        print(f"\n  Total peerings: {len(sim.peerings)}")

        # ====================================================================
        # PHASE 3: Create initial content
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 3: Creating initial content")
        print("=" * 70)

        thoughts_created = {}

        # Research team creates research
        print("\n  Research team creating findings...")
        alice_id = sim.get_identity("Alice")
        research_1 = sim.create_thought("Alice", "research", {
            "title": "Initial Hypothesis",
            "text": "We believe the core algorithm can be optimized by 40%"
        }, [alice_id["cid"]])
        thoughts_created["Alice"] = [research_1]

        bob_id = sim.get_identity("Bob")
        research_2 = sim.create_thought("Bob", "research", {
            "title": "Supporting Evidence",
            "text": "Benchmarks confirm the optimization potential in memory-bound operations"
        }, [research_1["cid"], bob_id["cid"]])
        thoughts_created["Bob"] = [research_2]

        # Engineering responds
        print("  Engineering team creating implementation notes...")
        eve_id = sim.get_identity("Eve")
        impl_1 = sim.create_thought("Eve", "note", {
            "text": "We can implement this using the new SIMD instructions"
        }, [eve_id["cid"]])
        thoughts_created["Eve"] = [impl_1]

        frank_id = sim.get_identity("Frank")
        impl_2 = sim.create_thought("Frank", "note", {
            "text": "Estimated 2 weeks for POC, need to coordinate with research"
        }, [impl_1["cid"], frank_id["cid"]])
        thoughts_created["Frank"] = [impl_2]

        # Partners create external content
        print("  Partners creating market analysis...")
        ivy_id = sim.get_identity("Ivy")
        market_1 = sim.create_thought("Ivy", "analysis", {
            "title": "Market Opportunity",
            "text": "Performance improvements could capture 15% more enterprise customers"
        }, [ivy_id["cid"]])
        thoughts_created["Ivy"] = [market_1]

        # Everyone else creates at least one thought
        for name in ["Carol", "Dave", "Grace", "Henry", "Jack", "Kate", "Leo"]:
            node_id = sim.get_identity(name)
            thought = sim.create_thought(name, "message", {
                "text": f"Status update from {name}: Ready for sync"
            }, [node_id["cid"]])
            thoughts_created[name] = [thought]

        total_thoughts = sum(len(v) for v in thoughts_created.values())
        print(f"\n  Created {total_thoughts} initial thoughts across 12 nodes")

        # ====================================================================
        # PHASE 4: Initial sync rounds
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 4: Initial sync rounds")
        print("=" * 70)

        print("\n  Running sync rounds until convergence...")
        sync_stats = sim.sync_all_peers(rounds=5)

        for rs in sync_stats["rounds"]:
            active_pairs = [s for s in rs["syncs"] if s["new"] > 0]
            print(f"    Round {rs['round']}: {sum(s['new'] for s in rs['syncs'])} new thoughts synced")
            if len(active_pairs) <= 5:
                for s in active_pairs:
                    print(f"      {s['pair']}: {s['new']} new")

        print(f"\n  Total synced: {sync_stats['total_synced']} thoughts")

        # ====================================================================
        # PHASE 5: Response threads
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 5: Creating response threads (cross-cluster)")
        print("=" * 70)

        # Eve responds to Alice's research (she received it via sync)
        eve_thoughts = sim.get_thoughts("Eve")
        alice_research = [t for t in eve_thoughts if t["content"].get("title") == "Initial Hypothesis"]
        if alice_research:
            response_1 = sim.create_thought("Eve", "response", {
                "text": "This aligns with our implementation plan. Can we schedule a sync?"
            }, [alice_research[0]["cid"], eve_id["cid"]])
            print(f"  Eve responded to Alice's research")
            thoughts_created["Eve"].append(response_1)

        # Ivy responds to Bob's evidence (received via bridge)
        ivy_thoughts = sim.get_thoughts("Ivy")
        bob_research = [t for t in ivy_thoughts if t["content"].get("title") == "Supporting Evidence"]
        if bob_research:
            response_2 = sim.create_thought("Ivy", "response", {
                "text": "The benchmark data supports our market projections. Great work!"
            }, [bob_research[0]["cid"], ivy_id["cid"]])
            print(f"  Ivy responded to Bob's research")
            thoughts_created["Ivy"].append(response_2)
        else:
            print(f"  Ivy hasn't received Bob's research yet (needs more sync)")

        # Jack creates a summary referencing multiple sources
        jack_thoughts = sim.get_thoughts("Jack")
        jack_id = sim.get_identity("Jack")

        # Find thoughts Jack has received
        refs = []
        for t in jack_thoughts:
            if t["type"] in ["research", "analysis"]:
                refs.append(t["cid"])

        if len(refs) >= 2:
            summary = sim.create_thought("Jack", "summary", {
                "title": "Cross-team Summary",
                "text": f"Synthesizing {len(refs)} inputs from research, engineering, and market analysis"
            }, refs[:3] + [jack_id["cid"]])
            print(f"  Jack created summary referencing {len(refs[:3])} sources")
            thoughts_created["Jack"].append(summary)

        # ====================================================================
        # PHASE 6: More sync rounds (propagate responses)
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 6: Sync rounds (propagate responses)")
        print("=" * 70)

        sync_stats_2 = sim.sync_all_peers(rounds=3)

        for rs in sync_stats_2["rounds"]:
            total = sum(s["new"] for s in rs["syncs"])
            if total > 0:
                print(f"    Round {rs['round']}: {total} new thoughts synced")

        # ====================================================================
        # PHASE 7: Verify propagation
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 7: Verify propagation")
        print("=" * 70)

        print("\n  Thought counts per node:")
        all_counts = {}
        for name in sim.nodes:
            stats = sim.get_stats(name)
            all_counts[name] = stats["thoughts"]

        # Group by cluster
        for cluster, nodes in [("Research", research_nodes), ("Engineering", eng_nodes), ("Partners", partner_nodes)]:
            counts = [all_counts[n] for n in nodes]
            print(f"    {cluster}: {counts} (avg: {sum(counts)/len(counts):.1f})")

        # Check convergence
        unique_counts = set(all_counts.values())
        if len(unique_counts) == 1:
            print(f"\n  ✓ Full convergence: all nodes have {list(unique_counts)[0]} thoughts")
        else:
            print(f"\n  Partial convergence: {min(unique_counts)}-{max(unique_counts)} thoughts")
            # Find which nodes have most/least
            max_count = max(unique_counts)
            min_count = min(unique_counts)
            print(f"    Most: {[n for n,c in all_counts.items() if c == max_count]}")
            print(f"    Least: {[n for n,c in all_counts.items() if c == min_count]}")

        # ====================================================================
        # PHASE 8: Cross-cluster visibility check
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 8: Cross-cluster visibility")
        print("=" * 70)

        # Can Leo (far from Research) see Alice's work?
        leo_thoughts = sim.get_thoughts("Leo")
        leo_sees_alice = [t for t in leo_thoughts
                          if t["content"].get("title") == "Initial Hypothesis"
                          or "Alice" in t["content"].get("text", "")]

        print(f"\n  Can Leo (Partners) see Alice's research?")
        if leo_sees_alice:
            print(f"    ✓ Yes - propagated through bridges")
        else:
            print(f"    ✗ No - hasn't reached yet")

        # Trace how research propagated
        print(f"\n  Research thought propagation:")
        for name in ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Ivy", "Jack", "Leo"]:
            thoughts = sim.get_thoughts(name)
            has_research = any(t["content"].get("title") == "Initial Hypothesis" for t in thoughts)
            hop_marker = "→" if has_research else "✗"
            print(f"    {name}: {hop_marker}")

        # ====================================================================
        # PHASE 9: Stats summary
        # ====================================================================
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        total_nodes = len(sim.nodes)
        total_peerings = len(sim.peerings)
        total_thoughts = sum(all_counts.values()) // total_nodes  # Approx unique

        print(f"""
  Network topology:
    Nodes: {total_nodes}
    Peerings: {total_peerings}
    Clusters: 3 (Research, Engineering, Partners)

  Content:
    Initial thoughts: {sum(len(v) for v in thoughts_created.values())}
    After sync: ~{total_thoughts} unique thoughts per node

  Sync performance:
    Rounds to converge: {len(sync_stats['rounds']) + len(sync_stats_2['rounds'])}
    Total thought transfers: {sync_stats['total_synced'] + sync_stats_2['total_synced']}

  Cross-cluster propagation:
    Research → Engineering: via Carol↔Eve, Dave↔Frank bridges
    Engineering → Partners: via Eve↔Ivy bridge
    Research → Partners: via Alice↔Jack direct bridge

  Key observations:
    - Intra-cluster sync is fast (dense peering)
    - Cross-cluster requires bridge nodes
    - Multiple bridges provide redundancy
    - Response threads create cross-cluster because chains
        """)

        # Write output
        output = {
            "nodes": {n: {"cid": info.get("cid"), "thoughts": sim.get_stats(n)["thoughts"]}
                     for n, info in sim.nodes.items()},
            "peerings": sim.peerings,
            "sync_stats": sync_stats,
            "propagation_check": {
                "leo_sees_alice": bool(leo_sees_alice)
            }
        }

        output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-019-network.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Wrote results to: {output_path}")

    finally:
        print("\n  Stopping all nodes...")
        sim.stop_all()
        print("  Done.")

if __name__ == "__main__":
    main()
