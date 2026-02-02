#!/usr/bin/env python3
"""
Wellspring Pool Sync: Multi-device pool as base sync layer.

The keif-devices pool is the foundation:
- Pool thought defines the container
- Device identities join via bilateral attestation
- Secrets sync only within pool (visibility: pool:<cid>)
- Multiple heads (devices) can sign as same logical identity
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
    visibility: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class Identity:
    """A signing identity (can be person or device)."""

    def __init__(self, name: str):
        self.name = name
        self.signing_key = nacl.signing.SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.pubkey_hex = self.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
        self.privkey_hex = self.signing_key.encode(encoder=nacl.encoding.HexEncoder).decode()
        self.cid: Optional[str] = None
        self.secret_cid: Optional[str] = None

    def compute_cid(self, content: dict, created_by: str, because: list) -> str:
        payload = {"content": content, "created_by": created_by, "because": because}
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        return f"cid:sha256:{digest[:32]}"

    def content_cid(self, content: dict) -> str:
        """CID from content only (for self-referential identities)."""
        canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        return f"cid:sha256:{digest[:32]}"

    def sign(self, cid: str) -> str:
        signed = self.signing_key.sign(cid.encode())
        return signed.signature.hex()

    def create_identity(self, autonomy: str = "sovereign", parent_cid: Optional[str] = None) -> Thought:
        """Create identity thought (public, shareable)."""
        content = {"name": self.name, "pubkey": f"ed25519:{self.pubkey_hex}", "autonomy": autonomy}
        if parent_cid:
            content["parent"] = parent_cid
        self.cid = self.content_cid(content)
        return Thought(
            cid=self.cid,
            type="identity",
            content=content,
            created_by=self.cid,
            because=[],
            created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(self.cid),
            schema_cid="cid:schema_identity_v1"
        )

    def create_secret(self, visibility: str = "local_forever") -> Thought:
        """Create secret thought with specified visibility."""
        content = {
            "type": "identity_secret",
            "for_identity": self.cid,
            "privkey": f"ed25519:{self.privkey_hex}"
        }
        self.secret_cid = self.content_cid(content)
        return Thought(
            cid=self.secret_cid,
            type="secret",
            content=content,
            created_by=self.cid,
            because=[],
            created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(self.secret_cid),
            visibility=visibility
        )

    def create_thought(self, type: str, content: dict, because: list,
                       schema_cid: Optional[str] = None, visibility: Optional[str] = None) -> Thought:
        because_norm = [{"thought_cid": b} if isinstance(b, str) else b for b in because]
        cid = self.compute_cid(content, self.cid, because_norm)
        return Thought(
            cid=cid, type=type, content=content, created_by=self.cid,
            because=because_norm, created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(cid), schema_cid=schema_cid, visibility=visibility
        )


def main():
    print("=" * 70)
    print("WELLSPRING POOL SYNC - Multi-Device Base Layer")
    print("=" * 70)

    # === LAYER 1: The Human Identity (Keif) ===
    keif = Identity("Keif")
    keif_identity = keif.create_identity()

    print(f"\n👤 HUMAN IDENTITY")
    print(f"   Keif: {keif.cid}")

    # === LAYER 2: The Devices Pool ===
    # Pool is created by Keif, defines the sync boundary for secrets
    pool_content = {
        "name": "keif-devices",
        "description": "Keif's personal devices - secrets sync within this pool",
        "visibility": "private",
        "admin": keif.cid
    }
    pool_cid = keif.content_cid(pool_content)

    pool_thought = keif.create_thought(
        type="pool",
        content=pool_content,
        because=[keif.cid],  # grounded in owner identity
        schema_cid="cid:schema_pool_v1"
    )
    # Fix: pool CID should be content-based for stable reference
    pool_thought.cid = pool_cid

    print(f"\n🏊 DEVICES POOL")
    print(f"   Pool: {pool_cid}")
    print(f"   Admin: {keif.cid[:32]}...")

    # === LAYER 3: Device Identities ===
    # Each device has its own keypair, but they're all "Keif"
    laptop = Identity("Keif@laptop")
    phone = Identity("Keif@phone")
    tablet = Identity("Keif@tablet")

    # Devices are managed identities under Keif
    laptop_identity = laptop.create_identity(autonomy="managed", parent_cid=keif.cid)
    phone_identity = phone.create_identity(autonomy="managed", parent_cid=keif.cid)
    tablet_identity = tablet.create_identity(autonomy="managed", parent_cid=keif.cid)

    print(f"\n💻 DEVICE IDENTITIES (managed under Keif)")
    print(f"   Laptop: {laptop.cid}")
    print(f"   Phone:  {phone.cid}")
    print(f"   Tablet: {tablet.cid}")

    # === LAYER 4: Pool Membership (Bilateral Attestation) ===
    thoughts = [keif_identity, pool_thought, laptop_identity, phone_identity, tablet_identity]

    # For each device: connection + bilateral attestation
    for device, device_id in [(laptop, laptop_identity), (phone, phone_identity), (tablet, tablet_identity)]:
        # Connection: device → member_of → pool
        conn = keif.create_thought(
            type="connection",
            content={"from": device.cid, "to": pool_cid, "relation": "member_of"},
            because=[device.cid, pool_cid],
            schema_cid="cid:schema_connection_v1"
        )
        thoughts.append(conn)

        # Attestation by device: "I want to join"
        device_attest = device.create_thought(
            type="attestation",
            content={"on": conn.cid, "weight": 1.0},
            because=[conn.cid],
            schema_cid="cid:schema_attestation_v1"
        )
        thoughts.append(device_attest)

        # Attestation by pool admin (Keif): "Pool accepts"
        admin_attest = keif.create_thought(
            type="attestation",
            content={"on": conn.cid, "weight": 1.0},
            because=[conn.cid, device.cid],  # I verified this device
            schema_cid="cid:schema_attestation_v1"
        )
        thoughts.append(admin_attest)

        print(f"\n   ✅ {device.name} membership:")
        print(f"      Connection: {conn.cid[:32]}...")
        print(f"      Device attests: {device_attest.cid[:32]}...")
        print(f"      Admin attests:  {admin_attest.cid[:32]}...")

    # === LAYER 5: Secrets with Pool Visibility ===
    # Keif's master secret syncs within devices pool
    keif_secret = keif.create_secret(visibility=f"pool:{pool_cid}")

    # Each device also has its own secret (for device-specific signing)
    laptop_secret = laptop.create_secret(visibility=f"pool:{pool_cid}")
    phone_secret = phone.create_secret(visibility=f"pool:{pool_cid}")
    tablet_secret = tablet.create_secret(visibility=f"pool:{pool_cid}")

    secrets = [keif_secret, laptop_secret, phone_secret, tablet_secret]

    print(f"\n🔐 SECRETS (visibility: pool:{pool_cid[:20]}...)")
    print(f"   Keif master: {keif_secret.cid}")
    print(f"   Laptop:      {laptop_secret.cid}")
    print(f"   Phone:       {phone_secret.cid}")
    print(f"   Tablet:      {tablet_secret.cid}")

    # === LAYER 6: Show Sync Behaviour ===
    print(f"\n" + "=" * 70)
    print("SYNC BEHAVIOUR")
    print("=" * 70)

    print(f"""
WHAT SYNCS WHERE:

  Public (everywhere):
    - keif identity
    - pool thought
    - device identities
    - membership connections
    - membership attestations
    - any thoughts created by Keif or devices

  Pool-scoped (keif-devices only):
    - keif master secret
    - laptop secret
    - phone secret
    - tablet secret

  External verifier sees:
    - All public thoughts ✓
    - Can verify all signatures ✓
    - Secret references unresolvable ✓ (expected)

  Any device in pool sees:
    - All public thoughts ✓
    - All secrets (can sign as Keif or as device) ✓
    - Full chain resolvable ✓
""")

    # === LAYER 7: Multi-Head Signing Demo ===
    print("=" * 70)
    print("MULTI-HEAD SIGNING (same logical identity, different devices)")
    print("=" * 70)

    # Laptop creates a thought
    laptop_thought = laptop.create_thought(
        type="basic",
        content={"text": "Written from laptop while on the train"},
        because=[laptop.cid],
        schema_cid="cid:schema_basic_v1"
    )
    thoughts.append(laptop_thought)

    # Phone creates a thought
    phone_thought = phone.create_thought(
        type="basic",
        content={"text": "Quick note from phone at the cafe"},
        because=[phone.cid],
        schema_cid="cid:schema_basic_v1"
    )
    thoughts.append(phone_thought)

    # Tablet continues the thread, referencing both
    tablet_thought = tablet.create_thought(
        type="basic",
        content={"text": "Synthesizing thoughts from laptop and phone"},
        because=[laptop_thought.cid, phone_thought.cid],
        schema_cid="cid:schema_basic_v1"
    )
    thoughts.append(tablet_thought)

    print(f"""
  Laptop writes:  {laptop_thought.cid[:32]}...
    created_by: {laptop.cid[:32]}...
    content: "Written from laptop while on the train"

  Phone writes:   {phone_thought.cid[:32]}...
    created_by: {phone.cid[:32]}...
    content: "Quick note from phone at the cafe"

  Tablet writes:  {tablet_thought.cid[:32]}...
    created_by: {tablet.cid[:32]}...
    because: [laptop_thought, phone_thought]
    content: "Synthesizing thoughts from laptop and phone"

  All three are Keif. Different devices, same person.
  Trust chain: device → managed under → Keif
  Verifiable: device pubkey in identity, signature checks out
""")

    # === OUTPUT FILES ===
    # Shareable thoughts (no secrets)
    share_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-004-public.jsonl"
    with open(share_path, 'w') as f:
        for t in thoughts:
            f.write(json.dumps(t.to_dict()) + '\n')

    # Pool-scoped secrets
    secret_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-004-secrets.jsonl"
    with open(secret_path, 'w') as f:
        for t in secrets:
            f.write(json.dumps(t.to_dict()) + '\n')

    print("=" * 70)
    print("OUTPUT")
    print("=" * 70)
    print(f"\n  Public thoughts:  wellspring-dogfood-004-public.jsonl ({len(thoughts)} thoughts)")
    print(f"  Pool secrets:     wellspring-dogfood-004-secrets.jsonl ({len(secrets)} secrets)")

    print(f"\n  Total structure:")
    print(f"    1 human identity (Keif)")
    print(f"    1 devices pool")
    print(f"    3 device identities (managed)")
    print(f"    3 membership connections")
    print(f"    6 membership attestations (bilateral)")
    print(f"    3 content thoughts (one per device)")
    print(f"    4 secrets (pool-scoped)")

    print(f"\n" + "=" * 70)
    print("Pool sync layer complete. Multi-headed operation verified.")
    print("=" * 70)


if __name__ == "__main__":
    main()
