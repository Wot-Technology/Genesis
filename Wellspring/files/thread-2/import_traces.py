#!/usr/bin/env python3
"""
Import trace thoughts from all threads into the RAG pipeline.
Tests embed→store→retrieve with real WoT development content.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from wellspring_core import create_thought, create_identity, store_thought, Thought
from wellspring_embeddings import WellspringRAG, EmbeddingPipeline

# ============================================================================
# IMPORT TRACES
# ============================================================================

def load_traces(trace_file: Path) -> list:
    """Load trace thoughts from JSONL file."""
    traces = []
    with open(trace_file) as f:
        for line in f:
            line = line.strip()
            if line:
                traces.append(json.loads(line))
    return traces

def import_traces():
    print("=" * 70)
    print("Importing Thread Traces into RAG")
    print("=" * 70)

    # Find all trace files
    files_dir = Path(__file__).parent.parent
    trace_files = list(files_dir.glob("thread-*/traces.jsonl"))
    trace_files.append(files_dir / "traces.jsonl")  # Root traces if exists

    print(f"\nFound trace files:")
    for f in trace_files:
        if f.exists():
            print(f"  {f}")

    # Create identity for imports
    identity = create_identity("trace-importer")
    print(f"\nImport identity: {identity.cid[:16]}...")

    # Initialize RAG
    print("\nInitializing RAG pipeline...")
    rag = WellspringRAG()

    # Import each trace file
    total_imported = 0
    for trace_file in trace_files:
        if not trace_file.exists():
            continue

        traces = load_traces(trace_file)
        print(f"\n{trace_file.name}: {len(traces)} traces")

        for trace in traces:
            content = trace.get("content", {})

            # Create thought from trace
            thought = create_thought(
                content=content,
                thought_type="trace",
                identity=identity,
                source=trace.get("source", "import"),
                because=trace.get("because", [])
            )

            # Store and index
            rag.store_and_index(thought, pool_cid=None)
            total_imported += 1

            # Show progress
            title = content.get("title", "")[:50]
            category = content.get("category", "?")
            print(f"    [{category}] {title}")

    print(f"\n{'=' * 70}")
    print(f"Imported {total_imported} traces")

    # Test retrieval
    print(f"\n{'=' * 70}")
    print("Testing retrieval...")
    print("=" * 70)

    queries = [
        "How is the CID computed?",
        "What hash algorithm is used?",
        "How does pool membership work?",
        "What is chain access?",
        "How are embeddings stored?",
    ]

    for query in queries:
        print(f"\nQuery: \"{query}\"")
        results = rag.retrieve(query, top_k=3)
        for i, r in enumerate(results):
            snippet = r['snippet'][:60] if r['snippet'] else "?"
            print(f"  {i+1}. (sim={r['similarity']:.3f}) {snippet}...")

    # Stats
    print(f"\n{'=' * 70}")
    print("Index Stats:")
    stats = rag.pipeline.get_stats()
    print(f"  Total embeddings: {stats['total_embeddings']}")
    print(f"  Model: {stats['model']}")

    rag.close()
    print("\nDone!")

if __name__ == "__main__":
    import_traces()
