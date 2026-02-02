#!/usr/bin/env python3
"""
Hybrid Search Benchmark: BM25 + Vector + Fusion
Run locally with Ollama: python3 hybrid_benchmark.py

Requirements:
  pip install chromadb rank-bm25 requests
  ollama pull nomic-embed-text
"""

import os
import time
import json
import requests
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from rank_bm25 import BM25Okapi
import chromadb

# Config
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
DOCS_DIR = Path(__file__).parent.parent  # Wellspring Eternal folder
CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

TEST_QUERIES = [
    "BM25 vector hybrid search",
    "trust graph vouch revocation",
    "IPFS content addressing CID",
    "local inference without GPU",
    "sync protocol peer discovery",
    "encryption key rotation",
    "E5-small embeddings semantic",
    "Grassmann algebra subspace",
    "Web of Trust identity verification",
    "SQLite FTS5 full text search",
]


@dataclass
class SearchResult:
    chunk_id: str
    doc_id: str
    score: float
    snippet: str
    method: str


def ollama_embed(texts: List[str], model: str = EMBED_MODEL) -> List[List[float]]:
    """Get embeddings from Ollama"""
    embeddings = []
    for text in texts:
        resp = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": model, "prompt": text}
        )
        resp.raise_for_status()
        embeddings.append(resp.json()["embedding"])
    return embeddings


def ollama_embed_batch(texts: List[str], model: str = EMBED_MODEL, batch_size: int = 50) -> List[List[float]]:
    """Batch embedding with progress"""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        print(f"    Embedding batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...")
        embs = ollama_embed(batch, model)
        all_embeddings.extend(embs)
    return all_embeddings


def load_documents(max_files: int = 12) -> List[Dict]:
    """Load markdown files from Wellspring directory"""
    docs = []
    md_files = sorted(
        [f for f in DOCS_DIR.rglob("*.md") if ".git" not in str(f) and "search-compare" not in str(f)],
        key=lambda p: p.stat().st_size,
        reverse=True
    )[:max_files]

    for fpath in md_files:
        try:
            content = fpath.read_text(encoding='utf-8', errors='ignore')
            if len(content) > 60000:
                content = content[:60000]
            docs.append({
                "id": str(fpath.relative_to(DOCS_DIR)),
                "content": content,
            })
        except Exception as e:
            print(f"  Skip {fpath.name}: {e}")
    return docs


def chunk_documents(docs: List[Dict]) -> List[Dict]:
    """Split documents into chunks"""
    chunks = []
    for doc in docs:
        content = doc["content"]
        start = 0
        idx = 0
        while start < len(content):
            end = start + CHUNK_SIZE
            text = content[start:end].strip()
            if text:
                chunks.append({
                    "id": f"{doc['id']}::{idx}",
                    "doc_id": doc["id"],
                    "content": text
                })
                idx += 1
            start = end - CHUNK_OVERLAP
    return chunks


class BM25Index:
    """BM25 keyword search"""

    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        self.tokenized = [c["content"].lower().split() for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized)

    def search(self, query: str, k: int = 10) -> List[SearchResult]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_k = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

        return [
            SearchResult(
                chunk_id=self.chunks[i]["id"],
                doc_id=self.chunks[i]["doc_id"],
                score=scores[i],
                snippet=self.chunks[i]["content"][:150],
                method="bm25"
            )
            for i in top_k
        ]


class VectorIndex:
    """Chroma vector search with Ollama embeddings"""

    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        self.client = chromadb.Client()
        self.collection = self.client.create_collection(
            name="wellspring",
            metadata={"hnsw:space": "cosine"}
        )

        # Embed and add
        texts = [c["content"] for c in chunks]
        embeddings = ollama_embed_batch(texts)

        self.collection.add(
            ids=[c["id"] for c in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"doc_id": c["doc_id"]} for c in chunks]
        )

    def search(self, query: str, k: int = 10) -> List[SearchResult]:
        query_emb = ollama_embed([query])[0]
        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=k
        )

        hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            hits.append(SearchResult(
                chunk_id=doc_id,
                doc_id=results["metadatas"][0][i]["doc_id"],
                score=1 - results["distances"][0][i],  # Convert distance to similarity
                snippet=results["documents"][0][i][:150],
                method="vector"
            ))
        return hits


def reciprocal_rank_fusion(
    results_list: List[List[SearchResult]],
    k: int = 60
) -> List[SearchResult]:
    """Combine rankings using RRF"""
    scores = {}
    chunks = {}

    for results in results_list:
        for rank, r in enumerate(results):
            if r.chunk_id not in scores:
                scores[r.chunk_id] = 0
                chunks[r.chunk_id] = r
            scores[r.chunk_id] += 1 / (k + rank + 1)

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    return [
        SearchResult(
            chunk_id=cid,
            doc_id=chunks[cid].doc_id,
            score=scores[cid],
            snippet=chunks[cid].snippet,
            method="hybrid_rrf"
        )
        for cid in sorted_ids
    ]


def evaluate_results(bm25_results: List[SearchResult],
                     vector_results: List[SearchResult],
                     hybrid_results: List[SearchResult]) -> Dict:
    """Compare result overlap"""
    bm25_top5 = {r.chunk_id for r in bm25_results[:5]}
    vec_top5 = {r.chunk_id for r in vector_results[:5]}
    hyb_top5 = {r.chunk_id for r in hybrid_results[:5]}

    return {
        "bm25_vec_overlap": len(bm25_top5 & vec_top5),
        "bm25_in_hybrid": len(bm25_top5 & hyb_top5),
        "vec_in_hybrid": len(vec_top5 & hyb_top5),
    }


def main():
    print("=" * 70)
    print("HYBRID SEARCH BENCHMARK: BM25 + Vector + RRF Fusion")
    print("=" * 70)

    # Check Ollama
    print("\n[0] Checking Ollama...")
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags")
        models = [m["name"] for m in resp.json().get("models", [])]
        if EMBED_MODEL not in models and f"{EMBED_MODEL}:latest" not in models:
            print(f"    WARNING: {EMBED_MODEL} not found. Available: {models}")
        else:
            print(f"    OK - using {EMBED_MODEL}")
    except Exception as e:
        print(f"    ERROR: Cannot reach Ollama at {OLLAMA_URL}: {e}")
        return

    # Load docs
    print("\n[1] Loading documents...")
    docs = load_documents()
    print(f"    Loaded {len(docs)} documents")

    # Chunk
    print("\n[2] Chunking...")
    chunks = chunk_documents(docs)
    print(f"    Created {len(chunks)} chunks")

    # Build BM25 index
    print("\n[3] Building BM25 index...")
    t0 = time.time()
    bm25_idx = BM25Index(chunks)
    bm25_time = time.time() - t0
    print(f"    Done in {bm25_time*1000:.1f}ms")

    # Build Vector index
    print("\n[4] Building Vector index (this takes a minute)...")
    t0 = time.time()
    vec_idx = VectorIndex(chunks)
    vec_time = time.time() - t0
    print(f"    Done in {vec_time:.1f}s")

    # Run queries
    print("\n[5] Running search queries...")
    print("-" * 70)

    all_metrics = []
    timing = {"bm25": [], "vector": [], "hybrid": []}

    for query in TEST_QUERIES:
        print(f"\n  Q: \"{query}\"")

        # BM25
        t0 = time.time()
        bm25_results = bm25_idx.search(query, k=10)
        timing["bm25"].append(time.time() - t0)

        # Vector
        t0 = time.time()
        vec_results = vec_idx.search(query, k=10)
        timing["vector"].append(time.time() - t0)

        # Hybrid
        t0 = time.time()
        hybrid_results = reciprocal_rank_fusion([bm25_results, vec_results])[:10]
        timing["hybrid"].append(time.time() - t0)

        # Compare
        metrics = evaluate_results(bm25_results, vec_results, hybrid_results)
        all_metrics.append(metrics)

        print(f"     BM25  → {bm25_results[0].doc_id[:45]}")
        print(f"     Vec   → {vec_results[0].doc_id[:45]}")
        print(f"     Hybrid→ {hybrid_results[0].doc_id[:45]}")
        print(f"     Overlap: BM25∩Vec={metrics['bm25_vec_overlap']}/5")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\n  Index build time:")
    print(f"    BM25:   {bm25_time*1000:>8.1f}ms")
    print(f"    Vector: {vec_time:>8.1f}s")

    print(f"\n  Avg query time:")
    print(f"    BM25:   {sum(timing['bm25'])/len(timing['bm25'])*1000:>8.2f}ms")
    print(f"    Vector: {sum(timing['vector'])/len(timing['vector'])*1000:>8.2f}ms")
    print(f"    Hybrid: {sum(timing['hybrid'])/len(timing['hybrid'])*1000:>8.2f}ms")

    avg_overlap = sum(m["bm25_vec_overlap"] for m in all_metrics) / len(all_metrics)
    print(f"\n  Avg BM25-Vector top-5 overlap: {avg_overlap:.1f}/5")

    print(f"\n  Interpretation:")
    if avg_overlap < 2:
        print("    → Low overlap: BM25 and Vector find DIFFERENT things")
        print("    → Hybrid fusion adds significant value")
    elif avg_overlap > 3:
        print("    → High overlap: both methods agree")
        print("    → Either method works, hybrid marginal benefit")
    else:
        print("    → Moderate overlap: complementary signals")
        print("    → Hybrid likely best choice")


if __name__ == "__main__":
    main()
