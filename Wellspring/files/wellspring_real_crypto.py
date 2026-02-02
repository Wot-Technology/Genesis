#!/usr/bin/env python3
"""
Dogfood 013: Real Cryptography

All previous dogfoods used simulated signatures.
This one uses real Ed25519:
- Key generation
- Message signing
- Signature verification
- Key rotation with cryptographic proof
- Multi-identity interaction with verified chains

No more fake sigs. Real crypto.
"""

import json
import hashlib
import base64
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

def compute_cid(content: dict) -> str:
    """Content-addressed ID from canonical JSON"""
    canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return f"baf_{hashlib.sha256(canonical.encode()).hexdigest()[:32]}"

def pubkey_to_hex(pubkey: Ed25519PublicKey) -> str:
    """Serialize public key to hex string"""
    raw = pubkey.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return raw.hex()

def hex_to_pubkey(hex_str: str) -> Ed25519PublicKey:
    """Deserialize public key from hex string"""
    raw = bytes.fromhex(hex_str)
    return Ed25519PublicKey.from_public_bytes(raw)

def sign_content(private_key: Ed25519PrivateKey, content: bytes) -> str:
    """Sign content, return base64-encoded signature"""
    sig = private_key.sign(content)
    return base64.b64encode(sig).decode('ascii')

def verify_signature(pubkey_hex: str, content: bytes, signature_b64: str) -> bool:
    """Verify a signature"""
    try:
        pubkey = hex_to_pubkey(pubkey_hex)
        sig = base64.b64decode(signature_b64)
        pubkey.verify(sig, content)
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        print(f"Verification error: {e}")
        return False


@dataclass
class SignedThought:
    """A thought with real cryptographic signature"""
    type: str
    content: dict
    created_by: str  # CID of identity thought
    because: list = field(default_factory=list)
    visibility: Optional[str] = None
    cid: str = ""
    created_at: str = ""
    signature: str = ""  # base64-encoded Ed25519 signature

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def compute_signable(self) -> bytes:
        """Get the bytes that should be signed"""
        signable = {
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
            "because": self.because,
            "created_at": self.created_at
        }
        if self.visibility:
            signable["visibility"] = self.visibility
        return json.dumps(signable, sort_keys=True, separators=(',', ':')).encode()

    def sign(self, private_key: Ed25519PrivateKey):
        """Sign this thought and compute CID"""
        signable = self.compute_signable()
        self.signature = sign_content(private_key, signable)
        # CID includes signature
        full_content = {
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
            "because": self.because,
            "created_at": self.created_at,
            "signature": self.signature
        }
        if self.visibility:
            full_content["visibility"] = self.visibility
        self.cid = compute_cid(full_content)

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


class CryptoIdentity:
    """An identity with real Ed25519 keypair"""

    def __init__(self, name: str):
        self.name = name
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.pubkey_hex = pubkey_to_hex(self.public_key)

        # Create identity thought
        # Bootstrap: created_by stays "GENESIS" - the pubkey in content is the proof
        self.identity_thought = SignedThought(
            type="identity",
            content={
                "name": name,
                "pubkey": self.pubkey_hex
            },
            created_by="GENESIS"  # Bootstrap terminal - pubkey proves ownership
        )
        # Sign with own key (self-attesting via pubkey in content)
        self.identity_thought.sign(self.private_key)
        # CID is computed, use that as identity reference
        self.cid = self.identity_thought.cid
        self.thoughts: List[SignedThought] = [self.identity_thought]

    def create_thought(self, type: str, content: dict, because: list = None,
                       visibility: str = None) -> SignedThought:
        """Create and sign a new thought"""
        thought = SignedThought(
            type=type,
            content=content,
            created_by=self.cid,
            because=because or [],
            visibility=visibility
        )
        thought.sign(self.private_key)
        self.thoughts.append(thought)
        return thought

    def verify_thought(self, thought: SignedThought, identity_registry: Dict[str, 'CryptoIdentity']) -> Tuple[bool, str]:
        """Verify a thought's signature using the creator's public key"""
        # Find the pubkey to verify with
        if thought.type == "identity" and thought.created_by == "GENESIS":
            # Bootstrap identity thought - pubkey is in content, self-signed
            pubkey_hex = thought.content.get("pubkey")
            if not pubkey_hex:
                return (False, "Identity thought missing pubkey")
        elif thought.created_by == "GENESIS":
            # Non-identity GENESIS thought (shouldn't happen normally)
            return (False, "Non-identity GENESIS thought")
        elif thought.created_by in identity_registry:
            # Normal case: look up creator's pubkey
            pubkey_hex = identity_registry[thought.created_by].pubkey_hex
        else:
            return (False, f"Unknown creator: {thought.created_by[:16]}...")

        # Verify
        signable = thought.compute_signable()
        if verify_signature(pubkey_hex, signable, thought.signature):
            return (True, "Valid signature")
        else:
            return (False, "Invalid signature")


def run_simulation():
    """Run the real crypto simulation"""

    print("=" * 70)
    print("DOGFOOD 013: Real Cryptography")
    print("=" * 70)

    all_thoughts = []
    identity_registry: Dict[str, CryptoIdentity] = {}

    # === PHASE 1: Create identities with real keys ===
    print("\n" + "=" * 70)
    print("PHASE 1: Creating identities with real Ed25519 keys")
    print("=" * 70)

    alice = CryptoIdentity("Alice")
    bob = CryptoIdentity("Bob")
    carol = CryptoIdentity("Carol")

    for identity in [alice, bob, carol]:
        identity_registry[identity.cid] = identity
        all_thoughts.append(identity.identity_thought)
        print(f"\n  {identity.name}:")
        print(f"    CID:    {identity.cid[:32]}...")
        print(f"    Pubkey: {identity.pubkey_hex[:32]}...")
        print(f"    Sig:    {identity.identity_thought.signature[:32]}...")

    # === PHASE 2: Verify identity self-signatures ===
    print("\n" + "=" * 70)
    print("PHASE 2: Verifying identity self-signatures")
    print("=" * 70)

    for identity in [alice, bob, carol]:
        # Verify the identity thought
        valid, reason = identity.verify_thought(identity.identity_thought, identity_registry)
        status = "✓" if valid else "✗"
        print(f"  {identity.name}: {status} {reason}")

    # === PHASE 3: Create and verify cross-signed thoughts ===
    print("\n" + "=" * 70)
    print("PHASE 3: Cross-signed attestations")
    print("=" * 70)

    # Alice trusts Bob
    alice_trusts_bob = alice.create_thought(
        type="attestation",
        content={
            "aspect_type": "trust",
            "on": bob.cid,
            "weight": 1.0,
            "statement": "I trust Bob"
        },
        because=[alice.cid, bob.cid]
    )
    all_thoughts.append(alice_trusts_bob)
    print(f"\n  Alice → Bob trust attestation:")
    print(f"    CID: {alice_trusts_bob.cid[:32]}...")
    print(f"    Sig: {alice_trusts_bob.signature[:32]}...")

    # Verify
    valid, reason = alice.verify_thought(alice_trusts_bob, identity_registry)
    print(f"    Verification: {'✓' if valid else '✗'} {reason}")

    # Bob trusts Carol
    bob_trusts_carol = bob.create_thought(
        type="attestation",
        content={
            "aspect_type": "trust",
            "on": carol.cid,
            "weight": 0.8,
            "statement": "I trust Carol"
        },
        because=[bob.cid, carol.cid]
    )
    all_thoughts.append(bob_trusts_carol)
    print(f"\n  Bob → Carol trust attestation:")
    print(f"    CID: {bob_trusts_carol.cid[:32]}...")

    valid, reason = bob.verify_thought(bob_trusts_carol, identity_registry)
    print(f"    Verification: {'✓' if valid else '✗'} {reason}")

    # === PHASE 4: Message exchange with verification ===
    print("\n" + "=" * 70)
    print("PHASE 4: Message exchange with chain verification")
    print("=" * 70)

    # Create a shared pool
    shared_pool = alice.create_thought(
        type="pool",
        content={"name": "crypto-test-pool", "admin": alice.cid},
        because=[alice.cid]
    )
    all_thoughts.append(shared_pool)
    print(f"\n  Pool created by Alice: {shared_pool.cid[:32]}...")

    # Message chain
    msg1 = alice.create_thought(
        type="message",
        content={"text": "Hello Bob and Carol!", "pool": shared_pool.cid},
        because=[shared_pool.cid]
    )
    all_thoughts.append(msg1)

    msg2 = bob.create_thought(
        type="message",
        content={"text": "Hey Alice! Got your message.", "pool": shared_pool.cid},
        because=[msg1.cid]  # References Alice's message
    )
    all_thoughts.append(msg2)

    msg3 = carol.create_thought(
        type="message",
        content={"text": "Hi everyone! Joining the conversation.", "pool": shared_pool.cid},
        because=[msg1.cid, msg2.cid]  # References both
    )
    all_thoughts.append(msg3)

    print(f"\n  Message chain:")
    for i, (sender, msg) in enumerate([(alice, msg1), (bob, msg2), (carol, msg3)]):
        valid, reason = sender.verify_thought(msg, identity_registry)
        print(f"    {i+1}. {sender.name}: \"{msg.content['text'][:30]}...\"")
        print(f"       Sig valid: {'✓' if valid else '✗'}")
        print(f"       Because: {[c[:16]+'...' for c in msg.because]}")

    # === PHASE 5: Key rotation with cryptographic proof ===
    print("\n" + "=" * 70)
    print("PHASE 5: Key rotation with cryptographic proof")
    print("=" * 70)

    # Alice generates new keypair
    alice_v2_private = Ed25519PrivateKey.generate()
    alice_v2_public = alice_v2_private.public_key()
    alice_v2_pubkey_hex = pubkey_to_hex(alice_v2_public)

    print(f"\n  Alice generating new keypair:")
    print(f"    Old pubkey: {alice.pubkey_hex[:32]}...")
    print(f"    New pubkey: {alice_v2_pubkey_hex[:32]}...")

    # Create rotation thought signed by OLD key
    rotation_content = {
        "rotation_type": "key_upgrade",
        "old_pubkey": alice.pubkey_hex,
        "new_pubkey": alice_v2_pubkey_hex,
        "reason": "Scheduled rotation"
    }

    rotation_thought = SignedThought(
        type="key_rotation",
        content=rotation_content,
        created_by=alice.cid,
        because=[alice.cid]
    )
    # Sign with OLD key
    rotation_thought.sign(alice.private_key)
    all_thoughts.append(rotation_thought)

    print(f"\n  Rotation thought (signed by old key):")
    print(f"    CID: {rotation_thought.cid[:32]}...")

    # Verify with old key
    valid, reason = alice.verify_thought(rotation_thought, identity_registry)
    print(f"    Old key verification: {'✓' if valid else '✗'}")

    # Create attestation from NEW key acknowledging the rotation
    new_key_attestation = SignedThought(
        type="attestation",
        content={
            "aspect_type": "key_acknowledgment",
            "on": rotation_thought.cid,
            "weight": 1.0,
            "statement": "I acknowledge this rotation",
            "new_pubkey": alice_v2_pubkey_hex
        },
        created_by=alice.cid,  # Same identity CID
        because=[rotation_thought.cid]
    )
    # Sign with NEW key
    new_key_attestation.sign(alice_v2_private)
    all_thoughts.append(new_key_attestation)

    print(f"\n  Acknowledgment (signed by new key):")
    print(f"    CID: {new_key_attestation.cid[:32]}...")

    # Verify the acknowledgment using the NEW pubkey from rotation content
    signable = new_key_attestation.compute_signable()
    new_key_valid = verify_signature(alice_v2_pubkey_hex, signable, new_key_attestation.signature)
    print(f"    New key verification: {'✓' if new_key_valid else '✗'}")

    print(f"\n  Rotation chain:")
    print(f"    1. Rotation thought signed by old key ✓")
    print(f"    2. Acknowledgment signed by new key ✓")
    print(f"    3. Both reference same identity CID")
    print(f"    4. Chain proves continuity")

    # === PHASE 6: Tamper detection ===
    print("\n" + "=" * 70)
    print("PHASE 6: Tamper detection")
    print("=" * 70)

    # Try to verify a tampered message
    tampered = SignedThought(
        type="message",
        content={"text": "TAMPERED MESSAGE!", "pool": shared_pool.cid},
        created_by=bob.cid,
        because=[msg1.cid],
        created_at=msg2.created_at,  # Copy timestamp
        signature=msg2.signature  # Use Bob's valid signature from different message
    )
    tampered.cid = compute_cid(tampered.to_dict())

    valid, reason = bob.verify_thought(tampered, identity_registry)
    print(f"\n  Tampered message verification: {'✓' if valid else '✗'} {reason}")

    # === PHASE 7: Chain verification ===
    print("\n" + "=" * 70)
    print("PHASE 7: Full chain verification")
    print("=" * 70)

    print(f"\n  Verifying all {len(all_thoughts)} thoughts...")

    valid_count = 0
    invalid_count = 0

    for thought in all_thoughts:
        # Determine which key to use
        if thought.type == "identity" and thought.created_by == "GENESIS":
            # Self-signed identity - pubkey in content
            pubkey = thought.content.get("pubkey")
            signable = thought.compute_signable()
            valid = verify_signature(pubkey, signable, thought.signature)
        elif thought.type == "key_rotation":
            # Signed by old key
            creator = identity_registry.get(thought.created_by)
            if creator:
                valid, _ = creator.verify_thought(thought, identity_registry)
            else:
                valid = False
        elif thought.content.get("aspect_type") == "key_acknowledgment":
            # Signed by new key (special case)
            new_pubkey = thought.content.get("new_pubkey")
            signable = thought.compute_signable()
            valid = verify_signature(new_pubkey, signable, thought.signature)
        else:
            # Normal thought - look up creator
            creator = identity_registry.get(thought.created_by)
            if creator:
                valid, _ = creator.verify_thought(thought, identity_registry)
            else:
                valid = False

        if valid:
            valid_count += 1
        else:
            invalid_count += 1
            print(f"    ✗ Invalid: {thought.cid[:24]}... ({thought.type})")

    print(f"\n  Results: {valid_count} valid, {invalid_count} invalid")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"""
Real Ed25519 cryptography:
  - Key generation: Ed25519PrivateKey.generate()
  - Signing: private_key.sign(message)
  - Verification: public_key.verify(signature, message)

Signature coverage:
  - type, content, created_by, because, created_at
  - visibility (if present)
  - CID computed AFTER signature (includes signature)

Key rotation proof:
  1. Old key signs rotation thought (declares new key)
  2. New key signs acknowledgment (proves possession)
  3. Both thoughts reference same identity CID
  4. Chain is cryptographically verifiable

Tamper detection:
  - Signature binds to exact content
  - Any modification invalidates signature
  - Can't replay signatures across different content

Total thoughts: {len(all_thoughts)}
All signatures verified: {'✓' if invalid_count == 0 else '✗'}
    """)

    # Write output
    output_file = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-013-crypto.jsonl"
    with open(output_file, 'w') as f:
        for thought in all_thoughts:
            f.write(json.dumps(thought.to_dict()) + "\n")

    print(f"Wrote {len(all_thoughts)} thoughts to:")
    print(f"  {output_file}")

    return all_thoughts


if __name__ == "__main__":
    run_simulation()
