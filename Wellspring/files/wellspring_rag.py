#!/usr/bin/env python3
"""
Dogfood 017: RAG with Wellspring Thoughts
Semantic retrieval with trust weighting and connection awareness.
"""

import json
import hashlib
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
import base64

# Embedding model (TF-IDF fallback - works offline)
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
        """Extract indexable text from thought."""
        if "text" in self.content:
            return self.content["text"]
        elif "title" in self.content:
            parts = [self.content["title"]]
            if "body" in self.content:
                parts.append(self.content["body"])
            return " ".join(parts)
        elif "summary" in self.content:
            return self.content["summary"]
        else:
            return json.dumps(self.content)

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
# SEMANTIC INDEX (per-pool)
# ============================================================================

class SemanticIndex:
    """Pool-level semantic index with configurable behavior."""

    def __init__(self, config: dict):
        self.config = config
        self.model_name = config.get("embedding_model", "tfidf")  # TF-IDF works offline
        self.similarity_threshold = config.get("similarity_threshold", 0.1)
        self.max_candidates = config.get("max_candidates", 50)

        print(f"  Using embedding model: {self.model_name}")

        # TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_features=5000
        )

        self.cids: List[str] = []  # Ordered list of CIDs
        self.texts: List[str] = []  # Corresponding texts
        self.thoughts: Dict[str, SignedThought] = {}  # cid -> thought
        self.tfidf_matrix = None  # Will be computed on demand

    def add_thought(self, thought: SignedThought):
        """Index a thought."""
        text = thought.get_text()
        self.cids.append(thought.cid)
        self.texts.append(text)
        self.thoughts[thought.cid] = thought
        self.tfidf_matrix = None  # Invalidate matrix

    def _ensure_matrix(self):
        """Rebuild TF-IDF matrix if needed."""
        if self.tfidf_matrix is None and self.texts:
            self.tfidf_matrix = self.vectorizer.fit_transform(self.texts)

    def query(self, query_text: str, top_k: int = None) -> List[Tuple[str, float]]:
        """
        Query the index.
        Returns: [(cid, similarity), ...] sorted by similarity desc.
        """
        if top_k is None:
            top_k = self.max_candidates

        self._ensure_matrix()
        if self.tfidf_matrix is None:
            return []

        # Transform query using fitted vectorizer
        query_vec = self.vectorizer.transform([query_text])

        # Compute cosine similarities
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        results = []
        for i, sim in enumerate(similarities):
            if sim >= self.similarity_threshold:
                results.append((self.cids[i], float(sim)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def find_neighbors(self, cid: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Find semantically similar thoughts to a given thought."""
        if cid not in self.thoughts:
            return []

        self._ensure_matrix()
        if self.tfidf_matrix is None:
            return []

        # Find index of target CID
        try:
            target_idx = self.cids.index(cid)
        except ValueError:
            return []

        target_vec = self.tfidf_matrix[target_idx]

        # Compute similarities to all others
        similarities = cosine_similarity(target_vec, self.tfidf_matrix).flatten()

        results = []
        for i, sim in enumerate(similarities):
            if self.cids[i] != cid:
                results.append((self.cids[i], float(sim)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

# ============================================================================
# THOUGHT POOL WITH RAG
# ============================================================================

class ThoughtPool:
    """A pool with semantic indexing and connection tracking."""

    def __init__(self, name: str, admin: CryptoIdentity, index_config: dict):
        self.name = name
        self.admin = admin

        # Create pool thought
        self.pool_thought = admin.create_thought(
            type="pool",
            content={"name": name, "admin": admin.cid},
            because=[admin.cid]
        )
        self.cid = self.pool_thought.cid

        # Create index config thought
        self.index_config_thought = admin.create_thought(
            type="aspect",
            content={"aspect_type": "index_config", **index_config},
            because=[self.cid]
        )

        # Initialize index
        self.index = SemanticIndex(index_config)

        # Storage
        self.thoughts: Dict[str, SignedThought] = {}
        self.connections: Dict[str, List[str]] = {}  # from_cid -> [to_cids]
        self.trust_scores: Dict[str, float] = {}  # identity_cid -> trust

        # Add founding thoughts
        self._store(admin.identity_thought)
        self._store(self.pool_thought)
        self._store(self.index_config_thought)

    def _store(self, thought: SignedThought):
        """Store and index a thought."""
        self.thoughts[thought.cid] = thought

        # Index if it has content worth indexing
        if thought.type in ["message", "research", "note", "article"]:
            self.index.add_thought(thought)

        # Track connections via because
        for ref in thought.because:
            if ref not in self.connections:
                self.connections[ref] = []
            self.connections[ref].append(thought.cid)

    def add_thought(self, thought: SignedThought):
        """Add a thought to the pool."""
        self._store(thought)

    def set_trust(self, identity_cid: str, score: float):
        """Set trust score for an identity (from pool admin's perspective)."""
        self.trust_scores[identity_cid] = score

    def query(self, query_text: str, viewer_cid: str = None, top_k: int = 10) -> List[dict]:
        """
        Query the pool with optional trust weighting.

        Returns list of:
        {
            "thought": thought_dict,
            "similarity": float,
            "trust": float,
            "relevance": float (similarity * trust),
            "connections": [connected_thought_cids],
            "chain_depth": int (hops in because chain)
        }
        """
        # Get semantic candidates
        candidates = self.index.query(query_text, top_k=self.index.config["max_candidates"])

        results = []
        for cid, similarity in candidates:
            thought = self.thoughts[cid]

            # Compute trust (default 0.5 for unknown)
            creator = thought.created_by
            trust = self.trust_scores.get(creator, 0.5)

            # Trust-weighted relevance
            relevance = similarity * trust

            # Find connections (thoughts that reference this one)
            connections = self.connections.get(cid, [])

            # Compute chain depth (how deep is the because chain?)
            chain_depth = self._chain_depth(cid)

            results.append({
                "thought": thought.to_dict(),
                "similarity": round(similarity, 4),
                "trust": round(trust, 2),
                "relevance": round(relevance, 4),
                "connections": connections[:5],  # Limit for display
                "chain_depth": chain_depth
            })

        # Sort by relevance (trust-weighted)
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:top_k]

    def _chain_depth(self, cid: str, visited: set = None) -> int:
        """Compute depth of because chain."""
        if visited is None:
            visited = set()

        if cid in visited or cid not in self.thoughts:
            return 0

        visited.add(cid)
        thought = self.thoughts[cid]

        if not thought.because:
            return 0

        max_depth = 0
        for ref in thought.because:
            if ref in self.thoughts:
                depth = self._chain_depth(ref, visited)
                max_depth = max(max_depth, depth)

        return max_depth + 1

    def get_context_window(self, cids: List[str], max_tokens: int = 4000) -> str:
        """
        Collapse thoughts into a context window for LLM injection.
        Walks because chains to include grounding.
        """
        included = set()
        context_parts = []
        token_estimate = 0

        def add_thought(cid: str, depth: int = 0):
            nonlocal token_estimate
            if cid in included or cid not in self.thoughts:
                return
            if token_estimate > max_tokens:
                return

            thought = self.thoughts[cid]
            text = thought.get_text()

            # Rough token estimate (4 chars per token)
            tokens = len(text) // 4
            if token_estimate + tokens > max_tokens:
                return

            included.add(cid)
            token_estimate += tokens

            prefix = "  " * depth
            creator = thought.created_by[:12] + "..."
            context_parts.append(f"{prefix}[{creator}] {text}")

            # Walk because chain (limited depth)
            if depth < 2:
                for ref in thought.because:
                    add_thought(ref, depth + 1)

        for cid in cids:
            add_thought(cid)

        return "\n".join(context_parts)

# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("=" * 70)
    print("DOGFOOD 017: RAG with Wellspring Thoughts")
    print("=" * 70)

    # ========================================================================
    # PHASE 1: Create identities with different trust levels
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Creating identities")
    print("=" * 70)

    expert = CryptoIdentity("Dr. Sarah (Domain Expert)")
    researcher = CryptoIdentity("Alex (Researcher)")
    journalist = CryptoIdentity("Jordan (Journalist)")
    random_person = CryptoIdentity("RandomUser42")

    print(f"\n  Created: {expert.name}, {researcher.name}, {journalist.name}, {random_person.name}")

    # ========================================================================
    # PHASE 2: Create pool with index configuration
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Creating pool with index config")
    print("=" * 70)

    index_config = {
        "embedding_model": "tfidf",  # TF-IDF works offline, swap to neural when available
        "similarity_threshold": 0.05,  # Lower threshold for TF-IDF
        "max_candidates": 50,
        "chunk_strategy": "whole_thought",
        "index_scope": "pool"
    }

    pool = ThoughtPool("Research Pool", expert, index_config)

    # Set trust levels (from expert's perspective as admin)
    pool.set_trust(expert.cid, 1.0)       # Self: full trust
    pool.set_trust(researcher.cid, 0.8)   # Researcher: high trust
    pool.set_trust(journalist.cid, 0.5)   # Journalist: medium trust
    pool.set_trust(random_person.cid, 0.2) # Random: low trust

    print(f"\n  Pool: {pool.name}")
    print(f"  Trust levels:")
    print(f"    Expert (self):  1.0")
    print(f"    Researcher:     0.8")
    print(f"    Journalist:     0.5")
    print(f"    Random:         0.2")

    # ========================================================================
    # PHASE 3: Add diverse content
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Adding semantically diverse content")
    print("=" * 70)

    # Topic cluster 1: Climate change
    climate_1 = expert.create_thought(
        type="research",
        content={
            "title": "Climate Impact Analysis",
            "text": "Rising global temperatures are causing measurable changes in precipitation patterns, with drought conditions increasing in equatorial regions while flooding becomes more common in temperate zones."
        },
        because=[expert.cid]
    )
    pool.add_thought(climate_1)

    climate_2 = researcher.create_thought(
        type="research",
        content={
            "title": "Ocean Acidification Study",
            "text": "Carbon dioxide absorption by oceans has increased acidity by 30% since pre-industrial times, threatening coral reef ecosystems and shellfish populations."
        },
        because=[climate_1.cid, researcher.cid]  # References expert's work
    )
    pool.add_thought(climate_2)

    climate_3 = journalist.create_thought(
        type="article",
        content={
            "title": "Climate Crisis Deepens",
            "text": "Scientists warn that climate change is accelerating faster than predicted, with record temperatures and extreme weather events becoming the new normal."
        },
        because=[journalist.cid]
    )
    pool.add_thought(climate_3)

    # Topic cluster 2: Machine learning
    ml_1 = expert.create_thought(
        type="research",
        content={
            "title": "Transformer Architecture Analysis",
            "text": "Attention mechanisms in transformer models enable parallel processing of sequence data, significantly improving training efficiency compared to recurrent architectures."
        },
        because=[expert.cid]
    )
    pool.add_thought(ml_1)

    ml_2 = researcher.create_thought(
        type="note",
        content={
            "text": "The key insight is that self-attention allows each token to directly attend to all other tokens, bypassing the sequential bottleneck of RNNs and LSTMs."
        },
        because=[ml_1.cid, researcher.cid]
    )
    pool.add_thought(ml_2)

    ml_3 = random_person.create_thought(
        type="message",
        content={
            "text": "ChatGPT is amazing! AI is going to change everything! Neural networks are the future of computing and will solve all our problems!"
        },
        because=[random_person.cid]
    )
    pool.add_thought(ml_3)

    # Topic cluster 3: Economics
    econ_1 = researcher.create_thought(
        type="research",
        content={
            "title": "Monetary Policy Effects",
            "text": "Interest rate adjustments by central banks have delayed effects on inflation, typically requiring 12-18 months to fully manifest in consumer price indices."
        },
        because=[researcher.cid]
    )
    pool.add_thought(econ_1)

    # Cross-topic connection
    cross_1 = expert.create_thought(
        type="research",
        content={
            "title": "Climate Economics Integration",
            "text": "Machine learning models can improve climate impact predictions for economic planning, combining atmospheric data with economic indicators to forecast regional effects."
        },
        because=[climate_1.cid, ml_1.cid, expert.cid]  # Connects all three topics
    )
    pool.add_thought(cross_1)

    # Noise
    noise_1 = random_person.create_thought(
        type="message",
        content={
            "text": "Just had the best pizza ever! 🍕 The cheese was perfectly melted and the crust was crispy."
        },
        because=[random_person.cid]
    )
    pool.add_thought(noise_1)

    print(f"\n  Added {len(pool.thoughts)} thoughts across 3 topic clusters + noise")
    print(f"  Indexed {len(pool.index.texts)} thoughts for retrieval")

    # ========================================================================
    # PHASE 4: Query tests
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: Query tests")
    print("=" * 70)

    queries = [
        "How does climate change affect ocean ecosystems?",
        "Explain how transformer neural networks work",
        "What is the relationship between AI and climate science?",
        "Tell me about pizza"
    ]

    for query in queries:
        print(f"\n  Query: \"{query}\"")
        print("  " + "-" * 50)

        results = pool.query(query, top_k=5)

        for i, r in enumerate(results):
            thought = r["thought"]
            text = thought["content"].get("text", thought["content"].get("title", ""))[:60]
            creator_name = "Unknown"
            for identity in [expert, researcher, journalist, random_person]:
                if identity.cid == thought["created_by"]:
                    creator_name = identity.name.split()[0]
                    break

            print(f"    {i+1}. [{creator_name}] \"{text}...\"")
            print(f"       sim={r['similarity']:.3f} × trust={r['trust']:.1f} = relevance={r['relevance']:.3f}")
            if r["connections"]:
                print(f"       connections: {len(r['connections'])} thoughts reference this")
            if r["chain_depth"] > 0:
                print(f"       chain_depth: {r['chain_depth']} (grounded in prior work)")

    # ========================================================================
    # PHASE 5: Context window generation
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: Context window for LLM injection")
    print("=" * 70)

    query = "How can machine learning help with climate change?"
    results = pool.query(query, top_k=3)

    print(f"\n  Query: \"{query}\"")
    print(f"  Top 3 results selected for context:")

    cids = [r["thought"]["cid"] for r in results]
    context = pool.get_context_window(cids, max_tokens=500)

    print("\n  Generated context window:")
    print("  " + "-" * 50)
    for line in context.split("\n"):
        print(f"  {line}")
    print("  " + "-" * 50)

    # ========================================================================
    # PHASE 6: Semantic neighborhoods
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 6: Semantic neighborhoods (connection discovery)")
    print("=" * 70)

    print(f"\n  Finding neighbors for cross-topic thought:")
    print(f"  \"{cross_1.content['title']}\"")

    neighbors = pool.index.find_neighbors(cross_1.cid, top_k=5)

    print("\n  Nearest semantic neighbors:")
    for cid, sim in neighbors:
        thought = pool.thoughts[cid]
        text = thought.get_text()[:50]
        print(f"    sim={sim:.3f}: \"{text}...\"")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("""
  RAG with Wellspring Thoughts:

  1. Pool-level index configuration (thought, not setting)
     - Embedding model, thresholds, scope all configurable
     - Different pools can have different strategies

  2. Trust-weighted relevance
     - relevance = similarity × trust
     - Expert's research surfaces above random noise
     - Same query, different results for different viewers

  3. Connection awareness
     - Thoughts that reference others are tracked
     - Chain depth shows grounding in prior work
     - Can walk because chains for full context

  4. Context window generation
     - Collapse relevant thoughts + their grounding
     - Token budget respected
     - Ready for LLM injection

  5. Semantic neighborhoods
     - Find related thoughts by embedding similarity
     - Could become automatic semantic_proximity connections
     - Subconscious maintenance pattern

  Key insight: The index IS the pool's intelligence.
  Configure it via thoughts, query it with trust weighting,
  surface results with full provenance.
    """)

    # Write output
    output = {
        "pool": pool.pool_thought.to_dict(),
        "index_config": pool.index_config_thought.to_dict(),
        "thoughts": [t.to_dict() for t in pool.thoughts.values()],
        "trust_scores": pool.trust_scores
    }

    output_path = "/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/wellspring-dogfood-017-rag.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Wrote results to: {output_path}")

if __name__ == "__main__":
    main()
