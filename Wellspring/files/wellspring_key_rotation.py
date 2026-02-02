#!/usr/bin/env python3
"""
Wellspring Key Rotation: Attestation Chain vs same_as

Key insight: You don't need a special `same_as` connection.
The rotation IS a thought, attested by both keys.
Anyone walking back from new identity sees the proof.
"""

import json
import hashlib
from datetime import datetime, timezone
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

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class Identity:
    def __init__(self, name: str):
        self.name = name
        self.signing_key = nacl.signing.SigningKey.generate()
        self.pubkey_hex = self.signing_key.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
        self.cid: Optional[str] = None

    def content_cid(self, content: dict) -> str:
        return f"cid:sha256:{hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:32]}"

    def compute_cid(self, content: dict, created_by: str, because: list) -> str:
        payload = {"content": content, "created_by": created_by, "because": because}
        return f"cid:sha256:{hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]}"

    def sign(self, cid: str) -> str:
        return self.signing_key.sign(cid.encode()).signature.hex()

    def create_identity(self) -> Thought:
        content = {"name": self.name, "pubkey": f"ed25519:{self.pubkey_hex}"}
        self.cid = self.content_cid(content)
        return Thought(
            cid=self.cid, type="identity", content=content, created_by=self.cid,
            because=[], created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(self.cid), schema_cid="cid:schema_identity_v1"
        )

    def create_thought(self, type: str, content: dict, because: list,
                       schema_cid: Optional[str] = None) -> Thought:
        because_norm = [{"thought_cid": b} if isinstance(b, str) else b for b in because]
        cid = self.compute_cid(content, self.cid, because_norm)
        return Thought(
            cid=cid, type=type, content=content, created_by=self.cid,
            because=because_norm, created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(cid), schema_cid=schema_cid
        )


def main():
    print("=" * 70)
    print("WELLSPRING KEY ROTATION - Attestation Chain Proves Continuity")
    print("=" * 70)

    all_thoughts = []

    # === ORIGINAL IDENTITY ===
    keif_v1 = Identity("Keif")
    keif_v1_id = keif_v1.create_identity()
    all_thoughts.append(keif_v1_id)

    print(f"\n🔑 ORIGINAL IDENTITY (v1)")
    print(f"   Name: Keif")
    print(f"   CID:  {keif_v1.cid}")
    print(f"   Key:  {keif_v1.pubkey_hex[:32]}...")

    # Some thoughts under v1
    v1_thought1 = keif_v1.create_thought(
        "basic",
        {"text": "Memory is traversal, not storage"},
        [keif_v1.cid],
        "cid:schema_basic_v1"
    )
    all_thoughts.append(v1_thought1)

    v1_thought2 = keif_v1.create_thought(
        "basic",
        {"text": "Self-describing schemas all the way down"},
        [v1_thought1.cid],
        "cid:schema_basic_v1"
    )
    all_thoughts.append(v1_thought2)

    print(f"\n   Thoughts created: 2")
    print(f"   Trail: v1_id → thought1 → thought2")

    # === KEY ROTATION ===
    print(f"\n" + "=" * 70)
    print("KEY ROTATION")
    print("=" * 70)

    # Create new identity with fresh keypair
    keif_v2 = Identity("Keif")
    keif_v2_id = keif_v2.create_identity()
    all_thoughts.append(keif_v2_id)

    print(f"\n🔑 NEW IDENTITY (v2)")
    print(f"   Name: Keif")
    print(f"   CID:  {keif_v2.cid}")
    print(f"   Key:  {keif_v2.pubkey_hex[:32]}...")

    # === THE ROTATION THOUGHT ===
    # Created by OLD identity, references NEW identity
    # This is the bridge — signed with the old key

    rotation_thought = keif_v1.create_thought(
        "basic",
        {
            "text": "Rotating to new keypair",
            "rotation": {
                "from_identity": keif_v1.cid,
                "to_identity": keif_v2.cid,
                "reason": "Scheduled key rotation",
                "old_key_status": "deprecated"
            }
        },
        [keif_v1.cid, keif_v2.cid],  # because includes BOTH identities
        "cid:schema_basic_v1"
    )
    all_thoughts.append(rotation_thought)

    print(f"\n📜 ROTATION THOUGHT (signed by v1)")
    print(f"   CID:        {rotation_thought.cid}")
    print(f"   created_by: {rotation_thought.created_by[:32]}... (v1)")
    print(f"   because:    [{keif_v1.cid[:20]}..., {keif_v2.cid[:20]}...]")
    print(f"   signature:  {rotation_thought.signature[:32]}... (v1 key)")

    # === NEW IDENTITY ATTESTS THE ROTATION ===
    # This closes the loop — new key confirms the rotation

    rotation_attestation = keif_v2.create_thought(
        "attestation",
        {
            "on": rotation_thought.cid,
            "weight": 1.0
        },
        [rotation_thought.cid, keif_v1.cid],  # grounded in rotation and old identity
        "cid:schema_attestation_v1"
    )
    all_thoughts.append(rotation_attestation)

    print(f"\n✅ ROTATION ATTESTATION (signed by v2)")
    print(f"   CID:        {rotation_attestation.cid}")
    print(f"   created_by: {rotation_attestation.created_by[:32]}... (v2)")
    print(f"   on:         {rotation_thought.cid[:32]}...")
    print(f"   signature:  {rotation_attestation.signature[:32]}... (v2 key)")

    # === CONTINUE WITH NEW IDENTITY ===
    v2_thought1 = keif_v2.create_thought(
        "basic",
        {"text": "First thought after rotation"},
        [rotation_attestation.cid],  # Grounded in the rotation!
        "cid:schema_basic_v1"
    )
    all_thoughts.append(v2_thought1)

    v2_thought2 = keif_v2.create_thought(
        "basic",
        {"text": "Continuing the work with new key"},
        [v2_thought1.cid, v1_thought2.cid],  # Can still reference old thoughts!
        "cid:schema_basic_v1"
    )
    all_thoughts.append(v2_thought2)

    print(f"\n   New thoughts: 2")
    print(f"   v2_thought1.because → [rotation_attestation]")
    print(f"   v2_thought2.because → [v2_thought1, v1_thought2]")

    # === THE PROOF ===
    print(f"\n" + "=" * 70)
    print("THE PROOF: Walking the Chain")
    print("=" * 70)

    print(f"""
Starting from v2_thought2, walk because backward:

  v2_thought2 (by v2)
    ├── because: v2_thought1 (by v2)
    │     └── because: rotation_attestation (by v2)
    │           └── because: rotation_thought (by v1!)  ← BRIDGE
    │                 └── because: [v1_identity, v2_identity]
    │
    └── because: v1_thought2 (by v1)
          └── because: v1_thought1 (by v1)
                └── because: v1_identity

WHAT THE VERIFIER SEES:

  1. v2_thought2 signed by v2 key ✓
  2. Walk back → rotation_attestation signed by v2 ✓
  3. Walk back → rotation_thought signed by v1 ✓
  4. Rotation thought says "v1 → v2"
  5. Both keys signed their side of the bridge
  6. v1 and v2 are the same person (cryptographic proof)

NO `same_as` CONNECTION NEEDED:
  - The rotation thought IS the proof
  - Signed by old key
  - Attested by new key
  - Both signatures verifiable
  - Because chain links them
""")

    # === WHY NOT same_as? ===
    print("=" * 70)
    print("WHY `same_as` IS REDUNDANT")
    print("=" * 70)

    print(f"""
OPTION A: same_as connection
  CONNECTION {{ from: v1, to: v2, relation: "same_as" }}
  ATTESTATION by v1: +1.0
  ATTESTATION by v2: +1.0

OPTION B: rotation thought + attestation (what we did)
  THOUGHT by v1: "Rotating to v2" (because: [v1, v2])
  ATTESTATION by v2: +1.0 on rotation thought

BOTH PROVIDE:
  ✓ v1 key signed something referencing v2
  ✓ v2 key signed something referencing v1
  ✓ Bidirectional cryptographic proof

OPTION B IS SIMPLER:
  - No special connection type
  - Rotation thought carries context (reason, status, etc.)
  - Same attestation pattern used everywhere else
  - One less concept to implement

THE INSIGHT:
  Attestation is the universal mechanism.
  `same_as` is just an attestation pattern, not a primitive.
  The because chain already links identities.
""")

    # === REVOCATION OF OLD KEY ===
    print("=" * 70)
    print("AFTER ROTATION: OLD KEY STATUS")
    print("=" * 70)

    # v1 attests its own deprecation
    deprecation = keif_v1.create_thought(
        "attestation",
        {
            "on": keif_v1.cid,
            "weight": 0.0,  # No longer active
            "via": rotation_thought.cid,
            "status": "deprecated"
        },
        [rotation_thought.cid],
        "cid:schema_attestation_v1"
    )
    all_thoughts.append(deprecation)

    print(f"""
OLD IDENTITY DEPRECATION:
  v1 attests on itself: weight 0.0 (deprecated)
  via: rotation_thought

  This means:
  - v1 can still verify old signatures ✓
  - New signatures from v1 are suspect (deprecated)
  - Trust computation sees: v1 → deprecated → use v2

DELETE OLD SECRET:
  If old secret is deleted, v1 can't sign anything new.
  Only the deprecation attestation remains (already signed).
  Clean handoff complete.
""")

    # === OUTPUT ===
    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-007-rotation.jsonl"
    with open(output_path, 'w') as f:
        for t in all_thoughts:
            f.write(json.dumps(t.to_dict()) + '\n')

    print("=" * 70)
    print("OUTPUT")
    print("=" * 70)
    print(f"\n  File: wellspring-dogfood-007-rotation.jsonl")
    print(f"  Thoughts: {len(all_thoughts)}")
    print(f"")
    print(f"  Chain:")
    print(f"    v1_identity → v1_thought1 → v1_thought2")
    print(f"         ↓")
    print(f"    rotation_thought (by v1, because includes v2)")
    print(f"         ↓")
    print(f"    rotation_attestation (by v2)")
    print(f"         ↓")
    print(f"    v2_thought1 → v2_thought2")
    print(f"                      ↓")
    print(f"               (also references v1_thought2)")

    print(f"\n" + "=" * 70)
    print("Key rotation complete. No same_as needed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
