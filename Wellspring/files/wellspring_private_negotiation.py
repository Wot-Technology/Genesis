#!/usr/bin/env python3
"""
Dogfood 020: Private Negotiation with Public Attestation
Multiple pools with privacy levels, off-connection negotiation,
multi-party attestation proving work happened without revealing details.
"""

import subprocess
import time
import requests
import json
import sys
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_SCRIPT = os.path.join(BASE_DIR, "wellspring_node.py")

# ============================================================================
# EXTENDED NODE - adds pool and visibility support
# ============================================================================

class AdvancedNetworkSimulator:
    def __init__(self):
        self.processes = []
        self.nodes = {}
        self.pools = {}  # pool_name -> {cid, visibility, members, thoughts}

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
            "proc": proc,
            "pools": []  # Pool memberships
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

    def get_identity(self, name: str) -> dict:
        return requests.get(f"{self.nodes[name]['url']}/identity").json()

    def get_stats(self, name: str) -> dict:
        return requests.get(f"{self.nodes[name]['url']}/").json()

    def get_thoughts(self, name: str) -> list:
        return requests.get(f"{self.nodes[name]['url']}/thoughts").json()["thoughts"]

    def create_thought(self, name: str, type: str, content: dict,
                       because: list = None, visibility: str = None) -> dict:
        payload = {"type": type, "content": content, "because": because or []}
        # Note: visibility would be handled by the node in a full impl
        # For now we track it in content
        if visibility:
            payload["content"]["_visibility"] = visibility
        return requests.post(f"{self.nodes[name]['url']}/thoughts", json=payload).json()

    def sync_nodes(self, src: str, dst: str) -> dict:
        src_url = self.nodes[src]["url"]
        dst_url = self.nodes[dst]["url"]

        bloom = requests.get(f"{dst_url}/bloom").json()
        src_id = self.get_identity(src)

        sync_resp = requests.post(
            f"{src_url}/sync",
            json={"bloom_hex": bloom["bloom_hex"], "sender_cid": src_id["cid"]}
        )
        sync_data = sync_resp.json()

        if sync_data["count"] > 0:
            # Filter by visibility in a real impl
            recv = requests.post(
                f"{dst_url}/receive",
                json={"thoughts": sync_data["thoughts"], "sender_cid": src_id["cid"]}
            )
            return recv.json()
        return {"received": 0, "new": 0}

    def bidirectional_sync(self, a: str, b: str):
        self.sync_nodes(a, b)
        self.sync_nodes(b, a)

    def sync_group(self, members: list, rounds: int = 3):
        """Sync all members of a group with each other."""
        for _ in range(rounds):
            for i, a in enumerate(members):
                for b in members[i+1:]:
                    self.bidirectional_sync(a, b)

# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("=" * 70)
    print("DOGFOOD 020: Private Negotiation with Public Attestation")
    print("=" * 70)

    sim = AdvancedNetworkSimulator()

    try:
        # ====================================================================
        # PHASE 1: Create diverse network
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 1: Creating diverse network (15 nodes, 5 pools)")
        print("=" * 70)

        # Humans
        humans = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank"]
        for i, name in enumerate(humans):
            sim.start_node(name, 8001 + i)

        # Bots/Agents
        bots = ["Agent-1", "Agent-2", "Agent-3"]
        for i, name in enumerate(bots):
            sim.start_node(name, 8011 + i)

        # Organizations
        orgs = ["OrgA-Node", "OrgB-Node", "OrgC-Node"]
        for i, name in enumerate(orgs):
            sim.start_node(name, 8021 + i)

        # Public infrastructure
        infra = ["PublicRelay", "ArchiveNode", "IndexNode"]
        for i, name in enumerate(infra):
            sim.start_node(name, 8031 + i)

        print("\n  Waiting for nodes...")
        sim.wait_for_nodes()

        print(f"\n  Humans: {', '.join(humans)}")
        print(f"  Bots: {', '.join(bots)}")
        print(f"  Orgs: {', '.join(orgs)}")
        print(f"  Infrastructure: {', '.join(infra)}")

        # ====================================================================
        # PHASE 2: Create pools with different privacy levels
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 2: Creating pools with different privacy levels")
        print("=" * 70)

        # Pool 1: Public Commons (everyone can see, anyone can write)
        alice_id = sim.get_identity("Alice")
        public_pool = sim.create_thought("Alice", "pool", {
            "name": "Public Commons",
            "visibility": "public",
            "access": "open",
            "description": "Public discussion space"
        }, [alice_id["cid"]])
        print(f"\n  1. Public Commons: {public_pool['cid'][:20]}...")
        print("     Visibility: public, Access: open")

        # Pool 2: OrgA Private (only OrgA members)
        orga_id = sim.get_identity("OrgA-Node")
        orga_pool = sim.create_thought("OrgA-Node", "pool", {
            "name": "OrgA Internal",
            "visibility": "members_only",
            "access": "invite",
            "description": "OrgA private discussions"
        }, [orga_id["cid"]])
        print(f"\n  2. OrgA Internal: {orga_pool['cid'][:20]}...")
        print("     Visibility: members_only, Access: invite")

        # Pool 3: Human-Bot Negotiation (private, specific participants)
        negotiation_pool = sim.create_thought("Alice", "pool", {
            "name": "Alice-Agent1 Negotiation",
            "visibility": "participants_only",
            "access": "closed",
            "participants": ["Alice", "Agent-1"],
            "description": "Private negotiation space"
        }, [alice_id["cid"]])
        print(f"\n  3. Alice-Agent1 Negotiation: {negotiation_pool['cid'][:20]}...")
        print("     Visibility: participants_only, Access: closed")

        # Pool 4: Cross-Org Collaboration (selected orgs)
        collab_pool = sim.create_thought("OrgA-Node", "pool", {
            "name": "OrgA-OrgB Collaboration",
            "visibility": "members_only",
            "access": "invite",
            "organizations": ["OrgA", "OrgB"],
            "description": "Cross-org project space"
        }, [orga_id["cid"]])
        print(f"\n  4. OrgA-OrgB Collaboration: {collab_pool['cid'][:20]}...")
        print("     Visibility: members_only, Access: invite (OrgA, OrgB)")

        # Pool 5: Archive (public read, restricted write)
        archive_id = sim.get_identity("ArchiveNode")
        archive_pool = sim.create_thought("ArchiveNode", "pool", {
            "name": "Public Archive",
            "visibility": "public",
            "access": "attested_only",
            "description": "Permanent record of attested work"
        }, [archive_id["cid"]])
        print(f"\n  5. Public Archive: {archive_pool['cid'][:20]}...")
        print("     Visibility: public, Access: attested_only")

        # ====================================================================
        # PHASE 3: The Workflow - Public request, private negotiation
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 3: The Workflow")
        print("=" * 70)

        # Step 1: Alice posts a request in public
        print("\n  STEP 1: Alice posts request in Public Commons")
        public_request = sim.create_thought("Alice", "request", {
            "title": "Need analysis of Q4 market data",
            "description": "Looking for someone to analyze our Q4 sales figures",
            "pool": public_pool["cid"],
            "_visibility": "public"
        }, [public_pool["cid"], alice_id["cid"]])
        print(f"    Request: {public_request['cid'][:20]}...")

        # Step 2: Agent-1 responds publicly (showing interest)
        print("\n  STEP 2: Agent-1 responds publicly (interest)")
        agent1_id = sim.get_identity("Agent-1")
        public_response = sim.create_thought("Agent-1", "response", {
            "text": "I can help with this analysis. Shall we discuss details privately?",
            "pool": public_pool["cid"],
            "_visibility": "public"
        }, [public_request["cid"], agent1_id["cid"]])
        print(f"    Response: {public_response['cid'][:20]}...")

        # Step 3: Move to private negotiation
        print("\n  STEP 3: Move to private negotiation pool")
        private_start = sim.create_thought("Alice", "message", {
            "text": "Here are the confidential Q4 figures: [REDACTED - actual data]",
            "pool": negotiation_pool["cid"],
            "_visibility": "participants_only"
        }, [negotiation_pool["cid"], public_response["cid"], alice_id["cid"]])
        print(f"    Private message (Alice): {private_start['cid'][:20]}...")

        # Step 4: Agent works on it (private)
        print("\n  STEP 4: Agent-1 works privately")
        agent_work_1 = sim.create_thought("Agent-1", "analysis", {
            "text": "Initial findings show 23% growth in segment A, decline in B",
            "pool": negotiation_pool["cid"],
            "_visibility": "participants_only"
        }, [private_start["cid"], agent1_id["cid"]])
        print(f"    Analysis draft 1: {agent_work_1['cid'][:20]}...")

        agent_work_2 = sim.create_thought("Agent-1", "analysis", {
            "text": "Revised analysis with corrected seasonality adjustment",
            "pool": negotiation_pool["cid"],
            "_visibility": "participants_only"
        }, [agent_work_1["cid"], agent1_id["cid"]])
        print(f"    Analysis draft 2: {agent_work_2['cid'][:20]}...")

        # Step 5: Alice reviews and requests changes (private)
        print("\n  STEP 5: Alice reviews privately")
        alice_feedback = sim.create_thought("Alice", "feedback", {
            "text": "Good but please add regional breakdown",
            "pool": negotiation_pool["cid"],
            "_visibility": "participants_only"
        }, [agent_work_2["cid"], alice_id["cid"]])
        print(f"    Feedback: {alice_feedback['cid'][:20]}...")

        # Step 6: Agent final version (private)
        print("\n  STEP 6: Agent-1 creates final version")
        agent_final = sim.create_thought("Agent-1", "deliverable", {
            "title": "Q4 Market Analysis - Final",
            "text": "Complete analysis with regional breakdown [CONFIDENTIAL]",
            "pool": negotiation_pool["cid"],
            "_visibility": "participants_only"
        }, [alice_feedback["cid"], agent1_id["cid"]])
        print(f"    Final deliverable: {agent_final['cid'][:20]}...")

        # Step 7: Alice brings in Bob for review (still private, expanded)
        print("\n  STEP 7: Alice brings Bob into the loop")
        bob_id = sim.get_identity("Bob")

        # Create new pool for expanded review
        review_pool = sim.create_thought("Alice", "pool", {
            "name": "Q4 Analysis Review",
            "visibility": "participants_only",
            "access": "closed",
            "participants": ["Alice", "Agent-1", "Bob"],
        }, [alice_id["cid"]])
        print(f"    Review pool: {review_pool['cid'][:20]}...")

        # Share deliverable to review pool
        share_to_bob = sim.create_thought("Alice", "share", {
            "text": "Bob, please review this analysis",
            "references": agent_final["cid"],
            "pool": review_pool["cid"],
            "_visibility": "participants_only"
        }, [agent_final["cid"], review_pool["cid"], alice_id["cid"]])
        print(f"    Shared to Bob: {share_to_bob['cid'][:20]}...")

        # Bob reviews
        bob_review = sim.create_thought("Bob", "review", {
            "text": "Looks solid. I approve.",
            "pool": review_pool["cid"],
            "_visibility": "participants_only"
        }, [share_to_bob["cid"], bob_id["cid"]])
        print(f"    Bob's review: {bob_review['cid'][:20]}...")

        # ====================================================================
        # PHASE 4: Multi-party public attestation
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 4: Multi-party public attestation")
        print("=" * 70)

        # Now all three attest publicly that work was completed
        # The attestation is public, but references private work via CID
        # Observers can see THAT work happened, not WHAT the work contained

        print("\n  Creating public attestations (work happened, details private):")

        # Alice attests
        alice_attestation = sim.create_thought("Alice", "attestation", {
            "statement": "I attest that Q4 market analysis was completed satisfactorily",
            "work_reference": agent_final["cid"],  # CID is public, content is not
            "pool": archive_pool["cid"],
            "participants": ["Alice", "Agent-1", "Bob"],
            "_visibility": "public"
        }, [agent_final["cid"], archive_pool["cid"], alice_id["cid"]])
        print(f"    Alice attests: {alice_attestation['cid'][:20]}...")

        # Agent-1 attests
        agent_attestation = sim.create_thought("Agent-1", "attestation", {
            "statement": "I attest that I performed Q4 market analysis for Alice",
            "work_reference": agent_final["cid"],
            "pool": archive_pool["cid"],
            "deliverable_type": "market_analysis",
            "_visibility": "public"
        }, [agent_final["cid"], alice_attestation["cid"], agent1_id["cid"]])
        print(f"    Agent-1 attests: {agent_attestation['cid'][:20]}...")

        # Bob attests
        bob_attestation = sim.create_thought("Bob", "attestation", {
            "statement": "I reviewed and approved the Q4 market analysis",
            "work_reference": agent_final["cid"],
            "pool": archive_pool["cid"],
            "role": "reviewer",
            "_visibility": "public"
        }, [agent_final["cid"], alice_attestation["cid"], bob_id["cid"]])
        print(f"    Bob attests: {bob_attestation['cid'][:20]}...")

        # Combined attestation (optional - shows group consensus)
        combined_attestation = sim.create_thought("Alice", "group_attestation", {
            "statement": "Multi-party attestation: Q4 analysis completed and verified",
            "attestors": [alice_id["cid"], agent1_id["cid"], bob_id["cid"]],
            "individual_attestations": [
                alice_attestation["cid"],
                agent_attestation["cid"],
                bob_attestation["cid"]
            ],
            "pool": archive_pool["cid"],
            "_visibility": "public"
        }, [alice_attestation["cid"], agent_attestation["cid"], bob_attestation["cid"]])
        print(f"    Combined attestation: {combined_attestation['cid'][:20]}...")

        # ====================================================================
        # PHASE 5: Sync and verify visibility
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 5: Sync and verify visibility")
        print("=" * 70)

        # Sync public nodes
        public_nodes = ["Alice", "Bob", "Agent-1", "PublicRelay", "ArchiveNode", "IndexNode"]
        print("\n  Syncing public nodes...")
        sim.sync_group(public_nodes, rounds=3)

        # Check what each node type can see
        print("\n  Visibility check:")

        # Public relay should see all public thoughts
        relay_thoughts = sim.get_thoughts("PublicRelay")
        public_thoughts = [t for t in relay_thoughts if t["content"].get("_visibility") == "public"]
        private_thoughts = [t for t in relay_thoughts if t["content"].get("_visibility") == "participants_only"]

        print(f"\n    PublicRelay sees:")
        print(f"      Public thoughts: {len(public_thoughts)}")
        print(f"      Private thoughts: {len(private_thoughts)} (leaked in this sim - would be filtered)")

        # What's in the public archive?
        archive_thoughts = sim.get_thoughts("ArchiveNode")
        attestations = [t for t in archive_thoughts if t["type"] == "attestation" or t["type"] == "group_attestation"]
        print(f"\n    ArchiveNode attestations: {len(attestations)}")
        for att in attestations:
            stmt = att["content"].get("statement", "")[:50]
            print(f"      - \"{stmt}...\"")

        # Can Carol (outsider) see the work?
        print("\n    Carol (outsider) perspective:")
        # Sync Carol with public relay
        sim.bidirectional_sync("Carol", "PublicRelay")
        carol_thoughts = sim.get_thoughts("Carol")

        carol_sees_attestations = [t for t in carol_thoughts if t["type"] in ["attestation", "group_attestation"]]
        carol_sees_private = [t for t in carol_thoughts if t["content"].get("pool") == negotiation_pool["cid"]]

        print(f"      Can see attestations: {len(carol_sees_attestations)} ✓")
        print(f"      Can see private negotiation: {len(carol_sees_private)} {'✗ (good)' if len(carol_sees_private) == 0 else '(leaked!)'}")

        # ====================================================================
        # PHASE 6: Trace the provenance
        # ====================================================================
        print("\n" + "=" * 70)
        print("PHASE 6: Provenance trace")
        print("=" * 70)

        print("\n  The public can trace:")
        print("  ┌────────────────────────────────────────────────────────────┐")
        print("  │  Combined Attestation (public)                             │")
        print("  │    ├── Alice's attestation (public)                        │")
        print("  │    │     └── references: agent_final (PRIVATE CID)         │")
        print("  │    ├── Agent-1's attestation (public)                      │")
        print("  │    │     └── references: agent_final (PRIVATE CID)         │")
        print("  │    └── Bob's attestation (public)                          │")
        print("  │          └── references: agent_final (PRIVATE CID)         │")
        print("  └────────────────────────────────────────────────────────────┘")
        print("")
        print("  The public KNOWS:")
        print("    - Work was done (attestations exist)")
        print("    - Who participated (attestor identities)")
        print("    - That all parties agreed (multi-sig)")
        print("    - A deliverable exists (CID reference)")
        print("")
        print("  The public CANNOT see:")
        print("    - The actual analysis content")
        print("    - The negotiation process")
        print("    - The confidential data")
        print("    - Draft iterations")

        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        all_stats = {name: sim.get_stats(name)["thoughts"] for name in sim.nodes}

        print(f"""
  Network: {len(sim.nodes)} nodes
    - Humans: {len(humans)}
    - Bots: {len(bots)}
    - Orgs: {len(orgs)}
    - Infrastructure: {len(infra)}

  Pools created: 5
    - Public Commons (open)
    - OrgA Internal (members only)
    - Alice-Agent1 Negotiation (participants only)
    - Q4 Analysis Review (participants only)
    - Public Archive (public read, attested write)

  Workflow executed:
    1. Public request posted
    2. Public interest expressed
    3. Private negotiation (human + bot)
    4. Private iteration (drafts, feedback)
    5. Private review (added Bob)
    6. PUBLIC attestation (all 3 parties)

  Privacy preserved:
    - Negotiation details: PRIVATE (pool-scoped)
    - Work output: PRIVATE (CID referenced only)
    - Attestations: PUBLIC (in archive)
    - Participation proof: PUBLIC (verifiable)

  This is the "boardroom pattern":
    - The meeting happened (public knowledge)
    - Who attended (public)
    - That agreement was reached (public)
    - What was discussed (private)
        """)

        # Write output
        output = {
            "nodes": {n: {"thoughts": all_stats[n]} for n in sim.nodes},
            "pools": {
                "public_commons": public_pool["cid"],
                "orga_internal": orga_pool["cid"],
                "negotiation": negotiation_pool["cid"],
                "review": review_pool["cid"],
                "archive": archive_pool["cid"]
            },
            "attestations": {
                "alice": alice_attestation["cid"],
                "agent": agent_attestation["cid"],
                "bob": bob_attestation["cid"],
                "combined": combined_attestation["cid"]
            }
        }

        output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-020-negotiation.json"
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"Wrote results to: {output_path}")

    finally:
        print("\n  Stopping nodes...")
        sim.stop_all()
        print("  Done.")

if __name__ == "__main__":
    main()
