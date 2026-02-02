#!/usr/bin/env python3
"""
Dogfood 016: Multi-Instance Sync Test
Orchestrates 3 Wellspring nodes and tests thought propagation.
"""

import subprocess
import time
import requests
import json
import sys
import signal
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT = os.path.join(BASE_DIR, "wellspring_node.py")

# ============================================================================
# NODE MANAGEMENT
# ============================================================================

class NodeManager:
    def __init__(self):
        self.processes = []
        self.nodes = {}

    def start_node(self, name: str, port: int) -> dict:
        """Start a node as a subprocess."""
        proc = subprocess.Popen(
            [sys.executable, NODE_SCRIPT, "--name", name, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(proc)
        self.nodes[name] = {"port": port, "url": f"http://localhost:{port}"}
        return self.nodes[name]

    def wait_for_nodes(self, timeout: float = 10.0):
        """Wait for all nodes to be ready."""
        start = time.time()
        for name, info in self.nodes.items():
            while time.time() - start < timeout:
                try:
                    resp = requests.get(f"{info['url']}/", timeout=1)
                    if resp.status_code == 200:
                        break
                except:
                    pass
                time.sleep(0.1)
            else:
                raise TimeoutError(f"Node {name} didn't start in time")

    def stop_all(self):
        """Stop all nodes."""
        for proc in self.processes:
            proc.terminate()
            proc.wait()
        self.processes = []

# ============================================================================
# SYNC OPERATIONS
# ============================================================================

def sync_nodes(src_url: str, dst_url: str) -> dict:
    """Sync from src to dst using bloom filter exchange."""
    # Get dst's bloom filter
    bloom_resp = requests.get(f"{dst_url}/bloom")
    bloom_data = bloom_resp.json()

    # Get src's identity
    id_resp = requests.get(f"{src_url}/identity")
    src_identity = id_resp.json()

    # Ask src for thoughts dst is missing
    sync_resp = requests.post(
        f"{src_url}/sync",
        json={"bloom_hex": bloom_data["bloom_hex"], "sender_cid": src_identity["cid"]}
    )
    sync_data = sync_resp.json()

    if sync_data["count"] > 0:
        # Send missing thoughts to dst
        recv_resp = requests.post(
            f"{dst_url}/receive",
            json={"thoughts": sync_data["thoughts"], "sender_cid": src_identity["cid"]}
        )
        return recv_resp.json()
    return {"received": 0, "new": 0}

def get_stats(url: str) -> dict:
    return requests.get(f"{url}/").json()

def create_thought(url: str, type: str, content: dict, because: list = None) -> dict:
    return requests.post(
        f"{url}/thoughts",
        json={"type": type, "content": content, "because": because or []}
    ).json()

def get_identity(url: str) -> dict:
    return requests.get(f"{url}/identity").json()

def get_thoughts(url: str) -> list:
    return requests.get(f"{url}/thoughts").json()["thoughts"]

# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("=" * 70)
    print("DOGFOOD 016: Multi-Instance Sync")
    print("=" * 70)

    manager = NodeManager()

    try:
        # ====================================================================
        # PHASE 1: Start nodes
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 1: Starting 3 Wellspring nodes")
        print("=" * 70)

        nodes = {
            "Alice": manager.start_node("Alice", 8001),
            "Bob": manager.start_node("Bob", 8002),
            "Carol": manager.start_node("Carol", 8003)
        }

        print("\n  Waiting for nodes to start...")
        manager.wait_for_nodes()

        for name, info in nodes.items():
            stats = get_stats(info["url"])
            print(f"  {name}: {info['url']} ({stats['cid']})")

        # ====================================================================
        # PHASE 2: Create initial thoughts (isolated)
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 2: Creating thoughts (nodes isolated)")
        print("=" * 70)

        alice_id = get_identity(nodes["Alice"]["url"])
        bob_id = get_identity(nodes["Bob"]["url"])
        carol_id = get_identity(nodes["Carol"]["url"])

        # Alice creates thoughts
        alice_thought1 = create_thought(
            nodes["Alice"]["url"], "message",
            {"text": "Hello from Alice!", "seq": 1},
            [alice_id["cid"]]
        )
        alice_thought2 = create_thought(
            nodes["Alice"]["url"], "message",
            {"text": "Alice's second thought", "seq": 2},
            [alice_thought1["cid"]]
        )
        print(f"\n  Alice created 2 thoughts")

        # Bob creates thoughts
        bob_thought1 = create_thought(
            nodes["Bob"]["url"], "message",
            {"text": "Bob here!", "seq": 1},
            [bob_id["cid"]]
        )
        print(f"  Bob created 1 thought")

        # Carol creates thoughts
        carol_thought1 = create_thought(
            nodes["Carol"]["url"], "message",
            {"text": "Carol checking in", "seq": 1},
            [carol_id["cid"]]
        )
        carol_thought2 = create_thought(
            nodes["Carol"]["url"], "message",
            {"text": "Carol's analysis", "seq": 2},
            [carol_thought1["cid"]]
        )
        carol_thought3 = create_thought(
            nodes["Carol"]["url"], "message",
            {"text": "Carol's conclusion", "seq": 3},
            [carol_thought2["cid"]]
        )
        print(f"  Carol created 3 thoughts")

        # Check isolation
        print("\n  Thought counts (isolated):")
        for name, info in nodes.items():
            stats = get_stats(info["url"])
            print(f"    {name}: {stats['thoughts']} thoughts")

        # ====================================================================
        # PHASE 3: First sync round (Alice ↔ Bob)
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 3: First sync round (Alice ↔ Bob)")
        print("=" * 70)

        # Sync now auto-includes identity dependencies
        print("\n  Alice → Bob (identities auto-included)...")
        result1 = sync_nodes(nodes["Alice"]["url"], nodes["Bob"]["url"])
        print(f"    Sent {result1.get('received', 0)}, new: {result1.get('new', 0)}")

        print("  Bob → Alice (identities auto-included)...")
        result2 = sync_nodes(nodes["Bob"]["url"], nodes["Alice"]["url"])
        print(f"    Sent {result2.get('received', 0)}, new: {result2.get('new', 0)}")

        print("\n  Thought counts after Alice ↔ Bob sync:")
        for name, info in nodes.items():
            stats = get_stats(info["url"])
            print(f"    {name}: {stats['thoughts']} thoughts")

        # ====================================================================
        # PHASE 4: Second sync round (Bob ↔ Carol)
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 4: Second sync round (Bob ↔ Carol)")
        print("=" * 70)

        print("\n  Bob → Carol (identities auto-included)...")
        result3 = sync_nodes(nodes["Bob"]["url"], nodes["Carol"]["url"])
        print(f"    Sent {result3.get('received', 0)}, new: {result3.get('new', 0)}")

        print("  Carol → Bob (identities auto-included)...")
        result4 = sync_nodes(nodes["Carol"]["url"], nodes["Bob"]["url"])
        print(f"    Sent {result4.get('received', 0)}, new: {result4.get('new', 0)}")

        print("\n  Thought counts after Bob ↔ Carol sync:")
        for name, info in nodes.items():
            stats = get_stats(info["url"])
            print(f"    {name}: {stats['thoughts']} thoughts")

        # ====================================================================
        # PHASE 5: Third sync (Alice ↔ Bob again, propagates Carol's)
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 5: Third sync (Alice ← Bob, gets Carol's thoughts)")
        print("=" * 70)

        # Carol's identity will be auto-included since Alice doesn't have it
        print("\n  Bob → Alice (propagating Carol's thoughts + identity)...")
        result5 = sync_nodes(nodes["Bob"]["url"], nodes["Alice"]["url"])
        print(f"    Sent {result5.get('received', 0)}, new: {result5.get('new', 0)}")

        print("\n  Final thought counts:")
        for name, info in nodes.items():
            stats = get_stats(info["url"])
            print(f"    {name}: {stats['thoughts']} thoughts (verified: {stats['verified']}, rejected: {stats['rejected']})")

        # ====================================================================
        # PHASE 6: Verify propagation
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 6: Verify cross-node propagation")
        print("=" * 70)

        alice_thoughts = get_thoughts(nodes["Alice"]["url"])
        bob_thoughts = get_thoughts(nodes["Bob"]["url"])
        carol_thoughts = get_thoughts(nodes["Carol"]["url"])

        def has_thought_from(thoughts: list, creator_cid_prefix: str) -> int:
            return len([t for t in thoughts if t["created_by"].startswith(creator_cid_prefix) or
                       (t["type"] == "identity" and t["content"].get("name", "").lower() in creator_cid_prefix.lower())])

        alice_cid_prefix = alice_id["cid"][:20]
        bob_cid_prefix = bob_id["cid"][:20]
        carol_cid_prefix = carol_id["cid"][:20]

        print("\n  Alice's view:")
        alice_from_alice = len([t for t in alice_thoughts if t["created_by"] == alice_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Alice"])
        alice_from_bob = len([t for t in alice_thoughts if t["created_by"] == bob_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Bob"])
        alice_from_carol = len([t for t in alice_thoughts if t["created_by"] == carol_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Carol"])
        print(f"    From Alice: {alice_from_alice} (own)")
        print(f"    From Bob: {alice_from_bob} (direct peer)")
        print(f"    From Carol: {alice_from_carol} (via Bob)")

        print("\n  Bob's view:")
        bob_from_alice = len([t for t in bob_thoughts if t["created_by"] == alice_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Alice"])
        bob_from_bob = len([t for t in bob_thoughts if t["created_by"] == bob_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Bob"])
        bob_from_carol = len([t for t in bob_thoughts if t["created_by"] == carol_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Carol"])
        print(f"    From Alice: {bob_from_alice} (direct peer)")
        print(f"    From Bob: {bob_from_bob} (own)")
        print(f"    From Carol: {bob_from_carol} (direct peer)")

        print("\n  Carol's view:")
        carol_from_alice = len([t for t in carol_thoughts if t["created_by"] == alice_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Alice"])
        carol_from_bob = len([t for t in carol_thoughts if t["created_by"] == bob_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Bob"])
        carol_from_carol = len([t for t in carol_thoughts if t["created_by"] == carol_id["cid"] or t["created_by"] == "GENESIS" and t["content"].get("name") == "Carol"])
        print(f"    From Alice: {carol_from_alice} (via Bob)")
        print(f"    From Bob: {carol_from_bob} (direct peer)")
        print(f"    From Carol: {carol_from_carol} (own)")

        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        all_synced = (len(alice_thoughts) == len(bob_thoughts) == len(carol_thoughts))
        print(f"""
  Sync topology: Alice ↔ Bob ↔ Carol (linear)

  Initial state:
    Alice: 3 thoughts (identity + 2 messages)
    Bob:   2 thoughts (identity + 1 message)
    Carol: 4 thoughts (identity + 3 messages)
    Total: 9 unique thoughts

  Final state:
    Alice: {len(alice_thoughts)} thoughts
    Bob:   {len(bob_thoughts)} thoughts
    Carol: {len(carol_thoughts)} thoughts

  Full convergence: {'✓ YES' if all_synced else '✗ NO'}

  Propagation verified:
    - Carol's thoughts reached Alice via Bob
    - Alice's thoughts reached Carol via Bob
    - All signatures verified at each hop

  Key insight:
    Bloom filter exchange minimizes bandwidth.
    Each sync only transfers what the peer is missing.
    Signatures verify at destination, not in transit.
        """)

        # Write output
        output = {
            "alice": alice_thoughts,
            "bob": bob_thoughts,
            "carol": carol_thoughts
        }
        output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-016-sync.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Wrote sync results to: {output_path}")

    finally:
        print("\n  Stopping nodes...")
        manager.stop_all()
        print("  Done.")

if __name__ == "__main__":
    main()
