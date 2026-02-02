#!/usr/bin/env python3
"""
Ingest existing JSONL trace files into Thread 3 storage.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Any

import core

# Files to ingest (skip secrets)
WORKSPACE = Path(__file__).parent.parent
JSONL_FILES = [
    "wellspring-dogfood-001.jsonl",
    "wellspring-dogfood-002.jsonl",
    "wellspring-dogfood-003.jsonl",
    "wellspring-dogfood-004-public.jsonl",
    "wellspring-dogfood-005-revocation.jsonl",
    "wellspring-dogfood-006-vouch.jsonl",
    "wellspring-dogfood-007-rotation.jsonl",
    "wellspring-dogfood-008-hello.jsonl",
    "wellspring-dogfood-009-appetite.jsonl",
    "wellspring-dogfood-010-peering.jsonl",
    "wellspring-dogfood-011-trust-network.jsonl",
    "wellspring-dogfood-012-speed.jsonl",
    "wellspring-dogfood-013-crypto.jsonl",
    "wellspring-dogfood-014-speed-crypto.jsonl",
    "wellspring-dogfood-015-boundary.jsonl",
    "traces.jsonl",
    "thread-1/traces.jsonl",
    "thread-2/traces.jsonl",
]


def content_hash(content: Any, thought_type: str) -> str:
    """Compute stable hash of content for deduplication."""
    import blake3
    canonical = json.dumps({"type": thought_type, "content": content}, sort_keys=True)
    return blake3.blake3(canonical.encode()).hexdigest()[:32]


# Track imported content hashes to avoid duplicates
_imported_hashes: set = set()


def load_existing_hashes():
    """Load content hashes of existing thoughts."""
    global _imported_hashes
    if _imported_hashes:
        return  # Already loaded

    thoughts = core.query_thoughts(limit=50000)
    for t in thoughts:
        h = content_hash(t.content, t.type)
        _imported_hashes.add(h)
    print(f"  Loaded {len(_imported_hashes)} existing content hashes")


def ingest_jsonl(filepath: Path, identity: core.Identity) -> int:
    """Ingest a JSONL file, return count of imported thoughts."""
    if not filepath.exists():
        print(f"  Skipping (not found): {filepath.name}")
        return 0

    count = 0
    skipped = 0
    errors = 0

    with open(filepath) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)

                # Handle different JSONL formats
                content = data.get('content', data.get('body', data))
                thought_type = data.get('type', 'trace')
                because = data.get('because', [])
                source = data.get('source', f"import/{filepath.stem}")
                visibility = data.get('visibility')

                # Skip if already has CID and exists
                if 'cid' in data:
                    existing = core.get_thought(data['cid'])
                    if existing:
                        skipped += 1
                        continue

                # Skip if content already imported (dedupe)
                h = content_hash(content, thought_type)
                if h in _imported_hashes:
                    skipped += 1
                    continue

                # Create thought with our identity
                thought = core.create_thought(
                    content=content,
                    thought_type=thought_type,
                    identity=identity,
                    because=because if isinstance(because, list) else [],
                    visibility=visibility,
                    source=source
                )
                core.store_thought(thought)
                _imported_hashes.add(h)
                count += 1

            except json.JSONDecodeError as e:
                errors += 1
                if errors <= 3:
                    print(f"    JSON error line {line_num}: {e}")
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"    Error line {line_num}: {e}")

    if skipped > 0:
        print(f"  Skipped {skipped} duplicates")
    return count


def index_in_rag():
    """Index all thoughts in RAG for search."""
    try:
        import sys
        sys.path.insert(0, str(WORKSPACE / "thread-2"))
        from wellspring_embeddings import WellspringRAG

        print("\nIndexing in RAG...")
        rag = WellspringRAG(
            thought_db_path=core.DB_PATH,
            vec_db_path=Path(__file__).parent / "wellspring_vec.db"
        )
        count = rag.index_all_thoughts()
        print(f"  Indexed: {count} thoughts")

        stats = rag.pipeline.get_stats()
        print(f"  Total embeddings: {stats['total_embeddings']}")
        rag.close()
        return count
    except ImportError as e:
        print(f"  RAG not available: {e}")
        return 0


def main():
    print("=" * 60)
    print("Ingesting JSONL trace files")
    print("=" * 60)

    # Load or create identity
    identity_path = Path(__file__).parent / "daemon-identity.json"
    if identity_path.exists():
        identity = core.load_identity(identity_path)
    else:
        identity = core.create_identity("ingest-worker")
        core.save_identity(identity, identity_path)

    print(f"Identity: {identity.cid[:40]}...")
    print(f"DB: {core.DB_PATH}")

    # Load existing content hashes for deduplication
    load_existing_hashes()
    print()

    total = 0
    for filename in JSONL_FILES:
        filepath = WORKSPACE / filename
        print(f"Processing: {filename}")
        count = ingest_jsonl(filepath, identity)
        if count > 0:
            print(f"  Imported: {count} thoughts")
        total += count

    print()
    print(f"Total imported: {total} thoughts")

    # Show stats
    all_thoughts = core.query_thoughts(limit=10000)
    print(f"Total in DB: {len(all_thoughts)} thoughts")

    # Index in RAG
    index_in_rag()


if __name__ == "__main__":
    main()
