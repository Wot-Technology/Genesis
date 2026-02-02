#!/usr/bin/env python3
"""
Wellspring Revocation: Device compromise and trust degradation.

Scenario: Phone gets stolen. Bad actor creates thoughts.
Detection: Owner notices suspicious activity.
Response: Revoke device, mark compromise window, flag affected thoughts.

Key insight: Revocation isn't just "no more access" — it's "everything since
<timestamp> needs review." The chain is immutable, but trust is recomputable.
"""

import json
import hashlib
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import Optional
import nacl.signing
import nacl.encoding


@dataclass
class Thought:
    cid: str
    type: str
    content: dict
    created_by: str
    because: list
    created_at: str
    signature: str
    schema_cid: Optional[str] = None
    visibility: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class Identity:
    def __init__(self, name: str):
        self.name = name
        self.signing_key = nacl.signing.SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.pubkey_hex = self.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
        self.cid: Optional[str] = None

    def content_cid(self, content: dict) -> str:
        canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
        return f"cid:sha256:{hashlib.sha256(canonical.encode()).hexdigest()[:32]}"

    def compute_cid(self, content: dict, created_by: str, because: list) -> str:
        payload = {"content": content, "created_by": created_by, "because": because}
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return f"cid:sha256:{hashlib.sha256(canonical.encode()).hexdigest()[:32]}"

    def sign(self, cid: str) -> str:
        return self.signing_key.sign(cid.encode()).signature.hex()

    def create_identity(self, autonomy: str = "sovereign", parent_cid: Optional[str] = None) -> Thought:
        content = {"name": self.name, "pubkey": f"ed25519:{self.pubkey_hex}", "autonomy": autonomy}
        if parent_cid:
            content["parent"] = parent_cid
        self.cid = self.content_cid(content)
        return Thought(
            cid=self.cid, type="identity", content=content, created_by=self.cid,
            because=[], created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(self.cid), schema_cid="cid:schema_identity_v1"
        )

    def create_thought(self, type: str, content: dict, because: list,
                       schema_cid: Optional[str] = None, timestamp: Optional[str] = None) -> Thought:
        because_norm = [{"thought_cid": b} if isinstance(b, str) else b for b in because]
        cid = self.compute_cid(content, self.cid, because_norm)
        return Thought(
            cid=cid, type=type, content=content, created_by=self.cid,
            because=because_norm, created_at=timestamp or datetime.now(timezone.utc).isoformat(),
            signature=self.sign(cid), schema_cid=schema_cid
        )


def main():
    print("=" * 70)
    print("WELLSPRING REVOCATION - Compromise Detection & Trust Degradation")
    print("=" * 70)

    # === SETUP: Keif with phone device ===
    keif = Identity("Keif")
    keif_id = keif.create_identity()

    phone = Identity("Keif@phone")
    phone_id = phone.create_identity(autonomy="managed", parent_cid=keif.cid)

    pool_cid = "cid:sha256:keif_devices_pool_placeholder"

    # Membership connection
    membership_conn = keif.create_thought(
        type="connection",
        content={"from": phone.cid, "to": pool_cid, "relation": "member_of"},
        because=[phone.cid, pool_cid],
        schema_cid="cid:schema_connection_v1"
    )

    # Bilateral attestation (both approve)
    phone_accepts = phone.create_thought(
        type="attestation",
        content={"on": membership_conn.cid, "weight": 1.0},
        because=[membership_conn.cid],
        schema_cid="cid:schema_attestation_v1"
    )

    keif_accepts = keif.create_thought(
        type="attestation",
        content={"on": membership_conn.cid, "weight": 1.0},
        because=[membership_conn.cid, phone.cid],
        schema_cid="cid:schema_attestation_v1"
    )

    thoughts = [keif_id, phone_id, membership_conn, phone_accepts, keif_accepts]

    print(f"\n📱 SETUP COMPLETE")
    print(f"   Keif: {keif.cid[:32]}...")
    print(f"   Phone: {phone.cid[:32]}...")
    print(f"   Membership: {membership_conn.cid[:32]}...")

    # === TIMELINE: Normal usage, then compromise ===
    base_time = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

    # Day 1-5: Legitimate phone usage
    legitimate_thoughts = []
    for day in range(5):
        t = phone.create_thought(
            type="basic",
            content={"text": f"Legitimate note from phone, day {day+1}"},
            because=[phone.cid],
            schema_cid="cid:schema_basic_v1",
            timestamp=(base_time + timedelta(days=day)).isoformat()
        )
        legitimate_thoughts.append(t)
        thoughts.append(t)

    print(f"\n✅ LEGITIMATE USAGE (Day 1-5)")
    for t in legitimate_thoughts:
        print(f"   {t.created_at[:10]}: {t.content['text']}")

    # Day 6: Phone stolen, bad actor starts using it
    compromise_time = base_time + timedelta(days=5, hours=14)  # Afternoon of day 6

    # Day 6-8: Compromised usage (bad actor has the phone)
    compromised_thoughts = []
    for day in range(3):
        t = phone.create_thought(
            type="basic",
            content={"text": f"[COMPROMISED] Malicious note, day {day+6}"},
            because=[phone.cid],
            schema_cid="cid:schema_basic_v1",
            timestamp=(compromise_time + timedelta(days=day)).isoformat()
        )
        compromised_thoughts.append(t)
        thoughts.append(t)

    print(f"\n⚠️  COMPROMISED USAGE (Day 6-8) — bad actor has phone")
    for t in compromised_thoughts:
        print(f"   {t.created_at[:10]}: {t.content['text']}")

    # === DETECTION & REVOCATION ===
    detection_time = base_time + timedelta(days=8, hours=9)

    print(f"\n" + "=" * 70)
    print(f"🚨 COMPROMISE DETECTED: {detection_time.isoformat()}")
    print("=" * 70)

    # Step 1: Revoke device membership (-1.0 attestation)
    revocation = keif.create_thought(
        type="attestation",
        content={
            "on": membership_conn.cid,
            "weight": -1.0,  # REVOKE
        },
        because=[membership_conn.cid],
        schema_cid="cid:schema_attestation_v1",
        timestamp=detection_time.isoformat()
    )
    thoughts.append(revocation)

    print(f"\n1️⃣  REVOCATION ATTESTATION")
    print(f"   CID: {revocation.cid[:32]}...")
    print(f"   On: {membership_conn.cid[:32]}...")
    print(f"   Weight: -1.0 (revoke)")

    # Step 2: Create compromise window marker
    compromise_marker = keif.create_thought(
        type="aspect",
        content={
            "aspect_type": "constraint",
            "domain": "trust",
            "name": "compromise_window",
            "applies_to": phone.cid,
            "window_start": compromise_time.isoformat(),
            "window_end": detection_time.isoformat(),
            "reason": "Phone stolen, unauthorized access detected"
        },
        because=[revocation.cid, phone.cid],
        schema_cid="cid:schema_aspect_v1",
        timestamp=detection_time.isoformat()
    )
    thoughts.append(compromise_marker)

    print(f"\n2️⃣  COMPROMISE WINDOW MARKER")
    print(f"   CID: {compromise_marker.cid[:32]}...")
    print(f"   Device: {phone.cid[:32]}...")
    print(f"   Window: {compromise_time.isoformat()[:10]} → {detection_time.isoformat()[:10]}")
    print(f"   Reason: {compromise_marker.content['reason']}")

    # Step 3: Flag each compromised thought
    flags = []
    for ct in compromised_thoughts:
        flag = keif.create_thought(
            type="attestation",
            content={
                "on": ct.cid,
                "weight": 0.0,  # Neutral — needs review
                "via": compromise_marker.cid,  # Through this aspect
            },
            because=[ct.cid, compromise_marker.cid],
            schema_cid="cid:schema_attestation_v1",
            timestamp=detection_time.isoformat()
        )
        flags.append(flag)
        thoughts.append(flag)

    print(f"\n3️⃣  FLAGGED THOUGHTS (weight: 0.0 = needs review)")
    for i, (ct, flag) in enumerate(zip(compromised_thoughts, flags)):
        print(f"   [{i+1}] {ct.cid[:32]}...")
        print(f"       Flagged via: {compromise_marker.cid[:32]}...")
        print(f"       Content: {ct.content['text'][:40]}...")

    # === TRUST COMPUTATION ===
    print(f"\n" + "=" * 70)
    print("TRUST RECOMPUTATION")
    print("=" * 70)

    print(f"""
BEFORE compromise detection:
  - All phone thoughts trusted (device in pool, bilateral attestation)
  - Trust score: 1.0 (managed device, active membership)

AFTER compromise detection:
  - Revocation attestation: weight -1.0 on membership
  - Membership status: REVOKED
  - Compromise window defined: {compromise_time.isoformat()[:10]} → {detection_time.isoformat()[:10]}

THOUGHT-LEVEL TRUST:

  Legitimate thoughts (before compromise window):
    - Still trusted (created before window)
    - Trust = base_trust (device was valid at creation time)

  Compromised thoughts (within window):
    - Flagged with weight 0.0 via compromise_marker
    - Trust = 0.0 (requires manual review)
    - Can be individually verified or rejected later

  Future thoughts (after revocation):
    - Device can still sign (has keys)
    - But membership revoked → signatures don't grant trust
    - Trust = 0.0 (no valid membership path)
""")

    # === RESOLUTION OPTIONS ===
    print("=" * 70)
    print("RESOLUTION OPTIONS")
    print("=" * 70)

    print(f"""
For each flagged thought, Keif can:

  A) REJECT (-1.0): "This was definitely the bad actor"
     → Attestation weight -1.0, grounded in compromise_marker
     → Downstream thoughts referencing this are also suspect

  B) VERIFY (+1.0): "I actually wrote this, just before losing phone"
     → Attestation weight +1.0, grounded in memory/evidence
     → Restores trust to this specific thought

  C) LEAVE FLAGGED (0.0): "Can't determine, needs more investigation"
     → Stays at 0.0, others can see it's disputed
     → May be resolved later with more evidence

The compromise_marker stays forever. It's part of the history.
Anyone walking the chain can see: "This device was compromised during this window."
Trust is recomputable. The data is immutable. The interpretation evolves.
""")

    # === DOWNSTREAM EFFECTS ===
    print("=" * 70)
    print("DOWNSTREAM EFFECTS")
    print("=" * 70)

    # What if a compromised thought was referenced by others?
    # Create an example where someone cited a compromised thought
    other_person = Identity("Alice")
    other_id = other_person.create_identity()
    thoughts.append(other_id)

    # Alice cited the first compromised thought before Keif noticed
    alice_thought = other_person.create_thought(
        type="basic",
        content={"text": "Interesting point from Keif's phone note"},
        because=[compromised_thoughts[0].cid],  # References compromised thought!
        schema_cid="cid:schema_basic_v1",
        timestamp=(compromise_time + timedelta(days=1)).isoformat()
    )
    thoughts.append(alice_thought)

    print(f"""
SCENARIO: Alice cited a thought from the compromise window

  Alice's thought: {alice_thought.cid[:32]}...
    because: [{compromised_thoughts[0].cid[:32]}...]

  When compromise_marker is created:
    → Alice's because chain now includes a flagged thought
    → Her thought's groundedness score drops
    → She can see: "Warning: your source was flagged as potentially compromised"

  Alice's options:
    A) Remove the because reference (create new thought without it)
    B) Add her own attestation: "I verified this independently"
    C) Wait for Keif to resolve the flag

  The chain is transparent. Alice isn't blamed. She just cited something
  that turned out to be suspect. The system shows the uncertainty.
""")

    # === OUTPUT ===
    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-005-revocation.jsonl"
    with open(output_path, 'w') as f:
        for t in thoughts:
            f.write(json.dumps(t.to_dict()) + '\n')

    print("=" * 70)
    print("OUTPUT")
    print("=" * 70)
    print(f"\n  File: wellspring-dogfood-005-revocation.jsonl")
    print(f"  Thoughts: {len(thoughts)}")
    print(f"")
    print(f"  Structure:")
    print(f"    2 identities (Keif, Phone, Alice)")
    print(f"    1 membership connection")
    print(f"    2 membership attestations (+1.0 bilateral)")
    print(f"    5 legitimate thoughts (before compromise)")
    print(f"    3 compromised thoughts (during window)")
    print(f"    1 revocation attestation (-1.0)")
    print(f"    1 compromise window marker")
    print(f"    3 flag attestations (0.0 on compromised thoughts)")
    print(f"    1 downstream citation (Alice)")

    print(f"\n" + "=" * 70)
    print("Revocation complete. Compromise window marked. Trust recomputable.")
    print("=" * 70)


if __name__ == "__main__":
    main()
