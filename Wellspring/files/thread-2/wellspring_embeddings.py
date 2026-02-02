#!/usr/bin/env python3
"""
Thread 2: RAG/Vector Indexing for WoT
Uses sqlite-vec for vector storage, sentence-transformers for embeddings,
and wellspring_core.py as the thought storage backend.
"""

# Suppress tokenizers parallelism warning - must be before imports
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import sqlite3
import struct
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

# Try to load sqlite-vec, fall back to pure Python
try:
    import sqlite_vec
    HAVE_SQLITE_VEC = True
except ImportError:
    HAVE_SQLITE_VEC = False
    sqlite_vec = None

# Try to load sentence-transformers, fall back to hash-based embeddings
try:
    from sentence_transformers import SentenceTransformer
    HAVE_TRANSFORMERS = True
except ImportError:
    HAVE_TRANSFORMERS = False
    SentenceTransformer = None

# Import from wellspring_core (adjust path as needed)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from wellspring_core import (
    Thought, Identity,
    create_thought, store_thought, get_thought, query_thoughts,
    create_identity, load_identity, save_identity,
    DB_PATH, init_db
)

# ============================================================================
# CONFIGURATION
# ============================================================================

EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions, fast & good
EMBEDDING_DIM = 384

# Store vector DB alongside wellspring.db in parent dir
_THIS_DIR = Path(__file__).parent.resolve()
VEC_DB_PATH = _THIS_DIR.parent / "wellspring_vec.db"

# ============================================================================
# FALLBACK EMBEDDER (hash-based, works offline)
# ============================================================================

class HashEmbedder:
    """
    Fallback embedder using locality-sensitive hashing.
    Not as good as neural embeddings, but works offline and preserves
    some semantic similarity through n-gram overlap.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim
        # Random projection matrix (seeded for reproducibility)
        np.random.seed(42)
        self.projection = np.random.randn(10000, dim).astype(np.float32)

    def _tokenize(self, text: str) -> List[str]:
        """Simple word + ngram tokenization."""
        text = text.lower()
        words = text.split()

        # Add character n-grams for robustness
        ngrams = []
        for word in words:
            ngrams.append(word)
            for n in [2, 3]:
                for i in range(len(word) - n + 1):
                    ngrams.append(word[i:i+n])

        return ngrams

    def encode(self, text: str) -> np.ndarray:
        """Generate embedding from text using random projection."""
        tokens = self._tokenize(text)

        # Build sparse representation
        indices = []
        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            indices.append(h % 10000)

        # Project to dense space
        embedding = np.zeros(self.dim, dtype=np.float32)
        for idx in indices:
            embedding += self.projection[idx]

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm

        return embedding

# ============================================================================
# VECTOR DATABASE (Pure Python fallback)
# ============================================================================

def init_vec_db(db_path: Path = VEC_DB_PATH) -> sqlite3.Connection:
    """Initialize vector database. Uses pure SQLite (sqlite-vec not reliable)."""
    import tempfile

    # Try primary path, fall back to temp directory if it fails (iCloud issues)
    paths_to_try = [db_path, Path(tempfile.gettempdir()) / "wellspring_vec.db"]

    last_error = None
    for try_path in paths_to_try:
        try:
            conn = sqlite3.connect(try_path)

            # Store embeddings as BLOBs in regular table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thought_embeddings (
                    rowid INTEGER PRIMARY KEY,
                    embedding BLOB NOT NULL
                )
            """)

            # Metadata table linking rowids to CIDs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embedding_metadata (
                    rowid INTEGER PRIMARY KEY,
                    cid TEXT UNIQUE NOT NULL,
                    pool_cid TEXT,
                    text_content TEXT,
                    thought_type TEXT,
                    created_at INTEGER,
                    -- Trust weighting fields (Thread 1 handoff)
                    appetite_status TEXT DEFAULT 'welcomed',
                    trust_weight REAL DEFAULT 1.0,
                    chain_depth INTEGER DEFAULT 0
                )
            """)

            # Add columns if they don't exist (migration for existing DBs)
            try:
                conn.execute("ALTER TABLE embedding_metadata ADD COLUMN appetite_status TEXT DEFAULT 'welcomed'")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                conn.execute("ALTER TABLE embedding_metadata ADD COLUMN trust_weight REAL DEFAULT 1.0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE embedding_metadata ADD COLUMN chain_depth INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

            conn.execute("CREATE INDEX IF NOT EXISTS idx_cid ON embedding_metadata(cid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pool ON embedding_metadata(pool_cid)")

            conn.commit()

            if try_path != db_path:
                print(f"  Note: Using fallback DB at {try_path}")

            return conn
        except sqlite3.OperationalError as e:
            last_error = e
            continue

    raise last_error

def serialize_vector(vec: List[float]) -> bytes:
    """Serialize vector to bytes."""
    return struct.pack(f'{len(vec)}f', *vec)

def deserialize_vector(data: bytes, dim: int = EMBEDDING_DIM) -> List[float]:
    """Deserialize bytes back to vector."""
    return list(struct.unpack(f'{dim}f', data))

def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine distance (1 - cosine similarity)."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 1.0
    return 1.0 - (dot / (norm_a * norm_b))

# ============================================================================
# EMBEDDING PIPELINE
# ============================================================================

class EmbeddingPipeline:
    """Pipeline for embedding thoughts and storing in sqlite-vec."""

    def __init__(self, vec_db_path: Path = VEC_DB_PATH, use_neural: bool = True):
        self.use_neural = use_neural and HAVE_TRANSFORMERS

        if self.use_neural:
            print(f"Loading embedding model: {EMBEDDING_MODEL}")
            try:
                self.model = SentenceTransformer(EMBEDDING_MODEL)
                print(f"  Neural model loaded. Dimension: {EMBEDDING_DIM}")
            except Exception as e:
                print(f"  Neural model failed: {e}")
                print(f"  Falling back to hash-based embeddings")
                self.use_neural = False
                self.model = HashEmbedder(EMBEDDING_DIM)
        else:
            print(f"Using hash-based embeddings (offline mode)")
            self.model = HashEmbedder(EMBEDDING_DIM)

        self.vec_conn = init_vec_db(vec_db_path)
        self._next_rowid = self._get_max_rowid() + 1
        print(f"  Vector DB: {vec_db_path}")
        print(f"  Next rowid: {self._next_rowid}")

    def _get_max_rowid(self) -> int:
        """Get the maximum rowid currently in use."""
        row = self.vec_conn.execute(
            "SELECT MAX(rowid) FROM embedding_metadata"
        ).fetchone()
        return row[0] if row[0] else 0

    def extract_text(self, thought: Thought) -> str:
        """Extract indexable text from a thought."""
        content = thought.content

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            parts = []
            # Priority order for text extraction
            for key in ['text', 'body', 'title', 'summary', 'description', 'name']:
                if key in content:
                    parts.append(str(content[key]))

            if parts:
                return ' '.join(parts)

            # Fallback: serialize the whole dict
            return json.dumps(content)

        return str(content)

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if self.use_neural:
            embedding = self.model.encode(text, convert_to_numpy=True)
        else:
            embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_thought(self, thought: Thought, pool_cid: Optional[str] = None) -> int:
        """
        Embed a thought and store in vector DB.
        Returns the rowid assigned to this embedding.
        """
        # Check if already embedded
        existing = self.vec_conn.execute(
            "SELECT rowid FROM embedding_metadata WHERE cid = ?",
            (thought.cid,)
        ).fetchone()

        if existing:
            return existing[0]

        # Extract and embed text
        text = self.extract_text(thought)
        embedding = self.embed_text(text)

        # Store embedding in virtual table
        rowid = self._next_rowid
        self._next_rowid += 1

        self.vec_conn.execute(
            "INSERT INTO thought_embeddings(rowid, embedding) VALUES (?, ?)",
            (rowid, serialize_vector(embedding))
        )

        # Store metadata
        self.vec_conn.execute("""
            INSERT INTO embedding_metadata (rowid, cid, pool_cid, text_content, thought_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            rowid,
            thought.cid,
            pool_cid,
            text[:500],  # Truncate for storage
            thought.type,
            thought.created_at
        ))

        try:
            self.vec_conn.commit()
        except sqlite3.OperationalError:
            # iCloud sync issue - reconnect to fallback
            import tempfile
            fallback_path = Path(tempfile.gettempdir()) / "wellspring_vec.db"
            print(f"  Reconnecting to fallback: {fallback_path}")
            self.vec_conn.close()
            self.vec_conn = init_vec_db(fallback_path)
            # Re-insert (previous insert was rolled back)
            self.vec_conn.execute(
                "INSERT INTO thought_embeddings(rowid, embedding) VALUES (?, ?)",
                (rowid, serialize_vector(embedding))
            )
            self.vec_conn.execute("""
                INSERT INTO embedding_metadata (rowid, cid, pool_cid, text_content, thought_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rowid, thought.cid, pool_cid, text[:500], thought.type, thought.created_at))
            self.vec_conn.commit()

        return rowid

    def embed_many(self, thoughts: List[Thought], pool_cid: Optional[str] = None) -> List[int]:
        """Batch embed multiple thoughts."""
        rowids = []
        for thought in thoughts:
            rowid = self.embed_thought(thought, pool_cid)
            rowids.append(rowid)
        return rowids

    # =========================================================================
    # APPETITE NOTES (Thread 1 spec)
    # =========================================================================

    # Valid appetite statuses per Thread 1 schemas-core.md
    APPETITE_STATUSES = {
        'welcomed': 1.0,           # Full index, high priority
        'unauthorized_claim': 0.3, # Index but flag, low weight
        'unverified_source': 0.5,  # Index, medium weight
        'low_trust_path': 0.4,     # Index, lower weight
        'pending_attestation': 0.0, # Don't surface yet
        'flagged': 0.1,            # Index but heavily downweight
    }

    def set_appetite(self, cid: str, status: str, trust_weight: Optional[float] = None):
        """
        Set appetite note for a thought.

        Args:
            cid: Thought CID
            status: One of APPETITE_STATUSES keys
            trust_weight: Override weight (default: derived from status)
        """
        if status not in self.APPETITE_STATUSES:
            raise ValueError(f"Invalid appetite status: {status}")

        weight = trust_weight if trust_weight is not None else self.APPETITE_STATUSES[status]

        self.vec_conn.execute("""
            UPDATE embedding_metadata
            SET appetite_status = ?, trust_weight = ?
            WHERE cid = ?
        """, (status, weight, cid))
        self.vec_conn.commit()

    def set_trust_weight(self, cid: str, weight: float):
        """Set trust weight for a thought (0.0 to 1.0+)."""
        self.vec_conn.execute("""
            UPDATE embedding_metadata
            SET trust_weight = ?
            WHERE cid = ?
        """, (weight, cid))
        self.vec_conn.commit()

    def set_chain_depth(self, cid: str, depth: int):
        """Set chain depth (hops in because chain from query context)."""
        self.vec_conn.execute("""
            UPDATE embedding_metadata
            SET chain_depth = ?
            WHERE cid = ?
        """, (depth, cid))
        self.vec_conn.commit()

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        pool_cid: Optional[str] = None,
        apply_trust_weighting: bool = True,
        exclude_pending: bool = True,
        recency_decay: float = 0.0001  # Per-hour decay factor
    ) -> List[Tuple[str, float, str, Dict[str, Any]]]:
        """
        Query for similar thoughts with trust-weighted retrieval.

        Args:
            query_text: Query string
            top_k: Max results
            pool_cid: Pool scope filter
            apply_trust_weighting: Apply trust/appetite weighting
            exclude_pending: Filter out pending_attestation thoughts
            recency_decay: Decay factor for older thoughts (0 = no decay)

        Returns: [(cid, relevance_score, text_snippet, metadata), ...]
        Higher relevance = more relevant (combines similarity + trust).
        """
        import time
        query_embedding = np.array(self.embed_text(query_text))
        now_ms = int(time.time() * 1000)

        # Fetch all embeddings with trust metadata
        base_query = """
            SELECT m.cid, e.embedding, m.text_content,
                   m.appetite_status, m.trust_weight, m.chain_depth, m.created_at
            FROM thought_embeddings e
            JOIN embedding_metadata m ON e.rowid = m.rowid
        """

        if pool_cid:
            rows = self.vec_conn.execute(base_query + " WHERE m.pool_cid = ?", (pool_cid,)).fetchall()
        else:
            rows = self.vec_conn.execute(base_query).fetchall()

        results = []
        for cid, emb_bytes, text, appetite, trust_weight, chain_depth, created_at in rows:
            # Skip pending attestation if requested
            if exclude_pending and appetite == 'pending_attestation':
                continue

            # Compute base similarity (convert distance to similarity)
            emb = np.array(deserialize_vector(emb_bytes))
            dist = cosine_distance(query_embedding, emb)
            similarity = 1.0 - dist  # 0-1 range

            if apply_trust_weighting:
                # Trust weight from appetite (0.0 - 1.0+)
                trust = trust_weight if trust_weight else 1.0

                # Chain proximity boost (closer = better)
                chain_boost = 1.0 / (1.0 + (chain_depth or 0) * 0.1)

                # Recency decay (hours since creation)
                if recency_decay > 0 and created_at:
                    hours_old = (now_ms - created_at) / (1000 * 60 * 60)
                    recency = max(0.5, 1.0 - recency_decay * hours_old)
                else:
                    recency = 1.0

                # Combined relevance: similarity * trust * chain_boost * recency
                relevance = similarity * trust * chain_boost * recency
            else:
                relevance = similarity

            metadata = {
                'appetite': appetite,
                'trust_weight': trust_weight,
                'chain_depth': chain_depth,
                'similarity': round(similarity, 4),
                'created_at': created_at
            }

            results.append((cid, relevance, text, metadata))

        # Sort by relevance (higher = better)
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def find_similar(self, cid: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Find thoughts similar to a given thought CID."""
        # Get the embedding for the source thought
        row = self.vec_conn.execute("""
            SELECT e.embedding
            FROM thought_embeddings e
            JOIN embedding_metadata m ON e.rowid = m.rowid
            WHERE m.cid = ?
        """, (cid,)).fetchone()

        if not row:
            return []

        source_emb = np.array(deserialize_vector(row[0]))

        # Fetch all other embeddings
        rows = self.vec_conn.execute("""
            SELECT m.cid, e.embedding
            FROM thought_embeddings e
            JOIN embedding_metadata m ON e.rowid = m.rowid
            WHERE m.cid != ?
        """, (cid,)).fetchall()

        # Compute distances
        results = []
        for other_cid, emb_bytes in rows:
            emb = np.array(deserialize_vector(emb_bytes))
            dist = cosine_distance(source_emb, emb)
            results.append((other_cid, dist))

        results.sort(key=lambda x: x[1])
        return results[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index."""
        total = self.vec_conn.execute(
            "SELECT COUNT(*) FROM embedding_metadata"
        ).fetchone()[0]

        by_type = self.vec_conn.execute("""
            SELECT thought_type, COUNT(*)
            FROM embedding_metadata
            GROUP BY thought_type
        """).fetchall()

        by_pool = self.vec_conn.execute("""
            SELECT pool_cid, COUNT(*)
            FROM embedding_metadata
            WHERE pool_cid IS NOT NULL
            GROUP BY pool_cid
        """).fetchall()

        return {
            "total_embeddings": total,
            "by_type": dict(by_type),
            "by_pool": dict(by_pool),
            "embedding_dim": EMBEDDING_DIM,
            "model": EMBEDDING_MODEL if self.use_neural else "hash-based (offline)"
        }

    def close(self):
        """Close database connection."""
        self.vec_conn.close()

# ============================================================================
# INTEGRATION WITH WELLSPRING_CORE
# ============================================================================

class WellspringRAG:
    """
    High-level RAG interface that combines:
    - wellspring_core.py for thought storage
    - sqlite-vec for vector search
    """

    def __init__(self,
                 thought_db_path: Path = DB_PATH,
                 vec_db_path: Path = VEC_DB_PATH):
        self.thought_db_path = thought_db_path
        self.pipeline = EmbeddingPipeline(vec_db_path)

    def index_all_thoughts(self, pool_cid: Optional[str] = None) -> int:
        """Index all existing thoughts from wellspring_core storage."""
        thoughts = query_thoughts(limit=10000, db_path=self.thought_db_path)

        indexed = 0
        for thought in thoughts:
            # Skip non-content thoughts (like identity, pool definitions)
            if thought.type in ['identity', 'pool']:
                continue

            self.pipeline.embed_thought(thought, pool_cid)
            indexed += 1

        return indexed

    def store_and_index(
        self,
        thought: Thought,
        pool_cid: Optional[str] = None
    ) -> str:
        """Store a thought in both thought DB and vector index."""
        store_thought(thought, db_path=self.thought_db_path)
        self.pipeline.embed_thought(thought, pool_cid)
        return thought.cid

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        pool_cid: Optional[str] = None,
        include_thoughts: bool = True,
        apply_trust_weighting: bool = True,
        exclude_pending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant thoughts for a query with trust-weighted ranking.

        Args:
            query: Search query
            top_k: Max results
            pool_cid: Pool scope filter
            include_thoughts: Include full Thought objects
            apply_trust_weighting: Apply appetite/trust weighting
            exclude_pending: Filter out pending_attestation thoughts

        Returns list of:
        {
            "cid": str,
            "relevance": float,  # Combined score (higher = better)
            "similarity": float,  # Raw semantic similarity
            "snippet": str,
            "appetite": str,     # Appetite status
            "trust_weight": float,
            "thought": Thought (optional)
        }
        """
        results = self.pipeline.query(
            query, top_k, pool_cid,
            apply_trust_weighting=apply_trust_weighting,
            exclude_pending=exclude_pending
        )

        output = []
        for cid, relevance, snippet, metadata in results:
            entry = {
                "cid": cid,
                "relevance": round(relevance, 4),
                "similarity": metadata.get('similarity', relevance),
                "snippet": snippet,
                "appetite": metadata.get('appetite', 'welcomed'),
                "trust_weight": metadata.get('trust_weight', 1.0),
                "chain_depth": metadata.get('chain_depth', 0)
            }

            if include_thoughts:
                thought = get_thought(cid, db_path=self.thought_db_path)
                if thought:
                    entry["thought"] = thought

            output.append(entry)

        return output

    def set_appetite(self, cid: str, status: str, trust_weight: Optional[float] = None):
        """Set appetite note for a thought. Delegates to pipeline."""
        self.pipeline.set_appetite(cid, status, trust_weight)

    def get_context(
        self,
        query: str,
        max_tokens: int = 2000,
        top_k: int = 5,
        pool_cid: Optional[str] = None
    ) -> str:
        """
        Generate a context window for LLM injection.
        Walks because chains to include grounding.
        """
        results = self.retrieve(query, top_k, pool_cid, include_thoughts=True)

        context_parts = []
        token_estimate = 0
        included_cids = set()

        def add_thought(thought: Thought, depth: int = 0):
            nonlocal token_estimate

            if thought.cid in included_cids:
                return
            if token_estimate > max_tokens:
                return

            text = self.pipeline.extract_text(thought)
            tokens = len(text) // 4  # Rough estimate

            if token_estimate + tokens > max_tokens:
                return

            included_cids.add(thought.cid)
            token_estimate += tokens

            prefix = "  " * depth
            context_parts.append(f"{prefix}[{thought.type}] {text}")

            # Walk because chain (limited depth)
            if depth < 2:
                for ref_cid in thought.because:
                    ref_thought = get_thought(ref_cid, db_path=self.thought_db_path)
                    if ref_thought:
                        add_thought(ref_thought, depth + 1)

        for result in results:
            if "thought" in result and result["thought"]:
                add_thought(result["thought"])

        return "\n".join(context_parts)

    def close(self):
        """Close connections."""
        self.pipeline.close()

# ============================================================================
# CLI / TEST
# ============================================================================

def main():
    print("=" * 70)
    print("Thread 2: RAG/Vector Indexing with sqlite-vec")
    print("=" * 70)

    # Initialize RAG
    print("\n[1] Initializing RAG pipeline...")
    rag = WellspringRAG()

    # Check existing thoughts
    print("\n[2] Checking existing thoughts in wellspring_core...")
    thoughts = query_thoughts(limit=100)
    print(f"    Found {len(thoughts)} thoughts")

    # Index existing thoughts
    if thoughts:
        print("\n[3] Indexing existing thoughts...")
        indexed = rag.index_all_thoughts()
        print(f"    Indexed {indexed} thoughts")
    else:
        print("\n[3] No existing thoughts. Creating test data...")

        # Create test identity
        identity = create_identity("rag-test-user")

        # Create some test thoughts
        test_contents = [
            ("The transformer architecture uses self-attention mechanisms to process sequences in parallel.", "research"),
            ("Climate change is causing rising sea levels and extreme weather events.", "note"),
            ("Semantic similarity search uses vector embeddings to find related content.", "finding"),
            ("WoT uses signed thoughts with CID references for provenance tracking.", "decision"),
            ("The because chain creates a DAG of thought dependencies.", "observation"),
        ]

        for content, ttype in test_contents:
            thought = create_thought(
                content=content,
                thought_type=ttype,
                identity=identity,
                source="thread-2/test"
            )
            rag.store_and_index(thought)
            print(f"    Created: [{ttype}] {content[:50]}...")

    # Test retrieval
    print("\n[4] Testing retrieval...")
    queries = [
        "How do transformers work?",
        "What is the impact of climate change?",
        "How does WoT track thought provenance?"
    ]

    for query in queries:
        print(f"\n    Query: \"{query}\"")
        results = rag.retrieve(query, top_k=3)
        for i, r in enumerate(results):
            print(f"    {i+1}. (sim={r['similarity']:.3f}) {r['snippet'][:60]}...")

    # Generate context
    print("\n[5] Generating context window...")
    context = rag.get_context("vector search and semantic similarity", max_tokens=500)
    print(f"\n{context}")

    # Stats
    print("\n[6] Index statistics:")
    stats = rag.pipeline.get_stats()
    print(f"    Total embeddings: {stats['total_embeddings']}")
    print(f"    By type: {stats['by_type']}")
    print(f"    Model: {stats['model']}")

    rag.close()
    print("\n" + "=" * 70)
    print("Done!")

if __name__ == "__main__":
    main()
