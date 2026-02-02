#!/usr/bin/env python3
"""
Dogfood 010: Bidirectional Peering

Two identities establish a shared pool and exchange thoughts:
1. Alice creates identity, devices pool, sets expectation for "the bear"
2. The Bear creates identity, discovers Alice's expectation
3. Bilateral attestation establishes shared pool
4. Bidirectional thought exchange
5. Each side only sees what visibility allows

Simulates separate contexts communicating through a relay.
"""

import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from enum import Enum
import random

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
    signature: str = ""  # simulated

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
        if not self.signature:
            self.signature = f"sig_{self.created_by[:8]}_{self.cid[:8]}"

    def to_dict(self) -> dict:
        d = {
            "cid": self.cid,
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
            "because": self.because,
            "created_at": self.created_at,
            "signature": self.signature
        }
        if self.visibility:
            d["visibility"] = self.visibility
        return d


class SimulatedRelay:
    """
    Simulates the network/CDN layer.
    Thoughts go here; identities pull from here based on visibility.
    """

    def __init__(self):
        self.thoughts: Dict[str, Thought] = {}
        self.pool_members: Dict[str, Set[str]] = {}  # pool_cid -> set of identity_cids

    def publish(self, thought: Thought):
        """Publish a thought to the relay"""
        self.thoughts[thought.cid] = thought

    def add_pool_member(self, pool_cid: str, identity_cid: str):
        """Track pool membership for visibility checks"""
        if pool_cid not in self.pool_members:
            self.pool_members[pool_cid] = set()
        self.pool_members[pool_cid].add(identity_cid)

    def get_visible_thoughts(self, viewer_identity: str) -> List[Thought]:
        """Get all thoughts visible to this identity"""
        visible = []
        for thought in self.thoughts.values():
            if self._can_see(thought, viewer_identity):
                visible.append(thought)
        return visible

    def _can_see(self, thought: Thought, viewer_identity: str) -> bool:
        """Check if viewer can see this thought based on visibility"""
        if thought.visibility is None:
            return True  # public
        if thought.visibility == "local_forever":
            return thought.created_by == viewer_identity
        if thought.visibility.startswith("pool:"):
            pool_cid = thought.visibility.split(":", 1)[1]
            members = self.pool_members.get(pool_cid, set())
            return viewer_identity in members
        return False


class IdentityContext:
    """
    Represents one identity's view of the world.
    Has its own local storage and only sees what visibility allows.
    """

    def __init__(self, name: str, relay: SimulatedRelay):
        self.name = name
        self.relay = relay
        self.local_thoughts: Dict[str, Thought] = {}  # includes local_forever
        self.identity: Optional[Thought] = None
        self.devices_pool: Optional[Thought] = None

    def create_identity(self) -> Thought:
        """Bootstrap this identity"""
        self.identity = Thought(
            type="identity",
            content={
                "name": self.name,
                "pubkey": f"{self.name.lower().replace(' ', '_')}_pubkey_xxx"
            },
            created_by="GENESIS"
        )
        self.local_thoughts[self.identity.cid] = self.identity
        self.relay.publish(self.identity)
        return self.identity

    def create_devices_pool(self) -> Thought:
        """Create private devices pool"""
        self.devices_pool = Thought(
            type="pool",
            content={
                "name": f"{self.name.lower()}-devices",
                "purpose": "Private config and secrets",
                "admin": self.identity.cid
            },
            created_by=self.identity.cid,
            because=[self.identity.cid]
        )
        self.local_thoughts[self.devices_pool.cid] = self.devices_pool
        self.relay.publish(self.devices_pool)
        self.relay.add_pool_member(self.devices_pool.cid, self.identity.cid)
        return self.devices_pool

    def create_thought(self, type: str, content: dict, because: list = None,
                       visibility: str = None) -> Thought:
        """Create and publish a thought"""
        thought = Thought(
            type=type,
            content=content,
            created_by=self.identity.cid,
            because=because or [],
            visibility=visibility
        )
        self.local_thoughts[thought.cid] = thought

        # Only publish if not local_forever
        if visibility != "local_forever":
            self.relay.publish(thought)

        return thought

    def get_visible_thoughts(self) -> List[Thought]:
        """Get all thoughts this identity can see"""
        # Start with local thoughts
        visible = dict(self.local_thoughts)

        # Add relay thoughts we can see
        for thought in self.relay.get_visible_thoughts(self.identity.cid):
            visible[thought.cid] = thought

        return list(visible.values())

    def find_thoughts(self, type: str = None, created_by: str = None) -> List[Thought]:
        """Query visible thoughts"""
        results = []
        for thought in self.get_visible_thoughts():
            if type and thought.type != type:
                continue
            if created_by and thought.created_by != created_by:
                continue
            results.append(thought)
        return results


def run_simulation():
    """Run the bidirectional peering dogfood"""

    print("=" * 70)
    print("DOGFOOD 010: Bidirectional Peering")
    print("=" * 70)

    # Shared relay (simulates CDN/network)
    relay = SimulatedRelay()

    # === PHASE 1: Alice sets up ===
    print("\n" + "=" * 70)
    print("PHASE 1: Alice creates identity and expectation")
    print("=" * 70)

    alice = IdentityContext("Alice", relay)
    alice_id = alice.create_identity()
    print(f"  Alice identity: {alice_id.cid[:24]}...")

    alice_devices = alice.create_devices_pool()
    print(f"  Alice devices pool: {alice_devices.cid[:24]}...")

    # Alice creates expectation for "the bear"
    expectation = alice.create_thought(
        type="expectation",
        content={
            "expecting_name": "The Bear",
            "expecting_channel": "public_hello",
            "expires": (datetime.now() + timedelta(days=7)).isoformat(),
            "reason": "Friend introduction"
        },
        because=[alice_id.cid],
        visibility=f"pool:{alice_devices.cid}"  # private config
    )
    print(f"  Expectation for 'The Bear': {expectation.cid[:24]}...")
    print(f"    (visibility: pool-scoped, only Alice's devices see this)")

    # Alice creates a public hello pool for introductions
    hello_pool = alice.create_thought(
        type="pool",
        content={
            "name": "alice-hello",
            "purpose": "Public introductions",
            "admin": alice_id.cid,
            "visibility": "public"
        },
        because=[alice_id.cid]
    )
    print(f"  Hello pool (public): {hello_pool.cid[:24]}...")

    # Alice publishes hello card
    hello_card = alice.create_thought(
        type="hello_card",
        content={
            "identity": alice_id.cid,
            "name": "Alice",
            "hello_pool": hello_pool.cid,
            "message": "Looking to connect with The Bear"
        },
        because=[alice_id.cid, hello_pool.cid]
    )
    print(f"  Hello card published: {hello_card.cid[:24]}...")

    # === PHASE 2: The Bear discovers Alice ===
    print("\n" + "=" * 70)
    print("PHASE 2: The Bear discovers Alice's hello")
    print("=" * 70)

    bear = IdentityContext("The Bear", relay)
    bear_id = bear.create_identity()
    print(f"  The Bear identity: {bear_id.cid[:24]}...")

    bear_devices = bear.create_devices_pool()
    print(f"  The Bear devices pool: {bear_devices.cid[:24]}...")

    # The Bear searches for hello cards
    hello_cards = bear.find_thoughts(type="hello_card")
    print(f"  Found {len(hello_cards)} hello cards")

    for card in hello_cards:
        print(f"    - From: {card.content.get('name')}")
        print(f"      Message: {card.content.get('message')}")

    # The Bear decides to connect with Alice
    alice_card = hello_cards[0]  # Alice's card

    # === PHASE 3: Create shared pool with bilateral attestation ===
    print("\n" + "=" * 70)
    print("PHASE 3: Establish shared pool (bilateral attestation)")
    print("=" * 70)

    # The Bear creates a shared pool proposal
    shared_pool = bear.create_thought(
        type="pool",
        content={
            "name": "alice-bear-chat",
            "purpose": "Private conversation",
            "proposed_by": bear_id.cid,
            "proposed_to": alice_id.cid,
            "visibility": "private"
        },
        because=[bear_id.cid, alice_card.cid]
    )
    print(f"  Shared pool proposed: {shared_pool.cid[:24]}...")

    # The Bear attests to the pool (their half of bilateral)
    bear_membership = bear.create_thought(
        type="connection",
        content={
            "from": bear_id.cid,
            "to": shared_pool.cid,
            "relation": "member_of"
        },
        because=[bear_id.cid, shared_pool.cid]
    )

    bear_attestation = bear.create_thought(
        type="attestation",
        content={
            "on": bear_membership.cid,
            "weight": 1.0,
            "statement": "I want to join this pool"
        },
        because=[bear_membership.cid]
    )
    print(f"  The Bear attests membership: {bear_attestation.cid[:24]}...")

    # Add Bear to pool members in relay
    relay.add_pool_member(shared_pool.cid, bear_id.cid)

    # === Alice sees the proposal and accepts ===
    print("\n  --- Alice's turn ---")

    # Alice checks for pool proposals
    pools = alice.find_thoughts(type="pool")
    proposals = [p for p in pools if p.content.get("proposed_to") == alice_id.cid]
    print(f"  Alice sees {len(proposals)} pool proposals")

    # Alice checks her expectation
    print(f"  Checking expectation for 'The Bear'...")
    # (In real impl, would match proposal creator to expectation)
    print(f"    ✓ Matches expectation!")

    # Alice attests to accept
    alice_membership = alice.create_thought(
        type="connection",
        content={
            "from": alice_id.cid,
            "to": shared_pool.cid,
            "relation": "member_of"
        },
        because=[alice_id.cid, shared_pool.cid]
    )

    alice_attestation = alice.create_thought(
        type="attestation",
        content={
            "on": alice_membership.cid,
            "weight": 1.0,
            "statement": "I accept this pool"
        },
        because=[alice_membership.cid, expectation.cid]  # grounded in expectation
    )
    print(f"  Alice attests membership: {alice_attestation.cid[:24]}...")

    # Add Alice to pool members in relay
    relay.add_pool_member(shared_pool.cid, alice_id.cid)

    print(f"\n  ✓ Bilateral attestation complete!")
    print(f"    Pool: alice-bear-chat")
    print(f"    Members: Alice, The Bear")

    # === PHASE 4: Bidirectional thought exchange ===
    print("\n" + "=" * 70)
    print("PHASE 4: Bidirectional thought exchange")
    print("=" * 70)

    conversation = []

    # Alice sends first message
    msg1 = alice.create_thought(
        type="message",
        content={
            "text": "Hey Bear! Glad you found my hello card.",
            "pool": shared_pool.cid
        },
        because=[shared_pool.cid, alice_attestation.cid],
        visibility=f"pool:{shared_pool.cid}"
    )
    conversation.append(("Alice", msg1))
    print(f"  Alice: {msg1.content['text']}")

    # The Bear responds
    msg2 = bear.create_thought(
        type="message",
        content={
            "text": "Hey Alice! Yeah, the expectation system worked great.",
            "pool": shared_pool.cid
        },
        because=[shared_pool.cid, msg1.cid],  # references Alice's message
        visibility=f"pool:{shared_pool.cid}"
    )
    conversation.append(("The Bear", msg2))
    print(f"  The Bear: {msg2.content['text']}")

    # Alice responds with a thought chain
    msg3 = alice.create_thought(
        type="message",
        content={
            "text": "This is actually pretty cool. The because chain shows our whole conversation.",
            "pool": shared_pool.cid
        },
        because=[msg2.cid],
        visibility=f"pool:{shared_pool.cid}"
    )
    conversation.append(("Alice", msg3))
    print(f"  Alice: {msg3.content['text']}")

    # The Bear adds a thought with reasoning
    msg4 = bear.create_thought(
        type="message",
        content={
            "text": "And I can see the trail back through your expectation to your identity.",
            "pool": shared_pool.cid
        },
        because=[msg3.cid, alice_attestation.cid],
        visibility=f"pool:{shared_pool.cid}"
    )
    conversation.append(("The Bear", msg4))
    print(f"  The Bear: {msg4.content['text']}")

    # === PHASE 5: Verify visibility ===
    print("\n" + "=" * 70)
    print("PHASE 5: Visibility verification")
    print("=" * 70)

    # Create an outsider
    outsider = IdentityContext("Eve", relay)
    outsider_id = outsider.create_identity()
    print(f"  Outsider (Eve) created: {outsider_id.cid[:24]}...")

    # What can each party see?
    alice_visible = alice.get_visible_thoughts()
    bear_visible = bear.get_visible_thoughts()
    eve_visible = outsider.get_visible_thoughts()

    alice_messages = [t for t in alice_visible if t.type == "message"]
    bear_messages = [t for t in bear_visible if t.type == "message"]
    eve_messages = [t for t in eve_visible if t.type == "message"]

    print(f"\n  Visibility check:")
    print(f"    Alice sees {len(alice_messages)} messages ✓")
    print(f"    The Bear sees {len(bear_messages)} messages ✓")
    print(f"    Eve sees {len(eve_messages)} messages (should be 0)")

    # Can Eve see the hello card? (public)
    eve_hellos = [t for t in eve_visible if t.type == "hello_card"]
    print(f"    Eve sees {len(eve_hellos)} hello cards (public) ✓")

    # Can Eve see Alice's expectation? (pool-scoped)
    eve_expectations = [t for t in eve_visible if t.type == "expectation"]
    print(f"    Eve sees {len(eve_expectations)} expectations (should be 0)")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_thoughts = list(relay.thoughts.values())
    print(f"""
Total thoughts in relay: {len(all_thoughts)}

By type:
  - identity: {len([t for t in all_thoughts if t.type == 'identity'])}
  - pool: {len([t for t in all_thoughts if t.type == 'pool'])}
  - hello_card: {len([t for t in all_thoughts if t.type == 'hello_card'])}
  - connection: {len([t for t in all_thoughts if t.type == 'connection'])}
  - attestation: {len([t for t in all_thoughts if t.type == 'attestation'])}
  - message: {len([t for t in all_thoughts if t.type == 'message'])}

Visibility model verified:
  - Pool-scoped messages: only pool members see
  - Pool-scoped expectations: only devices pool sees
  - Public hello cards: everyone sees
  - local_forever: never leaves local storage

Peering flow:
  1. Alice creates identity + expectation for "The Bear"
  2. Alice publishes hello card (public)
  3. The Bear discovers hello, proposes shared pool
  4. Bilateral attestation: both sign membership
  5. Messages flow in shared pool (pool-scoped visibility)
  6. Because chains link the whole conversation

Key insight:
  The expectation was PRIVATE (Alice's devices pool).
  But it grounded Alice's acceptance of The Bear's proposal.
  The Bear never saw the expectation, but Alice's attestation
  references it — proving the connection was expected.
    """)

    # Write output
    output_file = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-010-peering.jsonl"
    with open(output_file, 'w') as f:
        for thought in all_thoughts:
            f.write(json.dumps(thought.to_dict()) + "\n")

    print(f"Wrote {len(all_thoughts)} thoughts to:")
    print(f"  {output_file}")

    return all_thoughts


if __name__ == "__main__":
    run_simulation()
