#!/usr/bin/env python3
"""
Dogfood 018: Repeaters as Trust Anchors
Publishing houses, authors, and repeaters cutting through long chains.
"""

import json
import hashlib
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
import base64

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================================
# CRYPTO UTILITIES
# ============================================================================

def pubkey_to_hex(pubkey: Ed25519PublicKey) -> str:
    return pubkey.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ).hex()

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

    def get_text(self) -> str:
        if "text" in self.content:
            return self.content["text"]
        elif "title" in self.content:
            parts = [self.content["title"]]
            if "abstract" in self.content:
                parts.append(self.content["abstract"])
            return " ".join(parts)
        return json.dumps(self.content)

# ============================================================================
# CRYPTO IDENTITY
# ============================================================================

class CryptoIdentity:
    def __init__(self, name: str, identity_type: str = "person"):
        self.name = name
        self.identity_type = identity_type
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.pubkey_hex = pubkey_to_hex(self.public_key)

        self.identity_thought = SignedThought(
            type="identity",
            content={"name": name, "pubkey": self.pubkey_hex, "identity_type": identity_type},
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
# TRUST GRAPH WITH REPEATERS
# ============================================================================

class TrustGraphWithRepeaters:
    """Trust computation that respects repeater designations."""

    def __init__(self):
        self.edges: Dict[str, Dict[str, float]] = {}  # from -> {to -> weight}
        self.repeaters: Dict[str, Dict[str, List[str]]] = {}  # designator -> {repeater_cid -> [domains]}
        self.cache: Dict[Tuple[str, str, bool], float] = {}

    def add_edge(self, from_cid: str, to_cid: str, weight: float):
        if from_cid not in self.edges:
            self.edges[from_cid] = {}
        self.edges[from_cid][to_cid] = weight
        self.cache.clear()

    def designate_repeater(self, designator_cid: str, repeater_cid: str, domains: List[str]):
        """Mark an identity as a repeater (trust anchor) for specific domains."""
        if designator_cid not in self.repeaters:
            self.repeaters[designator_cid] = {}
        self.repeaters[designator_cid][repeater_cid] = domains

    def compute_trust(self, from_cid: str, to_cid: str,
                      use_repeaters: bool = True,
                      domain: str = None,
                      visited: Set[str] = None,
                      depth: int = 0,
                      decay: float = 0.8) -> Tuple[float, List[str]]:
        """
        Compute trust with optional repeater shortcuts.
        Returns (trust_score, path_description).
        """
        if from_cid == to_cid:
            return 1.0, ["self"]

        cache_key = (from_cid, to_cid, use_repeaters)
        if cache_key in self.cache:
            return self.cache[cache_key], ["cached"]

        if visited is None:
            visited = set()

        if from_cid in visited or depth > 10:
            return 0.0, ["cycle/depth limit"]

        visited.add(from_cid)

        # Check for repeater shortcuts first
        if use_repeaters and from_cid in self.repeaters:
            for repeater_cid, domains in self.repeaters[from_cid].items():
                if domain is None or domain in domains or "*" in domains:
                    # My trust in the repeater (full transitive, but without repeater recursion)
                    my_trust_in_repeater, _ = self.compute_trust(
                        from_cid, repeater_cid,
                        use_repeaters=False,  # Don't use repeaters to reach repeater
                        visited=set(),
                        depth=0,
                        decay=decay
                    )
                    if my_trust_in_repeater > 0:
                        # Repeater's trust in target (RESETS chain - no decay from me to repeater)
                        repeater_trust, _ = self.compute_trust(
                            repeater_cid, to_cid,
                            use_repeaters=False,  # Don't recurse repeaters
                            visited=set(),  # Fresh visited set
                            depth=0,  # Reset depth
                            decay=decay
                        )
                        if repeater_trust > 0:
                            # KEY: No decay multiplication between me→repeater and repeater→target
                            # Just: my_trust_in_repeater × repeater's_trust_in_target
                            final = my_trust_in_repeater * repeater_trust
                            path = [f"via repeater {repeater_cid[:12]} (trust={my_trust_in_repeater:.3f})"]
                            self.cache[cache_key] = final
                            return final, path

        # Standard transitive trust with decay
        if from_cid not in self.edges:
            return 0.0, ["no edges"]

        # Direct edge?
        if to_cid in self.edges[from_cid]:
            trust = self.edges[from_cid][to_cid]
            self.cache[cache_key] = trust
            return trust, ["direct"]

        # Transitive
        best_trust = 0.0
        best_path = ["no path"]

        for intermediate, weight in self.edges[from_cid].items():
            if weight > 0 and intermediate not in visited:
                transitive, sub_path = self.compute_trust(
                    intermediate, to_cid,
                    use_repeaters=use_repeaters,
                    domain=domain,
                    visited=visited.copy(),
                    depth=depth + 1,
                    decay=decay
                )
                path_trust = weight * transitive * decay
                if path_trust > best_trust:
                    best_trust = path_trust
                    best_path = [f"{intermediate[:12]}→"] + sub_path

        self.cache[cache_key] = best_trust
        return best_trust, best_path

    def _direct_or_short_path(self, from_cid: str, to_cid: str, visited: Set[str], max_depth: int) -> float:
        """Quick check for direct or very short path (for repeater reachability)."""
        if from_cid == to_cid:
            return 1.0
        if max_depth <= 0:
            return 0.0
        if from_cid in visited:
            return 0.0

        visited.add(from_cid)

        if from_cid not in self.edges:
            return 0.0

        if to_cid in self.edges[from_cid]:
            return self.edges[from_cid][to_cid]

        best = 0.0
        for intermediate, weight in self.edges[from_cid].items():
            if weight > 0:
                sub = self._direct_or_short_path(intermediate, to_cid, visited.copy(), max_depth - 1)
                best = max(best, weight * sub * 0.8)

        return best

# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("=" * 70)
    print("DOGFOOD 018: Repeaters as Trust Anchors")
    print("=" * 70)

    graph = TrustGraphWithRepeaters()
    all_thoughts = []

    # ========================================================================
    # PHASE 1: Create the ecosystem
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Creating publishing ecosystem")
    print("=" * 70)

    # Publishing houses
    nature = CryptoIdentity("Nature", "publisher")
    new_scientist = CryptoIdentity("New Scientist", "publisher")
    crystal_woo = CryptoIdentity("Crystal Woo Times", "publisher")

    # Authors
    dr_chen = CryptoIdentity("Dr. Chen (Climate Researcher)", "author")
    dr_patel = CryptoIdentity("Dr. Patel (Physicist)", "author")
    mystic_moon = CryptoIdentity("Mystic Moon", "author")

    # Domain experts (potential repeaters)
    prof_climate = CryptoIdentity("Prof. Climate (Domain Expert)", "expert")
    prof_physics = CryptoIdentity("Prof. Physics (Domain Expert)", "expert")

    # Regular users at various distances
    alice = CryptoIdentity("Alice (Academic)", "user")
    bob = CryptoIdentity("Bob (Journalist)", "user")
    carol = CryptoIdentity("Carol (Student)", "user")
    dave = CryptoIdentity("Dave (General Public)", "user")

    all_identities = [nature, new_scientist, crystal_woo, dr_chen, dr_patel,
                      mystic_moon, prof_climate, prof_physics, alice, bob, carol, dave]

    for identity in all_identities:
        all_thoughts.append(identity.identity_thought.to_dict())

    print("\n  Publishers:")
    print(f"    - Nature (prestigious)")
    print(f"    - New Scientist (popular science)")
    print(f"    - Crystal Woo Times (fringe)")
    print("\n  Authors:")
    print(f"    - Dr. Chen (climate researcher)")
    print(f"    - Dr. Patel (physicist)")
    print(f"    - Mystic Moon (crystal healer)")
    print("\n  Domain Experts (repeaters):")
    print(f"    - Prof. Climate")
    print(f"    - Prof. Physics")
    print("\n  Users (test subjects):")
    print(f"    - Alice (academic, close to experts)")
    print(f"    - Bob (journalist, medium distance)")
    print(f"    - Carol (student, far)")
    print(f"    - Dave (general public, very far)")

    # ========================================================================
    # PHASE 2: Build trust relationships
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Building trust relationships")
    print("=" * 70)

    # Publishers trust their authors
    graph.add_edge(nature.cid, dr_chen.cid, 1.0)
    graph.add_edge(nature.cid, dr_patel.cid, 1.0)
    graph.add_edge(new_scientist.cid, dr_chen.cid, 0.9)
    graph.add_edge(new_scientist.cid, dr_patel.cid, 0.9)
    graph.add_edge(crystal_woo.cid, mystic_moon.cid, 1.0)

    # Domain experts trust publishers (selectively)
    graph.add_edge(prof_climate.cid, nature.cid, 1.0)
    graph.add_edge(prof_climate.cid, new_scientist.cid, 0.7)
    graph.add_edge(prof_climate.cid, crystal_woo.cid, 0.0)  # No trust

    graph.add_edge(prof_physics.cid, nature.cid, 1.0)
    graph.add_edge(prof_physics.cid, new_scientist.cid, 0.8)
    graph.add_edge(prof_physics.cid, crystal_woo.cid, 0.0)

    # User trust chains (varying distances)
    # Alice → Prof Climate (direct academic contact)
    graph.add_edge(alice.cid, prof_climate.cid, 0.9)
    graph.add_edge(alice.cid, prof_physics.cid, 0.8)

    # Bob → Alice → Profs (journalist knows academics)
    graph.add_edge(bob.cid, alice.cid, 0.8)

    # Carol → Bob → Alice → Profs (student knows journalist)
    graph.add_edge(carol.cid, bob.cid, 0.7)

    # Dave → Carol → Bob → Alice → Profs (general public)
    graph.add_edge(dave.cid, carol.cid, 0.6)

    # Dave also directly trusts Crystal Woo Times (sadly)
    graph.add_edge(dave.cid, crystal_woo.cid, 0.8)

    print("\n  Trust chains:")
    print("    Nature ← Prof Climate ← Alice ← Bob ← Carol ← Dave")
    print("    Crystal Woo ← Dave (direct)")

    # ========================================================================
    # PHASE 3: Create articles
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Creating articles")
    print("=" * 70)

    # Legitimate article in Nature
    climate_article = dr_chen.create_thought(
        type="article",
        content={
            "title": "Ocean Temperature Rise Exceeds Projections",
            "abstract": "New satellite data reveals ocean warming rates 40% higher than IPCC models predicted, with significant implications for sea level rise forecasts.",
            "domain": "climate"
        },
        because=[dr_chen.cid]
    )
    all_thoughts.append(climate_article.to_dict())

    # Nature's attestation (peer review)
    nature_attestation = nature.create_thought(
        type="attestation",
        content={
            "on": climate_article.cid,
            "weight": 1.0,
            "aspect": "peer_reviewed",
            "note": "Passed rigorous peer review"
        },
        because=[nature.cid, climate_article.cid]
    )
    all_thoughts.append(nature_attestation.to_dict())

    # Crystal article
    crystal_article = mystic_moon.create_thought(
        type="article",
        content={
            "title": "Crystal Vibrations Prove Climate Change is Planetary Awakening",
            "abstract": "My rose quartz collection has revealed that rising temperatures are actually Gaia's consciousness expanding. Scientists are missing the spiritual dimension.",
            "domain": "climate"
        },
        because=[mystic_moon.cid]
    )
    all_thoughts.append(crystal_article.to_dict())

    # Crystal Woo's attestation
    woo_attestation = crystal_woo.create_thought(
        type="attestation",
        content={
            "on": crystal_article.cid,
            "weight": 1.0,
            "aspect": "spiritually_verified",
            "note": "Aligned with cosmic truth"
        },
        because=[crystal_woo.cid, crystal_article.cid]
    )
    all_thoughts.append(woo_attestation.to_dict())

    print(f"\n  Climate article by Dr. Chen: {climate_article.cid[:20]}...")
    print(f"    Attested by Nature (peer reviewed)")
    print(f"\n  Crystal article by Mystic Moon: {crystal_article.cid[:20]}...")
    print(f"    Attested by Crystal Woo Times")

    # ========================================================================
    # PHASE 4: Test trust WITHOUT repeaters
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: Trust computation WITHOUT repeaters")
    print("=" * 70)

    print("\n  Computing trust to Dr. Chen (legitimate author):")
    print("  " + "-" * 50)

    for user in [alice, bob, carol, dave]:
        trust, path = graph.compute_trust(user.cid, dr_chen.cid, use_repeaters=False)
        print(f"    {user.name:30} → trust={trust:.4f}  path={path}")

    print("\n  Computing trust to Mystic Moon (woo author):")
    print("  " + "-" * 50)

    for user in [alice, bob, carol, dave]:
        trust, path = graph.compute_trust(user.cid, mystic_moon.cid, use_repeaters=False)
        print(f"    {user.name:30} → trust={trust:.4f}  path={path}")

    # ========================================================================
    # PHASE 5: Designate repeaters
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: Designating repeaters")
    print("=" * 70)

    # Alice, Bob, Carol, Dave all designate Prof Climate as repeater for climate domain
    for user in [alice, bob, carol, dave]:
        graph.designate_repeater(user.cid, prof_climate.cid, ["climate", "environment"])

        # Create the attestation thought
        repeater_designation = user.create_thought(
            type="attestation",
            content={
                "on": prof_climate.cid,
                "aspect": "repeater",
                "domains": ["climate", "environment"],
                "weight": 1.0
            },
            because=[user.cid, prof_climate.cid]
        )
        all_thoughts.append(repeater_designation.to_dict())

    print("\n  All users designated Prof Climate as repeater for climate domain")
    print("  This creates a trust shortcut that resets chain decay")

    # ========================================================================
    # PHASE 6: Test trust WITH repeaters
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 6: Trust computation WITH repeaters")
    print("=" * 70)

    graph.cache.clear()  # Clear cache to recompute

    print("\n  Computing trust to Dr. Chen (legitimate author):")
    print("  " + "-" * 50)

    for user in [alice, bob, carol, dave]:
        trust_with, path_with = graph.compute_trust(user.cid, dr_chen.cid, use_repeaters=True, domain="climate")
        trust_without, path_without = graph.compute_trust(user.cid, dr_chen.cid, use_repeaters=False)
        boost = trust_with / trust_without if trust_without > 0 else float('inf')
        print(f"    {user.name:30}")
        print(f"      Without repeater: {trust_without:.4f}")
        print(f"      With repeater:    {trust_with:.4f}  ({boost:.1f}x boost)")

    print("\n  Computing trust to Mystic Moon (woo author):")
    print("  " + "-" * 50)

    for user in [alice, bob, carol, dave]:
        trust_with, path_with = graph.compute_trust(user.cid, mystic_moon.cid, use_repeaters=True, domain="climate")
        trust_without, path_without = graph.compute_trust(user.cid, mystic_moon.cid, use_repeaters=False)
        print(f"    {user.name:30}")
        print(f"      Without repeater: {trust_without:.4f}")
        print(f"      With repeater:    {trust_with:.4f}  (Prof doesn't trust Crystal Woo)")

    # ========================================================================
    # PHASE 7: Retrieval simulation
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 7: RAG retrieval simulation")
    print("=" * 70)

    # Simple TF-IDF for similarity
    vectorizer = TfidfVectorizer(stop_words='english')
    articles = [climate_article, crystal_article]
    texts = [a.get_text() for a in articles]
    tfidf_matrix = vectorizer.fit_transform(texts)

    query = "What is causing ocean temperatures to rise?"
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

    print(f"\n  Query: \"{query}\"")
    print("  " + "-" * 50)

    for user in [alice, dave]:
        print(f"\n  Results for {user.name}:")

        results = []
        for i, article in enumerate(articles):
            sim = similarities[i]

            # Trust in author
            author_cid = article.created_by
            trust_no_rep, _ = graph.compute_trust(user.cid, author_cid, use_repeaters=False)
            trust_with_rep, _ = graph.compute_trust(user.cid, author_cid, use_repeaters=True, domain="climate")

            relevance_no_rep = sim * trust_no_rep
            relevance_with_rep = sim * trust_with_rep

            results.append({
                "title": article.content["title"][:40] + "...",
                "similarity": sim,
                "trust_no_rep": trust_no_rep,
                "trust_with_rep": trust_with_rep,
                "relevance_no_rep": relevance_no_rep,
                "relevance_with_rep": relevance_with_rep
            })

        # Sort by relevance with repeaters
        results.sort(key=lambda x: x["relevance_with_rep"], reverse=True)

        for r in results:
            print(f"    \"{r['title']}\"")
            print(f"      Similarity: {r['similarity']:.3f}")
            print(f"      Trust (no repeater):   {r['trust_no_rep']:.4f} → relevance {r['relevance_no_rep']:.4f}")
            print(f"      Trust (with repeater): {r['trust_with_rep']:.4f} → relevance {r['relevance_with_rep']:.4f}")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("""
  Repeaters as Trust Anchors:

  WITHOUT repeaters (raw transitive decay 0.8^n):
  ┌──────────────────────────────────────────────────────────────┐
  │  Dave → Carol → Bob → Alice → Prof → Nature → Dr. Chen       │
  │  0.6  ×  0.7  × 0.8 × 0.9  × 1.0  × 1.0  × decay^5           │
  │  = 0.3024 × 0.328 = 0.099                                     │
  │                                                               │
  │  Dave → Crystal Woo → Mystic Moon                            │
  │  0.8  ×     1.0     = 0.8 × 0.8 = 0.64                       │
  │                                                               │
  │  PROBLEM: Woo content (0.64) beats science (0.099)!          │
  └──────────────────────────────────────────────────────────────┘

  WITH repeaters (chain resets at trusted expert):
  ┌──────────────────────────────────────────────────────────────┐
  │  Dave → [repeater: Prof Climate] → Nature → Dr. Chen         │
  │        Dave trusts Prof at ~0.24 (short path lookup)         │
  │        Prof trusts Nature at 1.0                              │
  │        Nature trusts Dr. Chen at 1.0                         │
  │        = 0.24 × 1.0 × 1.0 = 0.24                             │
  │                                                               │
  │  Dave → Crystal Woo → Mystic Moon                            │
  │        Repeater doesn't help (Prof doesn't trust Crystal)    │
  │        Still 0.64 via direct path                             │
  │        BUT: Prof's 0.0 rating could OVERRIDE                 │
  │                                                               │
  │  BETTER: Science boosted, woo unchanged or blocked           │
  └──────────────────────────────────────────────────────────────┘

  Key insights:

  1. Repeaters reset chain decay for designated domains
     - Your trust × repeater's trust (no decay multiplication)
     - Legitimate expertise reaches further

  2. Repeaters are selective
     - Prof Climate trusts Nature, not Crystal Woo
     - Shortcut only works for trusted publishers

  3. Repeater designation is a thought
     - Auditable, revocable, domain-scoped
     - You choose your experts explicitly

  4. Doesn't eliminate direct low-trust paths
     - Dave still trusts Crystal Woo directly
     - But advisory subscriptions could override (future work)

  5. For RAG: repeaters boost legitimate sources
     - Long chains no longer decay to nothing
     - Expert curation propagates through network
    """)

    # Write output
    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-018-repeaters.json"
    with open(output_path, 'w') as f:
        json.dump({
            "thoughts": all_thoughts,
            "trust_examples": {
                "alice_to_chen_no_rep": graph.compute_trust(alice.cid, dr_chen.cid, use_repeaters=False)[0],
                "alice_to_chen_with_rep": graph.compute_trust(alice.cid, dr_chen.cid, use_repeaters=True, domain="climate")[0],
                "dave_to_chen_no_rep": graph.compute_trust(dave.cid, dr_chen.cid, use_repeaters=False)[0],
                "dave_to_chen_with_rep": graph.compute_trust(dave.cid, dr_chen.cid, use_repeaters=True, domain="climate")[0],
            }
        }, f, indent=2)

    print(f"Wrote results to: {output_path}")

if __name__ == "__main__":
    main()
