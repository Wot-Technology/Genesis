#!/usr/bin/env python3
"""
Dogfood 014: Speed Test with Real Cryptography
50 identities, real Ed25519, single-threaded, unoptimized
"""

import json
import hashlib
import time
import random
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
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

        # CID includes signature
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

        # Bootstrap identity
        self.identity_thought = SignedThought(
            type="identity",
            content={"name": name, "pubkey": self.pubkey_hex},
            created_by="GENESIS"
        )
        self.identity_thought.sign(self.private_key)
        self.cid = self.identity_thought.cid

    def create_thought(self, type: str, content: dict, because: List[str] = None) -> SignedThought:
        thought = SignedThought(
            type=type,
            content=content,
            created_by=self.cid,
            because=because or []
        )
        thought.sign(self.private_key)
        return thought

# ============================================================================
# VERIFICATION
# ============================================================================

def verify_signature(thought: dict, pubkey_registry: Dict[str, str]) -> bool:
    """Verify a thought's signature against known pubkeys."""
    created_by = thought["created_by"]

    # Identity bootstrap: pubkey is in content
    if thought["type"] == "identity" and created_by == "GENESIS":
        pubkey_hex = thought["content"]["pubkey"]
    else:
        if created_by not in pubkey_registry:
            return False
        pubkey_hex = pubkey_registry[created_by]

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
        return True
    except (InvalidSignature, Exception):
        return False

# ============================================================================
# TRUST GRAPH
# ============================================================================

class TrustGraph:
    def __init__(self):
        self.edges: Dict[str, Dict[str, float]] = {}  # from -> {to -> weight}
        self.cache: Dict[Tuple[str, str], float] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def add_edge(self, from_cid: str, to_cid: str, weight: float):
        if from_cid not in self.edges:
            self.edges[from_cid] = {}
        self.edges[from_cid][to_cid] = weight
        self.cache.clear()  # Invalidate on change

    def compute_trust(self, from_cid: str, to_cid: str, visited: Set[str] = None, depth: int = 0) -> float:
        if from_cid == to_cid:
            return 1.0

        cache_key = (from_cid, to_cid)
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
        self.cache_misses += 1

        if visited is None:
            visited = set()

        if from_cid in visited or depth > 5:
            return 0.0

        visited.add(from_cid)

        # Direct edge?
        if from_cid in self.edges and to_cid in self.edges[from_cid]:
            trust = self.edges[from_cid][to_cid]
            self.cache[cache_key] = trust
            return trust

        # Transitive
        if from_cid not in self.edges:
            self.cache[cache_key] = 0.0
            return 0.0

        max_trust = 0.0
        for intermediate, weight in self.edges[from_cid].items():
            if weight > 0:
                transitive = self.compute_trust(intermediate, to_cid, visited.copy(), depth + 1)
                path_trust = weight * transitive * 0.8  # Decay
                max_trust = max(max_trust, path_trust)

        self.cache[cache_key] = max_trust
        return max_trust

# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("=" * 70)
    print("DOGFOOD 014: Speed Test with Real Cryptography")
    print("=" * 70)

    all_thoughts = []
    identities: List[CryptoIdentity] = []
    pubkey_registry: Dict[str, str] = {}
    trust_graph = TrustGraph()

    # ========================================================================
    # PHASE 1: Key Generation (50 identities)
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Generating 50 identities with real Ed25519 keys")
    print("=" * 70)

    start = time.perf_counter()
    for i in range(50):
        identity = CryptoIdentity(f"User{i:02d}")
        identities.append(identity)
        all_thoughts.append(identity.identity_thought.to_dict())
        pubkey_registry[identity.cid] = identity.pubkey_hex
    keygen_time = time.perf_counter() - start

    print(f"\n  Generated 50 keypairs in {keygen_time*1000:.1f}ms")
    print(f"  Per-key: {keygen_time/50*1000:.3f}ms")

    # ========================================================================
    # PHASE 2: Build trust topology (same as dogfood 012)
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Building trust topology with signed attestations")
    print("=" * 70)

    attestation_count = 0
    start = time.perf_counter()

    # Cluster 1: Dense core (0-9)
    print("\n  Cluster 1: Dense core (0-9, all trust each other)")
    for i in range(10):
        for j in range(10):
            if i != j:
                att = identities[i].create_thought(
                    type="attestation",
                    content={"on": identities[j].cid, "weight": 1.0, "aspect": "trust"},
                    because=[identities[i].cid, identities[j].cid]
                )
                all_thoughts.append(att.to_dict())
                trust_graph.add_edge(identities[i].cid, identities[j].cid, 1.0)
                attestation_count += 1

    # Cluster 2: Chain (10-19)
    print("  Cluster 2: Chain (10-19, bidirectional)")
    for i in range(10, 19):
        for direction in [(i, i+1), (i+1, i)]:
            att = identities[direction[0]].create_thought(
                type="attestation",
                content={"on": identities[direction[1]].cid, "weight": 0.9, "aspect": "trust"},
                because=[identities[direction[0]].cid, identities[direction[1]].cid]
            )
            all_thoughts.append(att.to_dict())
            trust_graph.add_edge(identities[direction[0]].cid, identities[direction[1]].cid, 0.9)
            attestation_count += 1

    # Cluster 3: Star (20 hub, 21-29 spokes)
    print("  Cluster 3: Star (20 hub, 21-29 spokes)")
    hub = identities[20]
    for i in range(21, 30):
        # Hub trusts spokes
        att1 = hub.create_thought(
            type="attestation",
            content={"on": identities[i].cid, "weight": 0.8, "aspect": "trust"},
            because=[hub.cid, identities[i].cid]
        )
        all_thoughts.append(att1.to_dict())
        trust_graph.add_edge(hub.cid, identities[i].cid, 0.8)

        # Spokes trust hub
        att2 = identities[i].create_thought(
            type="attestation",
            content={"on": hub.cid, "weight": 0.8, "aspect": "trust"},
            because=[identities[i].cid, hub.cid]
        )
        all_thoughts.append(att2.to_dict())
        trust_graph.add_edge(identities[i].cid, hub.cid, 0.8)
        attestation_count += 2

    # Cluster 4: Cycles (30-39)
    print("  Cluster 4: Cycles (30-39, intentional loops)")
    for i in range(30, 40):
        next_i = 30 + ((i - 30 + 1) % 10)
        att = identities[i].create_thought(
            type="attestation",
            content={"on": identities[next_i].cid, "weight": 0.7, "aspect": "trust"},
            because=[identities[i].cid, identities[next_i].cid]
        )
        all_thoughts.append(att.to_dict())
        trust_graph.add_edge(identities[i].cid, identities[next_i].cid, 0.7)
        attestation_count += 1

    # Cluster 5: Isolated (40-49, sparse)
    print("  Cluster 5: Isolated (40-49, sparse connections)")
    for i in range(40, 49, 2):
        att = identities[i].create_thought(
            type="attestation",
            content={"on": identities[i+1].cid, "weight": 0.6, "aspect": "trust"},
            because=[identities[i].cid, identities[i+1].cid]
        )
        all_thoughts.append(att.to_dict())
        trust_graph.add_edge(identities[i].cid, identities[i+1].cid, 0.6)
        attestation_count += 1

    # Cross-cluster bridges
    print("  Cross-cluster bridges: 5→15→25→35→45")
    bridges = [(5, 15), (15, 25), (25, 35), (35, 45)]
    for src, dst in bridges:
        att = identities[src].create_thought(
            type="attestation",
            content={"on": identities[dst].cid, "weight": 0.7, "aspect": "bridge"},
            because=[identities[src].cid, identities[dst].cid]
        )
        all_thoughts.append(att.to_dict())
        trust_graph.add_edge(identities[src].cid, identities[dst].cid, 0.7)
        attestation_count += 1

    attestation_time = time.perf_counter() - start
    print(f"\n  Created {attestation_count} attestations in {attestation_time*1000:.1f}ms")
    print(f"  Per-attestation: {attestation_time/attestation_count*1000:.3f}ms")
    print(f"  Attestations/sec: {attestation_count/attestation_time:,.0f}")

    # ========================================================================
    # PHASE 3: Message flood (500 messages)
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Message flood (500 signed messages)")
    print("=" * 70)

    messages = []
    start = time.perf_counter()

    for i in range(500):
        sender = random.choice(identities)
        msg = sender.create_thought(
            type="message",
            content={"text": f"Message {i} from {sender.name}", "seq": i},
            because=[sender.cid]
        )
        messages.append(msg)
        all_thoughts.append(msg.to_dict())

    message_time = time.perf_counter() - start
    print(f"\n  Created 500 messages in {message_time*1000:.1f}ms")
    print(f"  Per-message: {message_time/500*1000:.3f}ms")
    print(f"  Messages/sec: {500/message_time:,.0f}")

    # ========================================================================
    # PHASE 4: Signature verification
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: Verifying all signatures")
    print("=" * 70)

    start = time.perf_counter()
    valid = 0
    invalid = 0

    for thought in all_thoughts:
        if verify_signature(thought, pubkey_registry):
            valid += 1
        else:
            invalid += 1

    verify_time = time.perf_counter() - start
    print(f"\n  Verified {len(all_thoughts)} signatures in {verify_time*1000:.1f}ms")
    print(f"  Per-verification: {verify_time/len(all_thoughts)*1000:.3f}ms")
    print(f"  Verifications/sec: {len(all_thoughts)/verify_time:,.0f}")
    print(f"  Valid: {valid}, Invalid: {invalid}")

    # ========================================================================
    # PHASE 5: Trust lookups (stress test)
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: Trust computation stress test")
    print("=" * 70)

    # Warm up cache
    print("\n  Warming cache with full graph traversal...")
    for i in range(50):
        for j in range(50):
            trust_graph.compute_trust(identities[i].cid, identities[j].cid)

    trust_graph.cache_hits = 0
    trust_graph.cache_misses = 0

    # Speed test
    lookups = 100000
    start = time.perf_counter()

    for _ in range(lookups):
        i = random.randint(0, 49)
        j = random.randint(0, 49)
        trust_graph.compute_trust(identities[i].cid, identities[j].cid)

    trust_time = time.perf_counter() - start
    cache_rate = trust_graph.cache_hits / (trust_graph.cache_hits + trust_graph.cache_misses) * 100

    print(f"\n  {lookups:,} trust lookups in {trust_time*1000:.1f}ms")
    print(f"  Lookups/sec: {lookups/trust_time:,.0f}")
    print(f"  Cache hit rate: {cache_rate:.1f}%")

    # ========================================================================
    # PHASE 6: Message routing with trust filter
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 6: Message routing with trust filter")
    print("=" * 70)

    threshold = 0.3
    routed = 0
    filtered = 0

    start = time.perf_counter()

    for receiver in identities:
        for msg in messages:
            sender_cid = msg.created_by
            trust = trust_graph.compute_trust(receiver.cid, sender_cid)
            if trust >= threshold:
                routed += 1
            else:
                filtered += 1

    route_time = time.perf_counter() - start
    total_routes = len(identities) * len(messages)

    print(f"\n  Routed {total_routes:,} message checks in {route_time*1000:.1f}ms")
    print(f"  Routes/sec: {total_routes/route_time:,.0f}")
    print(f"  Passed: {routed:,} ({routed/total_routes*100:.1f}%)")
    print(f"  Filtered: {filtered:,} ({filtered/total_routes*100:.1f}%)")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY: Real Ed25519 Performance (Single Thread, Unoptimized)")
    print("=" * 70)

    print(f"""
  Key generation:      {50/keygen_time:,.0f} keys/sec
  Attestation signing: {attestation_count/attestation_time:,.0f} attestations/sec
  Message signing:     {500/message_time:,.0f} messages/sec
  Signature verify:    {len(all_thoughts)/verify_time:,.0f} verifications/sec
  Trust lookups:       {lookups/trust_time:,.0f} lookups/sec
  Message routing:     {total_routes/route_time:,.0f} routes/sec

  Total thoughts:      {len(all_thoughts)}
  All signatures:      {'✓ VALID' if invalid == 0 else f'✗ {invalid} INVALID'}
    """)

    # Write output
    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-014-speed-crypto.jsonl"
    with open(output_path, 'w') as f:
        for thought in all_thoughts:
            f.write(json.dumps(thought) + '\n')

    print(f"Wrote {len(all_thoughts)} thoughts to:")
    print(f"  {output_path}")

if __name__ == "__main__":
    main()
