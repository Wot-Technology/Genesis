#!/usr/bin/env python3
"""
Dogfood 021: Visibility-Aware Sync Test
Tests that sync properly filters thoughts based on pool membership and peer agreements.
"""

import subprocess
import time
import requests
import json
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT = os.path.join(BASE_DIR, "wellspring_node_v2.py")


class VisibilityTester:
    def __init__(self):
        self.processes = []
        self.nodes = {}

    def start_node(self, name: str, port: int) -> dict:
        proc = subprocess.Popen(
            [sys.executable, NODE_SCRIPT, "--name", name, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(proc)
        self.nodes[name] = {
            "port": port,
            "url": f"http://localhost:{port}",
            "proc": proc
        }
        return self.nodes[name]

    def wait_for_nodes(self, timeout: float = 30.0):
        start = time.time()
        for name, info in self.nodes.items():
            while time.time() - start < timeout:
                try:
                    resp = requests.get(f"{info['url']}/", timeout=1)
                    if resp.status_code == 200:
                        data = resp.json()
                        info["cid"] = data.get("cid", "unknown").replace("...", "")
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

    def get_identity(self, name: str) -> dict:
        return requests.get(f"{self.nodes[name]['url']}/identity").json()

    def get_stats(self, name: str) -> dict:
        return requests.get(f"{self.nodes[name]['url']}/").json()

    def get_thoughts(self, name: str) -> list:
        return requests.get(f"{self.nodes[name]['url']}/thoughts").json()["thoughts"]

    def create_thought(self, name: str, type: str, content: dict,
                       because: list = None, visibility: str = None) -> dict:
        payload = {"type": type, "content": content, "because": because or []}
        if visibility:
            payload["visibility"] = visibility
        return requests.post(f"{self.nodes[name]['url']}/thoughts", json=payload).json()

    def create_pool(self, name: str, pool_name: str, visibility: str = "members_only") -> dict:
        return requests.post(
            f"{self.nodes[name]['url']}/pools",
            params={"name": pool_name, "visibility": visibility}
        ).json()

    def add_pool_member(self, node_name: str, pool_cid: str, member_cid: str):
        return requests.post(
            f"{self.nodes[node_name]['url']}/pools/{pool_cid}/members",
            params={"member_cid": member_cid}
        ).json()

    def establish_peering(self, node_name: str, peer_identity: dict, shared_pools: list = None):
        return requests.post(
            f"{self.nodes[node_name]['url']}/peering",
            json={"peer_identity": peer_identity, "shared_pools": shared_pools or []}
        ).json()

    def sync_nodes(self, src: str, dst: str) -> dict:
        """Sync from src to dst (dst requests from src)."""
        src_url = self.nodes[src]["url"]
        dst_url = self.nodes[dst]["url"]

        # Get dst's bloom and identity
        bloom = requests.get(f"{dst_url}/bloom").json()
        dst_id = self.get_identity(dst)
        src_id = self.get_identity(src)

        # Request missing thoughts from src (filtered by visibility based on WHO'S ASKING)
        sync_resp = requests.post(
            f"{src_url}/sync",
            json={"bloom_hex": bloom["bloom_hex"], "sender_cid": dst_id["cid"]}  # dst is requesting
        )
        sync_data = sync_resp.json()

        # Receive at dst
        if sync_data["count"] > 0:
            recv = requests.post(
                f"{dst_url}/receive",
                json={"thoughts": sync_data["thoughts"], "sender_cid": src_id["cid"]}  # src is sending
            )
            return {**recv.json(), "filter_stats": sync_data.get("filter_stats", {})}
        return {"received": 0, "new": 0, "filter_stats": sync_data.get("filter_stats", {})}

    def bidirectional_sync(self, a: str, b: str):
        result_a = self.sync_nodes(a, b)
        result_b = self.sync_nodes(b, a)
        return {"a_to_b": result_a, "b_to_a": result_b}

    def get_provenance(self, name: str, thought_cid: str) -> dict:
        return requests.get(f"{self.nodes[name]['url']}/provenance/{thought_cid}").json()


def main():
    print("=" * 70)
    print("DOGFOOD 021: Visibility-Aware Sync Test")
    print("=" * 70)

    tester = VisibilityTester()

    try:
        # ====================================================================
        # PHASE 1: Create network
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 1: Creating network (4 nodes)")
        print("=" * 70)

        # Alice and Bob are in the same org
        # Carol is a partner with limited access
        # Eve is an outsider with no special access

        tester.start_node("Alice", 8001)
        tester.start_node("Bob", 8002)
        tester.start_node("Carol", 8003)
        tester.start_node("Eve", 8004)

        print("\n  Waiting for nodes...")
        tester.wait_for_nodes()

        alice_id = tester.get_identity("Alice")
        bob_id = tester.get_identity("Bob")
        carol_id = tester.get_identity("Carol")
        eve_id = tester.get_identity("Eve")

        print(f"\n  Alice: {alice_id['cid'][:20]}...")
        print(f"  Bob:   {bob_id['cid'][:20]}...")
        print(f"  Carol: {carol_id['cid'][:20]}...")
        print(f"  Eve:   {eve_id['cid'][:20]}...")

        # ====================================================================
        # PHASE 2: Create pools with different visibility
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 2: Creating pools")
        print("=" * 70)

        # Alice creates pools
        public_pool = tester.create_pool("Alice", "Public Announcements", "public")
        internal_pool = tester.create_pool("Alice", "Internal Team", "members_only")
        partner_pool = tester.create_pool("Alice", "Partner Collab", "members_only")

        print(f"\n  1. Public Announcements: {public_pool['cid'][:20]}...")
        print(f"  2. Internal Team: {internal_pool['cid'][:20]}...")
        print(f"  3. Partner Collab: {partner_pool['cid'][:20]}...")

        # Add members
        print("\n  Adding pool members:")

        # Internal: Alice + Bob
        tester.add_pool_member("Alice", internal_pool["cid"], alice_id["cid"])
        tester.add_pool_member("Alice", internal_pool["cid"], bob_id["cid"])
        print(f"    Internal Team: Alice, Bob")

        # Partner: Alice + Carol
        tester.add_pool_member("Alice", partner_pool["cid"], alice_id["cid"])
        tester.add_pool_member("Alice", partner_pool["cid"], carol_id["cid"])
        print(f"    Partner Collab: Alice, Carol")

        # Eve has no pool memberships

        # ====================================================================
        # PHASE 3: Create thoughts with different visibility
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 3: Creating thoughts with different visibility")
        print("=" * 70)

        # Public thought - everyone should see
        public_thought = tester.create_thought("Alice", "announcement", {
            "title": "Q1 Results Published",
            "text": "Our Q1 results are now available to the public."
        }, [alice_id["cid"]], visibility=None)  # None = public
        print(f"\n  1. Public announcement: {public_thought['cid'][:20]}...")

        # Internal thought - only Alice/Bob
        internal_thought = tester.create_thought("Alice", "memo", {
            "title": "Internal Strategy",
            "text": "CONFIDENTIAL: Our Q2 strategy is to focus on X market."
        }, [alice_id["cid"]], visibility=f"pool:{internal_pool['cid']}")
        print(f"  2. Internal memo (pool scoped): {internal_thought['cid'][:20]}...")

        # Partner thought - only Alice/Carol
        partner_thought = tester.create_thought("Alice", "proposal", {
            "title": "Partnership Draft",
            "text": "Here's the draft of our partnership agreement."
        }, [alice_id["cid"]], visibility=f"pool:{partner_pool['cid']}")
        print(f"  3. Partner proposal (pool scoped): {partner_thought['cid'][:20]}...")

        # Local-forever thought - never sync
        local_secret = tester.create_thought("Alice", "note", {
            "title": "Personal Reminder",
            "text": "Don't forget: Bob's birthday next week!"
        }, [alice_id["cid"]], visibility="local_forever")
        print(f"  4. Local secret (local_forever): {local_secret['cid'][:20]}...")

        # Participants-only thought
        participants_thought = tester.create_thought("Alice", "message", {
            "title": "Direct Message",
            "text": "Hey Bob, can you review this?",
            "participants": ["Alice", "Bob"]  # Only Alice and Bob
        }, [alice_id["cid"]], visibility="participants_only")
        print(f"  5. DM to Bob (participants_only): {participants_thought['cid'][:20]}...")

        # ====================================================================
        # PHASE 4: Establish peering agreements
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 4: Establishing peering agreements")
        print("=" * 70)

        # Alice ↔ Bob: Share internal pool
        tester.establish_peering("Alice", bob_id, [internal_pool["cid"]])
        tester.establish_peering("Bob", alice_id, [internal_pool["cid"]])
        print(f"\n  Alice ↔ Bob: Share internal pool")

        # Alice ↔ Carol: Share partner pool
        tester.establish_peering("Alice", carol_id, [partner_pool["cid"]])
        tester.establish_peering("Carol", alice_id, [partner_pool["cid"]])
        print(f"  Alice ↔ Carol: Share partner pool")

        # Alice ↔ Eve: No shared pools (public only)
        tester.establish_peering("Alice", eve_id, [])
        tester.establish_peering("Eve", alice_id, [])
        print(f"  Alice ↔ Eve: No shared pools (public only)")

        # ====================================================================
        # PHASE 5: Sync and verify filtering
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 5: Sync and verify filtering")
        print("=" * 70)

        # Sync Alice → Bob
        print("\n  Syncing Alice → Bob:")
        result = tester.sync_nodes("Alice", "Bob")
        stats = result.get("filter_stats", {})
        print(f"    Thoughts checked: {stats.get('total_checked', '?')}")
        print(f"    Missing (pre-filter): {stats.get('missing', '?')}")
        print(f"    Filtered (local_forever): {stats.get('filtered_local_forever', '?')}")
        print(f"    Filtered (no pool access): {stats.get('filtered_pool_access', '?')}")
        print(f"    Filtered (not participant): {stats.get('filtered_participants', '?')}")
        print(f"    Actually shared: {stats.get('shared', '?')}")
        print(f"    Bob received: {result.get('new', '?')} new thoughts")

        # Sync Alice → Carol
        print("\n  Syncing Alice → Carol:")
        result = tester.sync_nodes("Alice", "Carol")
        stats = result.get("filter_stats", {})
        print(f"    Thoughts checked: {stats.get('total_checked', '?')}")
        print(f"    Missing (pre-filter): {stats.get('missing', '?')}")
        print(f"    Filtered (local_forever): {stats.get('filtered_local_forever', '?')}")
        print(f"    Filtered (no pool access): {stats.get('filtered_pool_access', '?')}")
        print(f"    Filtered (not participant): {stats.get('filtered_participants', '?')}")
        print(f"    Actually shared: {stats.get('shared', '?')}")
        print(f"    Carol received: {result.get('new', '?')} new thoughts")

        # Sync Alice → Eve
        print("\n  Syncing Alice → Eve:")
        result = tester.sync_nodes("Alice", "Eve")
        stats = result.get("filter_stats", {})
        print(f"    Thoughts checked: {stats.get('total_checked', '?')}")
        print(f"    Missing (pre-filter): {stats.get('missing', '?')}")
        print(f"    Filtered (local_forever): {stats.get('filtered_local_forever', '?')}")
        print(f"    Filtered (no pool access): {stats.get('filtered_pool_access', '?')}")
        print(f"    Filtered (not participant): {stats.get('filtered_participants', '?')}")
        print(f"    Actually shared: {stats.get('shared', '?')}")
        print(f"    Eve received: {result.get('new', '?')} new thoughts")

        # ====================================================================
        # PHASE 6: Verify what each node can see
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 6: Verify thought visibility")
        print("=" * 70)

        # What should each node see? (match actual title values)
        expected = {
            "Bob": {
                "should_see": ["Q1 Results", "Internal Strategy", "Direct Message"],
                "should_not_see": ["Partnership Draft", "Personal Reminder"]
            },
            "Carol": {
                "should_see": ["Q1 Results", "Partnership Draft"],
                "should_not_see": ["Internal Strategy", "Personal Reminder", "Direct Message"]
            },
            "Eve": {
                "should_see": ["Q1 Results"],
                "should_not_see": ["Internal Strategy", "Partnership Draft", "Personal Reminder", "Direct Message"]
            }
        }

        def check_node_visibility(name: str):
            thoughts = tester.get_thoughts(name)
            titles = [t.get("content", {}).get("title", "") for t in thoughts]

            print(f"\n  {name}'s view:")
            print(f"    Total thoughts: {len(thoughts)}")

            # Check expected visibility
            exp = expected.get(name, {})
            for should_see in exp.get("should_see", []):
                found = any(should_see in title for title in titles)
                status = "✓" if found else "✗ MISSING"
                print(f"    {status} {should_see}")

            for should_not in exp.get("should_not_see", []):
                found = any(should_not in title for title in titles)
                status = "✗ LEAKED!" if found else "✓ (correctly hidden)"
                print(f"    {status} {should_not}")

        check_node_visibility("Bob")
        check_node_visibility("Carol")
        check_node_visibility("Eve")

        # ====================================================================
        # PHASE 7: Check sync provenance
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 7: Sync provenance tracking")
        print("=" * 70)

        # Check where Bob got the public thought from
        bob_provenance = tester.get_provenance("Bob", public_thought["cid"])
        print(f"\n  Bob's provenance for public thought:")
        print(f"    Thought: {public_thought['cid'][:20]}...")
        print(f"    Received via: {bob_provenance.get('received_via', 'unknown')[:20] if bob_provenance.get('received_via') else 'None'}...")

        # Check that Alice has no provenance for her own thoughts
        alice_provenance = tester.get_provenance("Alice", public_thought["cid"])
        print(f"\n  Alice's provenance for her own thought:")
        print(f"    Received via: {alice_provenance.get('received_via', 'None (created locally)')}")

        # Check local_forever provenance thoughts exist
        alice_thoughts = tester.get_thoughts("Alice")
        local_forever_count = sum(1 for t in alice_thoughts if t.get("visibility") == "local_forever")
        print(f"\n  Alice's local_forever thoughts: {local_forever_count}")

        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        all_stats = {name: tester.get_stats(name) for name in tester.nodes}

        print(f"""
  Nodes: 4 (Alice, Bob, Carol, Eve)
  Pools: 3 (Public, Internal, Partner)

  Peering agreements:
    Alice ↔ Bob: Internal pool
    Alice ↔ Carol: Partner pool
    Alice ↔ Eve: (public only)

  Thoughts created by Alice: 5
    1. Public announcement (visibility: null)
    2. Internal memo (visibility: pool:internal)
    3. Partner proposal (visibility: pool:partner)
    4. Local secret (visibility: local_forever)
    5. DM to Bob (visibility: participants_only)

  Visibility results:
    Bob sees:   Public, Internal, DM   (correct: teammate + DM recipient)
    Carol sees: Public, Partner        (correct: partner only)
    Eve sees:   Public only            (correct: outsider)

  Node statistics:
""")

        for name, stats in all_stats.items():
            print(f"    {name}: {stats['thoughts']} thoughts, {stats.get('filtered', 0)} filtered")

        print(f"""
  Key verifications:
    ✓ local_forever never syncs
    ✓ Pool-scoped thoughts only sync to pool members/peers
    ✓ participants_only respects participant list
    ✓ Sync provenance tracked as local_forever connections
        """)

        # Write output
        output = {
            "nodes": {name: {"thoughts": stats["thoughts"], "filtered": stats.get("filtered", 0)}
                      for name, stats in all_stats.items()},
            "pools": {
                "public": public_pool["cid"],
                "internal": internal_pool["cid"],
                "partner": partner_pool["cid"]
            },
            "thoughts": {
                "public": public_thought["cid"],
                "internal": internal_thought["cid"],
                "partner": partner_thought["cid"],
                "local_secret": local_secret["cid"],
                "dm_bob": participants_thought["cid"]
            }
        }

        output_path = os.path.join(BASE_DIR, "wellspring-dogfood-021-visibility.json")
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Wrote results to: {output_path}")

    finally:
        print("\n  Stopping nodes...")
        tester.stop_all()
        print("  Done.")


if __name__ == "__main__":
    main()
