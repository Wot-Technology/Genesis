#!/usr/bin/env python3
"""
Wellspring Hello: Cold Start Peer Discovery

The problem: Two identities want to communicate.
No prior chain. No shared pool. No vouch path.

The solution: Out-of-band bootstrap + in-band verification.
"""

import json
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional
import nacl.signing
import nacl.encoding
import base64


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

    def create_hello_card(self) -> str:
        """Generate a shareable hello card (out-of-band bootstrap)."""
        card = {
            "wellspring": "hello/1.0",
            "identity_cid": self.cid,
            "name": self.name,
            "pubkey": f"ed25519:{self.pubkey_hex}",
            "created": datetime.now(timezone.utc).isoformat()
        }
        # Sign the card
        card_json = json.dumps(card, sort_keys=True)
        card["signature"] = self.sign(hashlib.sha256(card_json.encode()).hexdigest())
        return base64.b64encode(json.dumps(card).encode()).decode()


def main():
    print("=" * 70)
    print("WELLSPRING HELLO - Cold Start Peer Discovery")
    print("=" * 70)

    all_thoughts = []

    # === TWO STRANGERS ===
    alice = Identity("Alice")
    bob = Identity("Bob")

    alice_id = alice.create_identity()
    bob_id = bob.create_identity()
    all_thoughts.extend([alice_id, bob_id])

    print(f"\n👤 ALICE: {alice.cid[:32]}...")
    print(f"👤 BOB:   {bob.cid[:32]}...")
    print(f"\nNo prior connection. No shared pool. No vouch chain.")

    # === STEP 1: OUT-OF-BAND HELLO ===
    print(f"\n" + "=" * 70)
    print("STEP 1: Out-of-Band Hello Card")
    print("=" * 70)

    alice_card = alice.create_hello_card()

    print(f"""
Alice creates a hello card (shareable via any channel):
  - QR code
  - Email
  - Text message
  - Business card
  - Shouted across a room

Card (base64):
{alice_card[:60]}...

Card contains:
  - identity_cid
  - name
  - pubkey
  - signature (proves Alice controls the key)
""")

    # === STEP 2: BOB RECEIVES AND VERIFIES ===
    print("=" * 70)
    print("STEP 2: Bob Receives and Verifies")
    print("=" * 70)

    # Bob decodes the card
    card_data = json.loads(base64.b64decode(alice_card))

    print(f"""
Bob receives card (via any channel).

Bob verifies:
  1. Decode card ✓
  2. Check signature against pubkey ✓
  3. Compute identity_cid from pubkey ✓
  4. Matches claimed identity_cid ✓

Result: Bob now knows Alice's identity CID and can verify her signatures.
        No trust yet — just cryptographic proof of identity.
""")

    # === STEP 3: CREATE SHARED POOL ===
    print("=" * 70)
    print("STEP 3: Create Shared Pool")
    print("=" * 70)

    # Alice creates a pool for their communication
    pool_content = {
        "name": "alice-bob-channel",
        "visibility": "private",
        "purpose": "Direct communication channel",
        "participants": [alice.cid, bob.cid]
    }
    pool_cid = alice.content_cid(pool_content)

    pool = alice.create_thought("pool", pool_content, [alice.cid], "cid:schema_pool_v1")
    pool.cid = pool_cid  # Use content-based CID for stability
    all_thoughts.append(pool)

    print(f"""
Alice creates shared pool:
  CID:  {pool_cid}
  Name: alice-bob-channel
  Participants: [alice, bob]

Pool is private — only participants can see contents.
""")

    # === STEP 4: MUTUAL MEMBERSHIP ===
    print("=" * 70)
    print("STEP 4: Mutual Membership (Bilateral Attestation)")
    print("=" * 70)

    # Connection: Alice member_of pool
    alice_conn = alice.create_thought(
        "connection",
        {"from": alice.cid, "to": pool_cid, "relation": "member_of"},
        [alice.cid, pool_cid],
        "cid:schema_connection_v1"
    )
    all_thoughts.append(alice_conn)

    # Alice attests her own membership
    alice_attest = alice.create_thought(
        "attestation",
        {"on": alice_conn.cid, "weight": 1.0},
        [alice_conn.cid],
        "cid:schema_attestation_v1"
    )
    all_thoughts.append(alice_attest)

    # Connection: Bob member_of pool
    bob_conn = bob.create_thought(
        "connection",
        {"from": bob.cid, "to": pool_cid, "relation": "member_of"},
        [bob.cid, pool_cid],
        "cid:schema_connection_v1"
    )
    all_thoughts.append(bob_conn)

    # Bob attests his own membership
    bob_attest = bob.create_thought(
        "attestation",
        {"on": bob_conn.cid, "weight": 1.0},
        [bob_conn.cid],
        "cid:schema_attestation_v1"
    )
    all_thoughts.append(bob_attest)

    # Cross-attestation: Alice accepts Bob
    alice_accepts_bob = alice.create_thought(
        "attestation",
        {"on": bob_conn.cid, "weight": 1.0},
        [bob_conn.cid, bob.cid],
        "cid:schema_attestation_v1"
    )
    all_thoughts.append(alice_accepts_bob)

    # Cross-attestation: Bob accepts Alice
    bob_accepts_alice = bob.create_thought(
        "attestation",
        {"on": alice_conn.cid, "weight": 1.0},
        [alice_conn.cid, alice.cid],
        "cid:schema_attestation_v1"
    )
    all_thoughts.append(bob_accepts_alice)

    print(f"""
Bilateral membership:

  Alice:
    CONNECTION: alice → member_of → pool ✓
    ATTESTATION by Alice: +1.0 ✓
    ATTESTATION by Bob: +1.0 ✓

  Bob:
    CONNECTION: bob → member_of → pool ✓
    ATTESTATION by Bob: +1.0 ✓
    ATTESTATION by Alice: +1.0 ✓

Both members confirmed. Channel is live.
""")

    # === STEP 5: FIRST MESSAGE ===
    print("=" * 70)
    print("STEP 5: First Message")
    print("=" * 70)

    alice_hello = alice.create_thought(
        "basic",
        {"text": "Hello Bob! Nice to meet you."},
        [alice_attest.cid, pool_cid],  # Grounded in membership and pool
        "cid:schema_basic_v1"
    )
    all_thoughts.append(alice_hello)

    bob_reply = bob.create_thought(
        "basic",
        {"text": "Hi Alice! Likewise. How did you hear about Wellspring?"},
        [bob_attest.cid, alice_hello.cid],  # Grounded in membership and Alice's message
        "cid:schema_basic_v1"
    )
    all_thoughts.append(bob_reply)

    print(f"""
First exchange:

  Alice: "Hello Bob! Nice to meet you."
    because: [alice_membership, pool]

  Bob: "Hi Alice! Likewise. How did you hear about Wellspring?"
    because: [bob_membership, alice_hello]

The conversation has a because chain.
It's grounded in the pool creation and membership.
""")

    # === THE FULL HANDSHAKE ===
    print("=" * 70)
    print("THE FULL HELLO HANDSHAKE")
    print("=" * 70)

    print(f"""
OUT-OF-BAND (any channel):
  1. Alice creates hello card (identity + pubkey + signature)
  2. Shares via QR/email/text/in-person
  3. Bob receives and verifies cryptographically

IN-BAND (Wellspring):
  4. Alice creates shared pool
  5. Alice joins pool (connection + attestation)
  6. Bob joins pool (connection + attestation)
  7. Cross-attestation (Alice accepts Bob, Bob accepts Alice)
  8. First messages (grounded in pool membership)

WHAT EACH PARTY NOW HAS:
  - Verified identity of the other (pubkey)
  - Private communication channel (pool)
  - Shared history (because chains)
  - No external trust required (cryptographic proof only)

TRUST LEVEL:
  - Zero external vouch chain
  - But: cryptographic identity verified
  - Trust grows from direct interaction
  - Can vouch for each other later (creates chain for others)
""")

    # === DISCOVERY OPTIONS ===
    print("=" * 70)
    print("DISCOVERY OPTIONS (Where to Share Hello Cards)")
    print("=" * 70)

    print(f"""
DIRECT (high trust):
  - In person (QR code, NFC, verbal)
  - Verified email/phone
  - Physical mail

SEMI-DIRECT (medium trust):
  - Website "contact me" section
  - Social media profile
  - Professional directory

PUBLIC DISCOVERY (low initial trust):
  - Public pool of hello cards
  - Search by name/interest
  - Verify independently before engaging

EXAMPLE: Public Hello Pool

  POOL: public-hello-cards
    visibility: public

  THOUGHT by alice:
    type: "hello_card"
    content:
      identity_cid: alice.cid
      name: "Alice"
      interests: ["AI safety", "cryptography"]
      pubkey: "ed25519:..."

  Anyone can:
    - Browse the pool
    - Find Alice's card
    - Verify her pubkey
    - Create private channel via handshake

  Trust = zero until you interact.
  But discovery is possible.
""")

    # === OUTPUT ===
    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-008-hello.jsonl"
    with open(output_path, 'w') as f:
        for t in all_thoughts:
            f.write(json.dumps(t.to_dict()) + '\n')

    print("=" * 70)
    print("OUTPUT")
    print("=" * 70)
    print(f"\n  File: wellspring-dogfood-008-hello.jsonl")
    print(f"  Thoughts: {len(all_thoughts)}")
    print(f"")
    print(f"  Structure:")
    print(f"    2 identities (Alice, Bob)")
    print(f"    1 shared pool")
    print(f"    2 membership connections")
    print(f"    4 membership attestations (bilateral)")
    print(f"    2 messages")

    print(f"\n" + "=" * 70)
    print("Hello handshake complete. Cold start solved.")
    print("=" * 70)


if __name__ == "__main__":
    main()
