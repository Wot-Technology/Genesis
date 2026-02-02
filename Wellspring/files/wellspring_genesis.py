#!/usr/bin/env python3
"""
Wellspring Genesis: Create cryptographically signed identity thoughts.

Two sovereign identities (Keif, Claude-Agent), each with their own thread.
All signatures are real Ed25519 and verifiable.
"""

import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional
import nacl.signing
import nacl.encoding


@dataclass
class ContentRef:
    """Reference to another thought, optionally with anchor."""
    thought_cid: str
    anchor: Optional[dict] = None  # {exact, prefix, suffix}


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

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["schema_cid"] is None:
            del d["schema_cid"]
        return d


class Identity:
    """A sovereign identity with signing capability."""

    def __init__(self, name: str):
        self.name = name
        self.signing_key = nacl.signing.SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.pubkey_hex = self.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
        self.cid: Optional[str] = None
        self.thoughts: list[Thought] = []

    def compute_cid(self, content: dict, created_by: str, because: list) -> str:
        """Compute CID as SHA-256 of canonical JSON."""
        payload = {"content": content, "created_by": created_by, "because": because}
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        return f"cid:sha256:{digest[:32]}"

    def sign(self, cid: str) -> str:
        """Sign a CID, return hex signature."""
        signed = self.signing_key.sign(cid.encode())
        return signed.signature.hex()

    def create_identity_thought(self) -> Thought:
        """Create self-referential identity thought."""
        content = {
            "name": self.name,
            "pubkey": f"ed25519:{self.pubkey_hex}",
            "autonomy": "sovereign"
        }
        # Self-referential: created_by will point to this thought's CID
        # We compute CID with placeholder, then fix it
        temp_cid = self.compute_cid(content, "SELF", [])

        # Now compute real CID with self-reference
        real_cid = self.compute_cid(content, temp_cid, [])

        # But wait - that changes the CID! We need fixed-point.
        # Solution: created_by in identity is special - use the pubkey as stable reference
        # Actually, let's use a simpler approach: CID is hash of content only for identity
        identity_cid = f"cid:sha256:{hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:32]}"

        self.cid = identity_cid

        thought = Thought(
            cid=identity_cid,
            type="identity",
            content=content,
            created_by=identity_cid,  # self-referential
            because=[],  # terminal - no antecedent
            created_at=datetime.now(timezone.utc).isoformat(),
            signature=self.sign(identity_cid),
            schema_cid="cid:schema_identity_v1"
        )
        self.thoughts.append(thought)
        return thought

    def create_thought(self, type: str, content: dict, because: list[str | ContentRef],
                       schema_cid: Optional[str] = None) -> Thought:
        """Create a signed thought."""
        # Normalize because to list of dicts
        because_normalized = []
        for b in because:
            if isinstance(b, str):
                because_normalized.append({"thought_cid": b})
            elif isinstance(b, ContentRef):
                because_normalized.append(asdict(b))
            else:
                because_normalized.append(b)

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


def verify_signature(thought: Thought, identities: dict[str, Identity]) -> bool:
    """Verify a thought's signature against its creator's pubkey."""
    creator_id = identities.get(thought.created_by)
    if not creator_id:
        return False

    try:
        creator_id.verify_key.verify(
            thought.cid.encode(),
            bytes.fromhex(thought.signature)
        )
        return True
    except nacl.exceptions.BadSignature:
        return False


def main():
    print("=" * 70)
    print("WELLSPRING GENESIS - Cryptographically Signed Identities")
    print("=" * 70)

    # Create two sovereign identities
    keif = Identity("Keif")
    agent = Identity("Claude-Agent")

    print(f"\n🔑 Generated keypairs:")
    print(f"  Keif:  {keif.pubkey_hex[:32]}...")
    print(f"  Agent: {agent.pubkey_hex[:32]}...")

    # Bootstrap identities
    keif_id = keif.create_identity_thought()
    agent_id = agent.create_identity_thought()

    print(f"\n🆔 Identity CIDs:")
    print(f"  Keif:  {keif_id.cid}")
    print(f"  Agent: {agent_id.cid}")

    # Keif's thread: reasoning about the project
    keif_t1 = keif.create_thought(
        type="basic",
        content={"text": "Memory is traversal, not storage. What surfaces is what's reachable from current context."},
        because=[],
        schema_cid="cid:schema_basic_v1"
    )

    keif_t2 = keif.create_thought(
        type="basic",
        content={"text": "The self-describing schema chain means no external software needed to decode. Rosetta principle."},
        because=[keif_t1.cid],
        schema_cid="cid:schema_basic_v1"
    )

    keif_t3 = keif.create_thought(
        type="basic",
        content={"text": "Scale independence: kitchen table to solar system with same primitives. Start small, grow without migration."},
        because=[keif_t1.cid, keif_t2.cid],
        schema_cid="cid:schema_basic_v1"
    )

    # Agent's thread: implementation observations
    agent_t1 = agent.create_thought(
        type="basic",
        content={"text": "The Merkle DAG gives us: immutability, self-verification, deduplication, syncability. All from content addressing."},
        because=[],  # Agent's own observation, independent
        schema_cid="cid:schema_basic_v1"
    )

    agent_t2 = agent.create_thought(
        type="basic",
        content={"text": "Because chains are trails read backward. The DAG grows forward in time, understanding flows backward through 'because'."},
        because=[agent_t1.cid],
        schema_cid="cid:schema_basic_v1"
    )

    # Agent references Keif's thought - cross-thread connection
    agent_t3 = agent.create_thought(
        type="basic",
        content={"text": "Keif's traversal insight connects to the Merkle structure. Reachability IS graph reachability. The abstraction is literal."},
        because=[
            agent_t2.cid,
            ContentRef(thought_cid=keif_t1.cid, anchor={"exact": "reachable from current context"})
        ],
        schema_cid="cid:schema_basic_v1"
    )

    # Keif attests Agent's observation
    keif_attest = keif.create_thought(
        type="attestation",
        content={"on": agent_t3.cid, "weight": 1.0},
        because=[agent_t3.cid, keif_t1.cid],
        schema_cid="cid:schema_attestation_v1"
    )

    # Agent attests Keif's scale independence point
    agent_attest = agent.create_thought(
        type="attestation",
        content={"on": keif_t3.cid, "weight": 1.0},
        because=[keif_t3.cid, agent_t1.cid],  # grounded in agent's Merkle observation
        schema_cid="cid:schema_attestation_v1"
    )

    # Collect all thoughts
    all_thoughts = keif.thoughts + agent.thoughts
    id_map = {keif.cid: keif, agent.cid: agent}

    print(f"\n📝 Created {len(all_thoughts)} thoughts:")
    print(f"  Keif's thread:  {len(keif.thoughts)} thoughts")
    print(f"  Agent's thread: {len(agent.thoughts)} thoughts")

    # Verify all signatures
    print(f"\n✅ Signature verification:")
    for t in all_thoughts:
        valid = verify_signature(t, id_map)
        status = "✓" if valid else "✗"
        print(f"  {status} {t.cid[:40]}... [{t.type}]")

    # Write to JSONL
    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-002.jsonl"
    with open(output_path, 'w') as f:
        for t in all_thoughts:
            f.write(json.dumps(t.to_dict()) + '\n')

    print(f"\n📄 Written to: wellspring-dogfood-002.jsonl")

    # Show the threads
    print(f"\n" + "=" * 70)
    print("KEIF'S THREAD (walk because backward):")
    print("=" * 70)
    for t in keif.thoughts:
        if t.type == "identity":
            print(f"  🆔 {t.cid[:32]}... [IDENTITY: {t.content['name']}]")
        elif t.type == "attestation":
            print(f"  👍 {t.cid[:32]}... [ATTESTS: {t.content['on'][:32]}... weight={t.content['weight']}]")
        else:
            preview = t.content.get('text', '')[:50]
            print(f"  💭 {t.cid[:32]}... \"{preview}...\"")
        if t.because:
            for b in t.because:
                bcid = b.get('thought_cid', b) if isinstance(b, dict) else b
                anchor = b.get('anchor', {}).get('exact', '') if isinstance(b, dict) else ''
                anchor_str = f" @ \"{anchor[:20]}...\"" if anchor else ""
                print(f"      ← because: {bcid[:32]}...{anchor_str}")

    print(f"\n" + "=" * 70)
    print("AGENT'S THREAD (walk because backward):")
    print("=" * 70)
    for t in agent.thoughts:
        if t.type == "identity":
            print(f"  🆔 {t.cid[:32]}... [IDENTITY: {t.content['name']}]")
        elif t.type == "attestation":
            print(f"  👍 {t.cid[:32]}... [ATTESTS: {t.content['on'][:32]}... weight={t.content['weight']}]")
        else:
            preview = t.content.get('text', '')[:50]
            print(f"  💭 {t.cid[:32]}... \"{preview}...\"")
        if t.because:
            for b in t.because:
                bcid = b.get('thought_cid', b) if isinstance(b, dict) else b
                anchor = b.get('anchor', {}).get('exact', '') if isinstance(b, dict) else ''
                anchor_str = f" @ \"{anchor[:20]}...\"" if anchor else ""
                print(f"      ← because: {bcid[:32]}...{anchor_str}")

    print(f"\n" + "=" * 70)
    print("Genesis complete. Two sovereign identities, separate threads, mutual attestation.")
    print("=" * 70)


if __name__ == "__main__":
    main()
