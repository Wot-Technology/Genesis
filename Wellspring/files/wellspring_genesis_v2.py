#!/usr/bin/env python3
"""
Wellspring Genesis v2: Private keys as local-forever thoughts.

Key insight: The private key is stored as a thought with visibility: "local_forever".
If it's present locally, we can sign as that identity. If not, we can verify but not sign.

Structure:
  identity_thought (pubkey, shareable)
      ↑ because
  secret_thought (privkey, local_forever, never syncs)
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
    """The one primitive."""
    cid: str
    type: str
    content: dict
    created_by: str
    because: list
    created_at: str
    signature: str
    schema_cid: Optional[str] = None
    visibility: Optional[str] = None  # None = default (shareable), "local_forever" = never sync

    def to_dict(self) -> dict:
        d = asdict(self)
        # Remove None fields
        return {k: v for k, v in d.items() if v is not None}


class Identity:
    """A sovereign identity with local secret storage."""

    def __init__(self, name: str):
        self.name = name
        self.signing_key = nacl.signing.SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.pubkey_hex = self.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
        self.privkey_hex = self.signing_key.encode(encoder=nacl.encoding.HexEncoder).decode()
        self.cid: Optional[str] = None
        self.secret_cid: Optional[str] = None
        self.thoughts: list[Thought] = []
        self.local_thoughts: list[Thought] = []  # Never sync these

    def compute_cid(self, content: dict, created_by: str, because: list) -> str:
        payload = {"content": content, "created_by": created_by, "because": because}
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        return f"cid:sha256:{digest[:32]}"

    def sign(self, cid: str) -> str:
        signed = self.signing_key.sign(cid.encode())
        return signed.signature.hex()

    def create_identity_pair(self) -> tuple[Thought, Thought]:
        """
        Create the identity thought pair:
        1. secret_thought - holds private key, local_forever
        2. identity_thought - holds public key, references secret via because
        """
        # Secret thought first (terminal, no because)
        secret_content = {
            "type": "identity_secret",
            "privkey": f"ed25519:{self.privkey_hex}",
            "note": "This thought never leaves local storage. Delete to revoke signing capability."
        }
        secret_cid_raw = hashlib.sha256(json.dumps(secret_content, sort_keys=True).encode()).hexdigest()
        self.secret_cid = f"cid:sha256:{secret_cid_raw[:32]}"

        # For secret, we self-sign with a bootstrap marker
        # The secret thought is signed by the key it contains (self-proving)
        secret_thought = Thought(
            cid=self.secret_cid,
            type="secret",
            content=secret_content,
            created_by=self.secret_cid,  # self-referential
            because=[],
            created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(self.secret_cid),
            visibility="local_forever"
        )
        self.local_thoughts.append(secret_thought)

        # Identity thought (public, references secret)
        identity_content = {
            "name": self.name,
            "pubkey": f"ed25519:{self.pubkey_hex}",
            "autonomy": "sovereign"
        }
        identity_cid_raw = hashlib.sha256(json.dumps(identity_content, sort_keys=True).encode()).hexdigest()
        self.cid = f"cid:sha256:{identity_cid_raw[:32]}"

        identity_thought = Thought(
            cid=self.cid,
            type="identity",
            content=identity_content,
            created_by=self.cid,  # self-referential (public identity)
            because=[{"thought_cid": self.secret_cid}],  # grounded in secret
            created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(self.cid),
            schema_cid="cid:schema_identity_v1"
        )
        self.thoughts.append(identity_thought)

        return secret_thought, identity_thought

    def create_thought(self, type: str, content: dict, because: list,
                       schema_cid: Optional[str] = None) -> Thought:
        """Create a signed thought."""
        because_normalized = []
        for b in because:
            if isinstance(b, str):
                because_normalized.append({"thought_cid": b})
            elif isinstance(b, dict):
                because_normalized.append(b)
            else:
                because_normalized.append(asdict(b))

        cid = self.compute_cid(content, self.cid, because_normalized)

        thought = Thought(
            cid=cid,
            type=type,
            content=content,
            created_by=self.cid,
            because=because_normalized,
            created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(cid),
            schema_cid=schema_cid
        )
        self.thoughts.append(thought)
        return thought


def main():
    print("=" * 70)
    print("WELLSPRING GENESIS v2 - Private Keys as Local-Forever Thoughts")
    print("=" * 70)

    # Create identities
    keif = Identity("Keif")
    agent = Identity("Claude-Agent")

    # Create identity pairs (secret + public)
    keif_secret, keif_id = keif.create_identity_pair()
    agent_secret, agent_id = agent.create_identity_pair()

    print(f"\n🔐 Identity Pairs Created:")
    print(f"\n  KEIF:")
    print(f"    Secret (local_forever): {keif_secret.cid}")
    print(f"    Public (shareable):     {keif_id.cid}")
    print(f"    Identity.because → [{keif_secret.cid[:32]}...]")

    print(f"\n  AGENT:")
    print(f"    Secret (local_forever): {agent_secret.cid}")
    print(f"    Public (shareable):     {agent_id.cid}")
    print(f"    Identity.because → [{agent_secret.cid[:32]}...]")

    # Create some thoughts
    keif_t1 = keif.create_thought(
        type="basic",
        content={"text": "Private keys are thoughts too. Local-forever means they never sync."},
        because=[keif_id.cid],
        schema_cid="cid:schema_basic_v1"
    )

    agent_t1 = agent.create_thought(
        type="basic",
        content={"text": "If the secret thought is present, we can sign. If not, we can only verify."},
        because=[agent_id.cid],
        schema_cid="cid:schema_basic_v1"
    )

    # Cross-reference
    agent_t2 = agent.create_thought(
        type="basic",
        content={"text": "The identity thought's 'because' points to its secret. Remote verifiers see the reference but can't resolve it."},
        because=[agent_t1.cid, {"thought_cid": keif_t1.cid}],
        schema_cid="cid:schema_basic_v1"
    )

    # Write outputs
    # Local file (includes secrets)
    local_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-local-secrets.jsonl"
    with open(local_path, 'w') as f:
        for t in keif.local_thoughts + agent.local_thoughts:
            f.write(json.dumps(t.to_dict()) + '\n')

    # Shareable file (no secrets)
    share_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-003.jsonl"
    with open(share_path, 'w') as f:
        for t in keif.thoughts + agent.thoughts:
            f.write(json.dumps(t.to_dict()) + '\n')

    print(f"\n📄 Output files:")
    print(f"  Local (with secrets): wellspring-local-secrets.jsonl ({len(keif.local_thoughts + agent.local_thoughts)} thoughts)")
    print(f"  Shareable:            wellspring-dogfood-003.jsonl ({len(keif.thoughts + agent.thoughts)} thoughts)")

    # Show what remote sees vs what local sees
    print(f"\n" + "=" * 70)
    print("WHAT REMOTE SEES (shareable, secrets stripped):")
    print("=" * 70)
    for t in keif.thoughts[:2]:
        print(f"\n  {t.type}: {t.cid}")
        if t.because:
            for b in t.because:
                bcid = b.get('thought_cid')
                resolvable = bcid in [x.cid for x in keif.thoughts + agent.thoughts]
                status = "✓ resolvable" if resolvable else "✗ unresolvable (local_forever)"
                print(f"    because: {bcid[:40]}... {status}")

    print(f"\n" + "=" * 70)
    print("WHAT LOCAL SEES (can sign, full chain):")
    print("=" * 70)
    all_local = keif.local_thoughts + keif.thoughts
    for t in all_local[:3]:
        print(f"\n  {t.type}: {t.cid}")
        vis = t.visibility or "shareable"
        print(f"    visibility: {vis}")
        if t.because:
            for b in t.because:
                bcid = b.get('thought_cid')
                resolvable = bcid in [x.cid for x in all_local]
                status = "✓ resolvable" if resolvable else "?"
                print(f"    because: {bcid[:40]}... {status}")

    print(f"\n" + "=" * 70)
    print("KEY INSIGHT:")
    print("=" * 70)
    print("""
  identity_thought.because → [secret_thought.cid]

  Remote verifier sees:
    - identity pubkey (can verify signatures)
    - reference to secret (can't resolve, that's fine)
    - all subsequent signatures verify against pubkey

  Local owner sees:
    - secret thought with privkey (can sign)
    - full chain from secret → identity → thoughts

  To revoke: delete the secret thought locally.
  You can still verify old signatures, but can't create new ones.

  To rotate: create new identity pair, attest equivalence from old identity.
""")

    print("=" * 70)


if __name__ == "__main__":
    main()
