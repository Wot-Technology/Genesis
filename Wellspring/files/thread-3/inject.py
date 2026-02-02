#!/usr/bin/env python3
"""
Inject thoughts into the WoT daemon.

Usage:
    # Inject text directly
    python inject.py --text "My insight here" --type insight --pool wot

    # Pipe content in
    echo "Some trace data" | python inject.py --type trace --pool wot

    # Inject JSON content
    python inject.py --json '{"key": "value"}' --type basic --pool wot

    # With because chain
    python inject.py --text "Builds on prior" --because cid:blake3:abc123...

    # From file
    cat trace.json | python inject.py --type trace --pool wot
"""

# Suppress tokenizers warning
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
import json
import argparse
from pathlib import Path

import core
import pool as pool_mgmt

# Thread-2 RAG
THREAD2_DIR = Path(__file__).parent.parent / "thread-2"
sys.path.insert(0, str(THREAD2_DIR))


def inject_thought(
    content: any,
    thought_type: str = "basic",
    pool_name: str = "wot",
    because: list = None,
    source: str = "inject/cli",
    identity: core.Identity = None
) -> core.Thought:
    """Inject a thought into the system."""

    # Find pool
    pools = pool_mgmt.list_pools()
    pool = None
    for p in pools:
        if pool_name.lower() in p.name.lower():
            pool = p
            break

    if not pool:
        # Use default
        pool = pool_mgmt.get_default_pool(identity)

    # Create thought
    thought = core.create_thought(
        content=content,
        thought_type=thought_type,
        identity=identity,
        because=because or [],
        visibility=f"pool:{pool.cid}",
        source=source
    )

    # Store
    core.store_thought(thought)

    # Index in RAG
    try:
        from wellspring_embeddings import WellspringRAG
        rag = WellspringRAG(
            thought_db_path=core.DB_PATH,
            vec_db_path=Path(__file__).parent / "wellspring_vec.db"
        )
        rag.pipeline.embed_thought(thought, pool.cid)
        rag.close()
    except ImportError:
        pass  # RAG not available

    return thought, pool


def main():
    parser = argparse.ArgumentParser(
        description="Inject thoughts into WoT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inject.py --text "My insight" --type insight
  echo "trace data" | python inject.py --type trace
  python inject.py --json '{"key": "val"}' --type basic
  python inject.py --text "builds on X" --because cid:blake3:abc...
        """
    )
    parser.add_argument('--text', '-t', help="Text content to inject")
    parser.add_argument('--json', '-j', help="JSON content to inject")
    parser.add_argument('--type', '-T', default="basic",
                        help="Thought type (basic, insight, trace, decision, etc.)")
    parser.add_argument('--pool', '-p', default="wot",
                        help="Pool name to inject into")
    parser.add_argument('--because', '-b', action='append', default=[],
                        help="CID(s) this thought builds on (can repeat)")
    parser.add_argument('--source', '-s', default="inject/cli",
                        help="Source identifier")
    parser.add_argument('--quiet', '-q', action='store_true',
                        help="Only output CID")

    args = parser.parse_args()

    # Load identity
    identity_path = Path(__file__).parent / "daemon-identity.json"
    if identity_path.exists():
        identity = core.load_identity(identity_path)
    else:
        identity = core.create_identity("inject-user")
        core.save_identity(identity, identity_path)

    # Get content
    if args.text:
        content = args.text
    elif args.json:
        content = json.loads(args.json)
    elif not sys.stdin.isatty():
        # Read from stdin
        stdin_data = sys.stdin.read().strip()
        # Try to parse as JSON, fall back to text
        try:
            content = json.loads(stdin_data)
        except json.JSONDecodeError:
            content = stdin_data
    else:
        parser.error("Provide --text, --json, or pipe content via stdin")

    # Inject
    thought, pool = inject_thought(
        content=content,
        thought_type=args.type,
        pool_name=args.pool,
        because=args.because,
        source=args.source,
        identity=identity
    )

    if args.quiet:
        print(thought.cid)
    else:
        print(f"Injected [{args.type}] into pool '{pool.name}'")
        print(f"  CID: {thought.cid}")
        if args.because:
            print(f"  Because: {', '.join(args.because)}")


if __name__ == "__main__":
    main()
