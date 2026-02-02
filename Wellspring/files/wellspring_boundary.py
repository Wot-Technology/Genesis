#!/usr/bin/env python3
"""
Dogfood 015: Boundary Verification
Two isolated teams share in a third space.
Provenance trails hit pool walls gracefully.
"""

import json
import hashlib
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import base64

# ============================================================================
# CRYPTO UTILITIES
# ============================================================================

def pubkey_to_hex(pubkey: Ed25519PublicKey) -> str:
    return pubkey.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ).hex()

def hex_to_pubkey(hex_str: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_str))

def compute_cid(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    hash_bytes = hashlib.sha256(canonical.encode()).hexdigest()
    return f"baf_{hash_bytes[:32]}"

# ============================================================================
# SIGNED THOUGHT
# ============================================================================

@dataclass
class SignedThought:
    type: str
    content: dict
    created_by: str
    because: List[str] = field(default_factory=list)
    visibility: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    signature: Optional[str] = None
    cid: Optional[str] = None

    def sign(self, private_key: Ed25519PrivateKey):
        sign_data = {
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by,
            "because": self.because,
            "created_at": self.created_at
        }
        if self.visibility:
            sign_data["visibility"] = self.visibility

        message = json.dumps(sign_data, sort_keys=True, separators=(',', ':')).encode()
        sig_bytes = private_key.sign(message)
        self.signature = base64.b64encode(sig_bytes).decode()

        cid_data = {**sign_data, "signature": self.signature}
        self.cid = compute_cid(cid_data)

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

# ============================================================================
# CRYPTO IDENTITY
# ============================================================================

class CryptoIdentity:
    def __init__(self, name: str):
        self.name = name
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.pubkey_hex = pubkey_to_hex(self.public_key)

        self.identity_thought = SignedThought(
            type="identity",
            content={"name": name, "pubkey": self.pubkey_hex},
            created_by="GENESIS"
        )
        self.identity_thought.sign(self.private_key)
        self.cid = self.identity_thought.cid

    def create_thought(self, type: str, content: dict, because: List[str] = None,
                       visibility: str = None) -> SignedThought:
        thought = SignedThought(
            type=type,
            content=content,
            created_by=self.cid,
            because=because or [],
            visibility=visibility
        )
        thought.sign(self.private_key)
        return thought

# ============================================================================
# POOL (isolated thought store)
# ============================================================================

class Pool:
    def __init__(self, name: str, pool_cid: str):
        self.name = name
        self.pool_cid = pool_cid
        self.thoughts: Dict[str, dict] = {}  # cid -> thought
        self.pubkeys: Dict[str, str] = {}    # identity_cid -> pubkey

    def add_thought(self, thought: SignedThought):
        self.thoughts[thought.cid] = thought.to_dict()

    def add_identity(self, identity: CryptoIdentity):
        self.thoughts[identity.cid] = identity.identity_thought.to_dict()
        self.pubkeys[identity.cid] = identity.pubkey_hex

    def has_cid(self, cid: str) -> bool:
        return cid in self.thoughts

    def get_thought(self, cid: str) -> Optional[dict]:
        return self.thoughts.get(cid)

    def verify_chain(self, cid: str, depth: int = 0, indent: str = "") -> dict:
        """
        Verify a thought and its because chain.
        Returns verification status for each CID.
        """
        result = {
            "cid": cid[:20] + "...",
            "status": None,
            "reason": None,
            "because": []
        }

        # Can we even find this thought?
        thought = self.get_thought(cid)
        if not thought:
            result["status"] = "BOUNDARY"
            result["reason"] = "CID not in pool (outside our visibility)"
            return result

        # Can we verify the signature?
        created_by = thought["created_by"]

        if thought["type"] == "identity" and created_by == "GENESIS":
            pubkey_hex = thought["content"]["pubkey"]
        elif created_by in self.pubkeys:
            pubkey_hex = self.pubkeys[created_by]
        else:
            result["status"] = "BOUNDARY"
            result["reason"] = f"Unknown identity: {created_by[:20]}..."
            return result

        try:
            pubkey = hex_to_pubkey(pubkey_hex)
            sign_data = {
                "type": thought["type"],
                "content": thought["content"],
                "created_by": thought["created_by"],
                "because": thought["because"],
                "created_at": thought["created_at"]
            }
            if "visibility" in thought and thought["visibility"]:
                sign_data["visibility"] = thought["visibility"]

            message = json.dumps(sign_data, sort_keys=True, separators=(',', ':')).encode()
            sig_bytes = base64.b64decode(thought["signature"])
            pubkey.verify(sig_bytes, message)
            result["status"] = "VERIFIED"
        except Exception as e:
            result["status"] = "INVALID"
            result["reason"] = str(e)
            return result

        # Recurse into because chain
        if depth < 5:
            for because_cid in thought.get("because", []):
                child_result = self.verify_chain(because_cid, depth + 1, indent + "  ")
                result["because"].append(child_result)

        return result

def print_verification(result: dict, indent: str = ""):
    status_icon = {
        "VERIFIED": "✓",
        "BOUNDARY": "◯",
        "INVALID": "✗"
    }.get(result["status"], "?")

    print(f"{indent}{status_icon} {result['cid']}")
    if result["reason"]:
        print(f"{indent}  └─ {result['reason']}")

    for child in result.get("because", []):
        print_verification(child, indent + "  ")

# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("=" * 70)
    print("DOGFOOD 015: Boundary Verification")
    print("=" * 70)

    # ========================================================================
    # PHASE 1: Create two isolated teams
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Creating isolated teams")
    print("=" * 70)

    # Team Alpha
    alpha_lead = CryptoIdentity("Alpha-Lead")
    alpha_dev1 = CryptoIdentity("Alpha-Dev1")
    alpha_dev2 = CryptoIdentity("Alpha-Dev2")

    alpha_pool_thought = alpha_lead.create_thought(
        type="pool",
        content={"name": "Team Alpha Internal", "access": "private"},
        because=[alpha_lead.cid]
    )
    alpha_pool = Pool("Team Alpha", alpha_pool_thought.cid)

    # Add identities to Alpha pool
    alpha_pool.add_identity(alpha_lead)
    alpha_pool.add_identity(alpha_dev1)
    alpha_pool.add_identity(alpha_dev2)
    alpha_pool.add_thought(alpha_pool_thought)

    # Team Bravo
    bravo_lead = CryptoIdentity("Bravo-Lead")
    bravo_dev1 = CryptoIdentity("Bravo-Dev1")
    bravo_dev2 = CryptoIdentity("Bravo-Dev2")

    bravo_pool_thought = bravo_lead.create_thought(
        type="pool",
        content={"name": "Team Bravo Internal", "access": "private"},
        because=[bravo_lead.cid]
    )
    bravo_pool = Pool("Team Bravo", bravo_pool_thought.cid)

    # Add identities to Bravo pool
    bravo_pool.add_identity(bravo_lead)
    bravo_pool.add_identity(bravo_dev1)
    bravo_pool.add_identity(bravo_dev2)
    bravo_pool.add_thought(bravo_pool_thought)

    print(f"\n  Team Alpha: {alpha_lead.name}, {alpha_dev1.name}, {alpha_dev2.name}")
    print(f"  Team Bravo: {bravo_lead.name}, {bravo_dev1.name}, {bravo_dev2.name}")

    # ========================================================================
    # PHASE 2: Internal work (private to each team)
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Internal work (private)")
    print("=" * 70)

    # Alpha's internal research chain
    alpha_research1 = alpha_dev1.create_thought(
        type="research",
        content={"finding": "Initial hypothesis about X"},
        because=[alpha_dev1.cid],
        visibility=f"pool:{alpha_pool_thought.cid}"
    )
    alpha_pool.add_thought(alpha_research1)

    alpha_research2 = alpha_dev2.create_thought(
        type="research",
        content={"finding": "Experimental results confirm X"},
        because=[alpha_research1.cid, alpha_dev2.cid],
        visibility=f"pool:{alpha_pool_thought.cid}"
    )
    alpha_pool.add_thought(alpha_research2)

    alpha_conclusion = alpha_lead.create_thought(
        type="conclusion",
        content={"summary": "X is validated by experiments"},
        because=[alpha_research1.cid, alpha_research2.cid, alpha_lead.cid],
        visibility=f"pool:{alpha_pool_thought.cid}"
    )
    alpha_pool.add_thought(alpha_conclusion)

    print(f"\n  Alpha internal chain:")
    print(f"    Dev1 research → Dev2 validation → Lead conclusion")
    print(f"    Conclusion CID: {alpha_conclusion.cid[:20]}...")

    # Bravo's internal analysis chain
    bravo_analysis1 = bravo_dev1.create_thought(
        type="analysis",
        content={"finding": "Y shows promising results"},
        because=[bravo_dev1.cid],
        visibility=f"pool:{bravo_pool_thought.cid}"
    )
    bravo_pool.add_thought(bravo_analysis1)

    bravo_analysis2 = bravo_dev2.create_thought(
        type="analysis",
        content={"finding": "Y correlates with Z"},
        because=[bravo_analysis1.cid, bravo_dev2.cid],
        visibility=f"pool:{bravo_pool_thought.cid}"
    )
    bravo_pool.add_thought(bravo_analysis2)

    bravo_conclusion = bravo_lead.create_thought(
        type="conclusion",
        content={"summary": "Y+Z relationship confirmed"},
        because=[bravo_analysis1.cid, bravo_analysis2.cid, bravo_lead.cid],
        visibility=f"pool:{bravo_pool_thought.cid}"
    )
    bravo_pool.add_thought(bravo_conclusion)

    print(f"\n  Bravo internal chain:")
    print(f"    Dev1 analysis → Dev2 correlation → Lead conclusion")
    print(f"    Conclusion CID: {bravo_conclusion.cid[:20]}...")

    # ========================================================================
    # PHASE 3: Create shared collaboration space
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Creating shared collaboration space")
    print("=" * 70)

    # Shared pool created jointly
    shared_pool_thought = alpha_lead.create_thought(
        type="pool",
        content={"name": "Alpha-Bravo Collaboration", "access": "shared"},
        because=[alpha_lead.cid]
    )

    shared_pool = Pool("Shared Space", shared_pool_thought.cid)
    shared_pool.add_thought(shared_pool_thought)

    # Both leads join with their public identities
    shared_pool.add_identity(alpha_lead)
    shared_pool.add_identity(bravo_lead)

    # Bravo attests joining
    bravo_join = bravo_lead.create_thought(
        type="attestation",
        content={"on": shared_pool_thought.cid, "weight": 1.0, "aspect": "membership"},
        because=[bravo_lead.cid, shared_pool_thought.cid]
    )
    shared_pool.add_thought(bravo_join)

    print(f"\n  Shared pool: {shared_pool_thought.cid[:20]}...")
    print(f"  Members: Alpha-Lead, Bravo-Lead")

    # ========================================================================
    # PHASE 4: Teams publish summaries to shared space
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: Publishing summaries to shared space")
    print("=" * 70)

    # Alpha publishes their conclusion (references internal work!)
    alpha_public = alpha_lead.create_thought(
        type="publication",
        content={
            "title": "Team Alpha: X Validation Report",
            "summary": "We validated hypothesis X through experimentation",
            "internal_refs": [alpha_research1.cid, alpha_research2.cid]  # Visible as CIDs
        },
        because=[alpha_conclusion.cid, alpha_lead.cid]  # References PRIVATE conclusion!
    )
    shared_pool.add_thought(alpha_public)

    print(f"\n  Alpha published: {alpha_public.cid[:20]}...")
    print(f"    because → [{alpha_conclusion.cid[:16]}...] (PRIVATE)")

    # Bravo publishes their conclusion
    bravo_public = bravo_lead.create_thought(
        type="publication",
        content={
            "title": "Team Bravo: Y+Z Correlation Study",
            "summary": "Y and Z show strong correlation",
            "internal_refs": [bravo_analysis1.cid, bravo_analysis2.cid]
        },
        because=[bravo_conclusion.cid, bravo_lead.cid]  # References PRIVATE conclusion!
    )
    shared_pool.add_thought(bravo_public)

    print(f"\n  Bravo published: {bravo_public.cid[:20]}...")
    print(f"    because → [{bravo_conclusion.cid[:16]}...] (PRIVATE)")

    # ========================================================================
    # PHASE 5: Cross-team collaboration (building on each other)
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: Cross-team collaboration")
    print("=" * 70)

    # Alpha builds on Bravo's work
    joint_insight = alpha_lead.create_thought(
        type="insight",
        content={
            "title": "X and Y+Z Connection",
            "finding": "Our X validation may explain Bravo's Y+Z correlation"
        },
        because=[alpha_public.cid, bravo_public.cid]  # Both publications
    )
    shared_pool.add_thought(joint_insight)

    print(f"\n  Joint insight: {joint_insight.cid[:20]}...")
    print(f"    because → [Alpha pub, Bravo pub]")

    # ========================================================================
    # PHASE 6: Verification from different perspectives
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 6: Verification from different perspectives")
    print("=" * 70)

    # --- Shared space view ---
    print("\n  FROM SHARED SPACE (limited visibility):")
    print("  " + "-" * 50)
    print(f"\n  Verifying joint insight...")
    result = shared_pool.verify_chain(joint_insight.cid)
    print_verification(result, "    ")

    print(f"\n  Verifying Alpha publication...")
    result = shared_pool.verify_chain(alpha_public.cid)
    print_verification(result, "    ")

    print(f"\n  Verifying Bravo publication...")
    result = shared_pool.verify_chain(bravo_public.cid)
    print_verification(result, "    ")

    # --- Alpha's view (can see their internals) ---
    print("\n  FROM ALPHA'S PERSPECTIVE (can see Alpha internals):")
    print("  " + "-" * 50)

    # Alpha pool has shared space content too (they synced it)
    alpha_pool.add_thought(shared_pool_thought)
    alpha_pool.add_thought(bravo_join)
    alpha_pool.add_thought(alpha_public)
    alpha_pool.add_thought(bravo_public)
    alpha_pool.add_thought(joint_insight)
    alpha_pool.add_identity(bravo_lead)  # They know Bravo lead from shared

    print(f"\n  Verifying joint insight...")
    result = alpha_pool.verify_chain(joint_insight.cid)
    print_verification(result, "    ")

    print(f"\n  Verifying Alpha publication (FULL CHAIN)...")
    result = alpha_pool.verify_chain(alpha_public.cid)
    print_verification(result, "    ")

    # --- Bravo's view ---
    print("\n  FROM BRAVO'S PERSPECTIVE (can see Bravo internals):")
    print("  " + "-" * 50)

    bravo_pool.add_thought(shared_pool_thought)
    bravo_pool.add_thought(bravo_join)
    bravo_pool.add_thought(alpha_public)
    bravo_pool.add_thought(bravo_public)
    bravo_pool.add_thought(joint_insight)
    bravo_pool.add_identity(alpha_lead)

    print(f"\n  Verifying Bravo publication (FULL CHAIN)...")
    result = bravo_pool.verify_chain(bravo_public.cid)
    print_verification(result, "    ")

    print(f"\n  Verifying Alpha publication (BOUNDARY)...")
    result = bravo_pool.verify_chain(alpha_public.cid)
    print_verification(result, "    ")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("""
  Boundary verification works as expected:

  ✓ VERIFIED  = Signature valid, we have the thought
  ◯ BOUNDARY  = CID referenced but thought not in our pool
                (outside our visibility - that's the wall)

  Key observations:

  1. Publications are VERIFIED in shared space
     - We can verify Alpha-Lead signed it
     - We can see it references internal work (CIDs visible)
     - We CANNOT verify the internal work (boundary hit)

  2. The because chain shows provenance structure
     - joint_insight → [alpha_pub, bravo_pub] → [internal work]
     - The shape is visible even when content isn't

  3. Each team can verify their own full chain
     - Alpha verifies Alpha's work: FULL DEPTH
     - Alpha verifies Bravo's work: BOUNDARY at Bravo's internals

  4. Boundary is GRACEFUL, not failure
     - It's information: "this references work I can't see"
     - Trust the boundary identity to have done their verification
     - The rep's signature IS the trust anchor

  This is the model:
    ┌─────────────────┐     ┌─────────────────┐
    │   ALPHA POOL    │     │   BRAVO POOL    │
    │  (full verify)  │     │  (full verify)  │
    └────────┬────────┘     └────────┬────────┘
             │                       │
             ▼                       ▼
    ┌─────────────────────────────────────────┐
    │           SHARED SPACE                   │
    │  (verify signatures, boundary on refs)   │
    └─────────────────────────────────────────┘
    """)

    # Write output
    all_thoughts = []
    for pool in [alpha_pool, bravo_pool, shared_pool]:
        for thought in pool.thoughts.values():
            if thought["cid"] not in [t["cid"] for t in all_thoughts]:
                all_thoughts.append(thought)

    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-015-boundary.jsonl"
    with open(output_path, 'w') as f:
        for thought in all_thoughts:
            f.write(json.dumps(thought) + '\n')

    print(f"Wrote {len(all_thoughts)} thoughts to:")
    print(f"  {output_path}")

if __name__ == "__main__":
    main()
