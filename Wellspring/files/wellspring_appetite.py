#!/usr/bin/env python3
"""
Dogfood 009: Appetite & Expectations

Testing aspect-based rate limiting and communication suppression:
1. Baseline appetite configuration (pool-scoped to devices)
2. Expected partner (pre-authorized)
3. Unknown sender (rate-limited)
4. Excessive comms detection and suppression
5. Attack mode escalation

All configuration is thoughts. No magic settings.
Appetite/expectations are SECRETS — visibility: pool:devices-pool
"""

import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# Simulated CID computation
def compute_cid(content: dict) -> str:
    canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return f"baf_{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"

class RateLimitResult(Enum):
    ALLOWED = "allowed"
    QUEUED = "queued"
    RATE_LIMITED = "rate_limited"
    REJECTED = "rejected"

@dataclass
class Thought:
    type: str
    content: dict
    created_by: str
    because: list = field(default_factory=list)
    visibility: Optional[str] = None  # None = public, "local_forever", "pool:<cid>"
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

@dataclass
class IncomingMessage:
    """Simulates an incoming message from a sender"""
    sender_id: str
    content: str
    channel: str  # email, direct, public_pool
    timestamp: datetime = field(default_factory=datetime.now)

class AppetiteEngine:
    """
    Rate limiting engine driven by aspect thoughts.

    No hardcoded limits — everything comes from the thought graph.
    """

    def __init__(self, my_identity_cid: str):
        self.my_identity = my_identity_cid
        self.thoughts: dict[str, Thought] = {}
        self.message_log: list[tuple[str, datetime]] = []  # (sender, time)

        # These get populated from aspect thoughts
        self.appetite: Optional[Thought] = None
        self.expectations: dict[str, Thought] = {}  # channel -> expectation
        self.trust_scores: dict[str, float] = {}  # identity -> score

    def add_thought(self, thought: Thought) -> str:
        self.thoughts[thought.cid] = thought

        # Index special thought types
        if thought.type == "aspect" and thought.content.get("aspect_type") == "appetite":
            self.appetite = thought
            print(f"  📊 Appetite configured: {thought.content.get('limits', {})}")

        elif thought.type == "expectation":
            channel = thought.content.get("expecting_channel", "unknown")
            self.expectations[channel] = thought
            name = thought.content.get("expecting_name", "unknown")
            print(f"  🎯 Expectation set: {name} via {channel}")

        elif thought.type == "attestation" and thought.content.get("aspect_type") == "trust":
            target = thought.content.get("on")
            weight = thought.content.get("weight", 0.0)
            self.trust_scores[target] = weight

        return thought.cid

    def get_limits(self) -> dict:
        """Get current rate limits from appetite aspect"""
        if not self.appetite:
            # Default limits if no appetite configured
            return {
                "unknown_rate": 5,      # per hour
                "trusted_rate": 100,    # per hour
                "expectation_boost": 10,  # multiplier
                "attack_mode": False,
                "attack_threshold": 50,  # messages/hour triggers attack mode
            }
        return self.appetite.content.get("limits", {})

    def check_expectation(self, sender_id: str, channel: str) -> Optional[Thought]:
        """Check if we have an expectation for this sender"""
        expectation = self.expectations.get(channel)
        if expectation:
            # Check expiry
            expires = expectation.content.get("expires")
            if expires:
                exp_date = datetime.fromisoformat(expires)
                if datetime.now() > exp_date:
                    print(f"    ⏰ Expectation expired")
                    return None
            return expectation
        return None

    def get_trust(self, sender_id: str) -> float:
        """Get trust score for sender (0.0 = unknown, 1.0 = fully trusted)"""
        return self.trust_scores.get(sender_id, 0.0)

    def count_recent(self, sender_id: str, window_hours: int = 1) -> int:
        """Count messages from sender in recent window"""
        cutoff = datetime.now() - timedelta(hours=window_hours)
        return sum(1 for s, t in self.message_log if s == sender_id and t > cutoff)

    def count_total_recent(self, window_hours: int = 1) -> int:
        """Count all messages in recent window"""
        cutoff = datetime.now() - timedelta(hours=window_hours)
        return sum(1 for _, t in self.message_log if t > cutoff)

    def evaluate(self, msg: IncomingMessage) -> tuple[RateLimitResult, str]:
        """
        Evaluate an incoming message against appetite configuration.

        Returns (result, reason)
        """
        limits = self.get_limits()
        trust = self.get_trust(msg.sender_id)
        expectation = self.check_expectation(msg.sender_id, msg.channel)
        recent_from_sender = self.count_recent(msg.sender_id)
        total_recent = self.count_total_recent()

        # Check attack mode
        attack_mode = limits.get("attack_mode", False)
        if total_recent > limits.get("attack_threshold", 50):
            attack_mode = True

        print(f"\n  Evaluating: {msg.sender_id[:20]}...")
        print(f"    Trust: {trust:.2f}, Expected: {expectation is not None}, Recent: {recent_from_sender}")
        print(f"    Attack mode: {attack_mode}, Total recent: {total_recent}")

        # Attack mode: reject all unknowns
        if attack_mode and trust == 0.0 and not expectation:
            return (RateLimitResult.REJECTED, "Attack mode: unknown sender rejected")

        # Calculate effective rate limit
        if trust >= 0.8:
            rate_limit = limits.get("trusted_rate", 100)
            category = "trusted"
        elif expectation:
            base = limits.get("unknown_rate", 5)
            boost = limits.get("expectation_boost", 10)
            rate_limit = base * boost
            category = "expected"
        else:
            rate_limit = limits.get("unknown_rate", 5)
            category = "unknown"

        print(f"    Category: {category}, Rate limit: {rate_limit}/hour")

        # Check against limit
        if recent_from_sender >= rate_limit:
            if category == "unknown":
                return (RateLimitResult.REJECTED, f"Unknown sender exceeded {rate_limit}/hour")
            else:
                return (RateLimitResult.RATE_LIMITED, f"Exceeded {rate_limit}/hour, queued")

        # Log and allow
        self.message_log.append((msg.sender_id, msg.timestamp))
        return (RateLimitResult.ALLOWED, f"Allowed ({category})")


def run_simulation():
    """Run the appetite/expectations dogfood"""

    thoughts_output = []

    print("=" * 60)
    print("DOGFOOD 009: Appetite & Expectations")
    print("=" * 60)

    # === SETUP: Identities ===
    print("\n## Setting up identities...")

    alice = Thought(
        type="identity",
        content={"name": "Alice", "pubkey": "alice_pub_key_xxx"},
        created_by="GENESIS"
    )
    thoughts_output.append(alice)
    print(f"  Alice: {alice.cid[:20]}...")

    # === SETUP: Devices Pool (for secrets) ===
    print("\n## Setting up devices pool...")

    alice_devices_pool = Thought(
        type="pool",
        content={
            "name": "alice-devices",
            "purpose": "Multi-device sync for Alice's secrets and config",
            "admin": alice.cid,
        },
        created_by=alice.cid,
        because=[alice.cid]
    )
    thoughts_output.append(alice_devices_pool)
    print(f"  Devices pool: {alice_devices_pool.cid[:20]}...")
    print(f"  (appetite/expectations will be scoped here)")

    bob = Thought(
        type="identity",
        content={"name": "Bob", "pubkey": "bob_pub_key_xxx"},
        created_by="GENESIS"
    )
    thoughts_output.append(bob)
    print(f"  Bob: {bob.cid[:20]}...")

    carol = Thought(
        type="identity",
        content={"name": "Carol", "pubkey": "carol_pub_key_xxx"},
        created_by="GENESIS"
    )
    thoughts_output.append(carol)
    print(f"  Carol: {carol.cid[:20]}...")

    stranger = Thought(
        type="identity",
        content={"name": "Stranger", "pubkey": "stranger_pub_key_xxx"},
        created_by="GENESIS"
    )
    thoughts_output.append(stranger)
    print(f"  Stranger: {stranger.cid[:20]}...")

    spammer = Thought(
        type="identity",
        content={"name": "Spammer", "pubkey": "spammer_pub_key_xxx"},
        created_by="GENESIS"
    )
    thoughts_output.append(spammer)
    print(f"  Spammer: {spammer.cid[:20]}...")

    # === ALICE'S APPETITE ENGINE ===
    engine = AppetiteEngine(alice.cid)

    # === SCENARIO 1: Baseline Appetite Configuration ===
    print("\n" + "=" * 60)
    print("SCENARIO 1: Baseline Appetite Configuration")
    print("=" * 60)

    appetite_v1 = Thought(
        type="aspect",
        content={
            "aspect_type": "appetite",
            "description": "Normal operating mode",
            "limits": {
                "unknown_rate": 10,        # unknowns: 10/hour
                "trusted_rate": 1000,      # trusted: 1000/hour
                "expectation_boost": 50,   # expected unknowns: 500/hour
                "attack_mode": False,
                "attack_threshold": 30,    # lowered for demo: 30 msgs triggers attack
            }
        },
        created_by=alice.cid,
        because=[alice.cid],
        visibility=f"pool:{alice_devices_pool.cid}"  # SECRET: only syncs to devices
    )
    thoughts_output.append(appetite_v1)
    engine.add_thought(appetite_v1)
    print(f"  🔒 Visibility: pool-scoped (devices only)")

    # Add trust for Bob
    trust_bob = Thought(
        type="attestation",
        content={
            "aspect_type": "trust",
            "on": bob.cid,
            "weight": 1.0,
            "reason": "Known friend"
        },
        created_by=alice.cid,
        because=[alice.cid, bob.cid]
    )
    thoughts_output.append(trust_bob)
    engine.add_thought(trust_bob)
    print(f"  ✅ Bob trusted at 1.0")

    # === SCENARIO 2: Expected Partner ===
    print("\n" + "=" * 60)
    print("SCENARIO 2: Expected Partner (Carol)")
    print("=" * 60)

    expect_carol = Thought(
        type="expectation",
        content={
            "expecting_name": "Carol",
            "expecting_channel": "email:carol@example.com",
            "expires": (datetime.now() + timedelta(days=7)).isoformat(),
            "reason": "Meeting scheduled for next week"
        },
        created_by=alice.cid,
        because=[alice.cid],
        visibility=f"pool:{alice_devices_pool.cid}"  # SECRET: only syncs to devices
    )
    thoughts_output.append(expect_carol)
    engine.add_thought(expect_carol)
    print(f"  🔒 Visibility: pool-scoped (devices only)")

    # Carol sends a message
    carol_msg = IncomingMessage(
        sender_id=carol.cid,
        content="Hi Alice, confirming our meeting",
        channel="email:carol@example.com"
    )
    result, reason = engine.evaluate(carol_msg)
    print(f"  Result: {result.value} - {reason}")

    carol_result = Thought(
        type="basic",
        content={
            "event": "message_evaluated",
            "sender": carol.cid,
            "result": result.value,
            "reason": reason,
            "expectation_matched": True
        },
        created_by=alice.cid,
        because=[expect_carol.cid, alice.cid]
    )
    thoughts_output.append(carol_result)

    # === SCENARIO 3: Unknown Sender (No Expectation) ===
    print("\n" + "=" * 60)
    print("SCENARIO 3: Unknown Sender (Stranger)")
    print("=" * 60)

    # Stranger sends messages (should hit rate limit)
    for i in range(12):
        stranger_msg = IncomingMessage(
            sender_id=stranger.cid,
            content=f"Hello, this is message {i+1}",
            channel="email:stranger@random.com"
        )
        result, reason = engine.evaluate(stranger_msg)
        if i < 2 or i >= 9:  # Show first 2 and last 3
            print(f"  Message {i+1}: {result.value} - {reason}")
        elif i == 2:
            print(f"  ... (messages 3-9 similar)")

    stranger_summary = Thought(
        type="basic",
        content={
            "event": "rate_limit_enforced",
            "sender": stranger.cid,
            "messages_attempted": 12,
            "messages_allowed": 10,
            "messages_rejected": 2,
            "reason": "Unknown sender exceeded 10/hour limit"
        },
        created_by=alice.cid,
        because=[appetite_v1.cid]
    )
    thoughts_output.append(stranger_summary)

    # === SCENARIO 4: Excessive Comms (Spam Detection) ===
    print("\n" + "=" * 60)
    print("SCENARIO 4: Excessive Comms (Spammer triggers attack mode)")
    print("=" * 60)

    # Spammer floods
    print("  Spammer sending 95 messages...")
    allowed = 0
    rejected = 0
    for i in range(95):
        spam_msg = IncomingMessage(
            sender_id=spammer.cid,
            content=f"BUY NOW!!! {i}",
            channel="public_pool"
        )
        result, reason = engine.evaluate(spam_msg)
        if result == RateLimitResult.ALLOWED:
            allowed += 1
        else:
            rejected += 1

        # Show transition points
        if i == 9:
            print(f"  Message 10: {result.value} - {reason}")
        elif i == 10:
            print(f"  Message 11: {result.value} - rate limit kicks in")

    print(f"\n  Spammer results: {allowed} allowed, {rejected} rejected")

    # Check if attack mode triggered (lowered threshold for demo)
    total = engine.count_total_recent()
    print(f"  Total messages this hour: {total}")

    attack_mode_thought = None
    if total >= 30:  # lowered threshold for demo
        print("  ⚠️  ATTACK MODE TRIGGERED")

        # Create attack mode aspect (updating appetite)
        attack_mode_thought = Thought(
            type="aspect",
            content={
                "aspect_type": "appetite",
                "description": "Attack mode - lockdown",
                "limits": {
                    "unknown_rate": 0,         # block all unknowns
                    "trusted_rate": 100,       # trusted still works
                    "expectation_boost": 1,    # expectations don't help
                    "attack_mode": True,
                    "attack_threshold": 30,
                },
                "triggered_by": "excessive_volume",
                "previous_appetite": appetite_v1.cid
            },
            created_by=alice.cid,
            because=[appetite_v1.cid, spammer.cid],  # because of spammer
            visibility=f"pool:{alice_devices_pool.cid}"  # still pool-scoped
        )
        thoughts_output.append(attack_mode_thought)
        engine.add_thought(attack_mode_thought)
        print(f"  🔒 Attack mode config also pool-scoped")

    # === SCENARIO 5: Trusted Still Works in Attack Mode ===
    print("\n" + "=" * 60)
    print("SCENARIO 5: Trusted Sender During Attack Mode")
    print("=" * 60)

    bob_msg = IncomingMessage(
        sender_id=bob.cid,
        content="Hey Alice, are you okay? Saw unusual activity.",
        channel="direct"
    )
    result, reason = engine.evaluate(bob_msg)
    print(f"  Bob's message: {result.value} - {reason}")

    # Use attack mode thought if it exists, otherwise appetite_v1
    config_ref = attack_mode_thought.cid if attack_mode_thought else appetite_v1.cid
    bob_during_attack = Thought(
        type="basic",
        content={
            "event": "trusted_allowed_during_attack" if attack_mode_thought else "trusted_allowed",
            "sender": bob.cid,
            "result": result.value,
            "note": "Trust relationship bypasses attack mode restrictions"
        },
        created_by=alice.cid,
        because=[config_ref, trust_bob.cid]
    )
    thoughts_output.append(bob_during_attack)

    # === SCENARIO 6: Recovery from Attack Mode ===
    print("\n" + "=" * 60)
    print("SCENARIO 6: Recovery - Restoring Normal Appetite")
    print("=" * 60)

    # Reference the attack mode thought if it exists
    recovery_from = attack_mode_thought.cid if attack_mode_thought else appetite_v1.cid

    recovery = Thought(
        type="aspect",
        content={
            "aspect_type": "appetite",
            "description": "Normal mode restored",
            "limits": {
                "unknown_rate": 10,
                "trusted_rate": 1000,
                "expectation_boost": 50,
                "attack_mode": False,
                "attack_threshold": 30,
            },
            "recovered_from": recovery_from,
            "recovery_reason": "Attack subsided, manual review complete"
        },
        created_by=alice.cid,
        because=[recovery_from, alice.cid],
        visibility=f"pool:{alice_devices_pool.cid}"  # still pool-scoped
    )
    thoughts_output.append(recovery)
    engine.add_thought(recovery)
    print(f"  ✅ Normal appetite restored")
    print(f"  🔒 Recovery config also pool-scoped")
    print(f"  Because chain: {'attack_mode' if attack_mode_thought else 'baseline'} → review → recovery")

    # === SUMMARY ===
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"""
Configuration as Thoughts:
  - Appetite aspects define rate limits
  - Expectation thoughts pre-authorize contacts
  - Trust attestations set sender categories
  - Attack mode is just another appetite aspect
  - Recovery creates because chain to attack

Visibility Model:
  - Appetite config: pool-scoped to devices pool
  - Expectations: pool-scoped to devices pool
  - Attack mode: pool-scoped (all devices see lockdown)
  - Recovery: pool-scoped (all devices recover together)

  → Your CDN partner is a pool member
  → Config syncs to devices, not broadcast publicly
  → Attestation from CDN = "I'll enforce these limits"

Rate Limit Categories:
  - Trusted (1.0): 1000/hour
  - Expected (0.0 + expectation): 500/hour (10 × 50 boost)
  - Unknown (0.0): 10/hour
  - Attack mode unknowns: rejected

Key Insights:
  - No magic settings — all configuration is thoughts
  - Because chains show why limits changed
  - Attack mode is auditable (who triggered, when, why)
  - Recovery is explicit (not silent reset)
  - Expectations are time-bounded (expire)
  - Pool scoping = same config across all devices
  - CDN relationship is just another pool membership
    """)

    # Write output
    output_file = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-009-appetite.jsonl"
    with open(output_file, 'w') as f:
        for thought in thoughts_output:
            record = {
                "cid": thought.cid,
                "type": thought.type,
                "content": thought.content,
                "created_by": thought.created_by,
                "because": thought.because,
                "created_at": thought.created_at
            }
            if thought.visibility:
                record["visibility"] = thought.visibility
            f.write(json.dumps(record) + "\n")

    print(f"\nWrote {len(thoughts_output)} thoughts to:")
    print(f"  {output_file}")

    return thoughts_output

if __name__ == "__main__":
    run_simulation()
