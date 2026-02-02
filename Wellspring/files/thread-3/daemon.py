#!/usr/bin/env python3
"""
WoT Daemon - Thread 3 Peer Service

Runs a gRPC server for peer-to-peer thought sharing.

Usage:
    # Start server on default port
    python daemon.py

    # Start on specific port
    python daemon.py --port 50052

    # Connect to another peer and sync
    python daemon.py --connect localhost:50051

    # Push thoughts to peer
    python daemon.py --push localhost:50051

    # Query peer's index
    python daemon.py --query localhost:50051 "search terms"
"""

# Suppress tokenizers parallelism warning - must be before any imports
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
import json
import sys
import time
import signal
from pathlib import Path
from concurrent import futures

import grpc

import core
import pool as pool_mgmt
import wot_peer_pb2_grpc as pb_grpc
from peer_service import WotPeerService, WotPeerClient

# Default configuration
DEFAULT_PORT = 50051
IDENTITY_PATH = Path(__file__).parent / "daemon-identity.json"


def load_or_create_identity() -> core.Identity:
    """Load existing identity or create new one."""
    if IDENTITY_PATH.exists():
        return core.load_identity(IDENTITY_PATH)

    identity = core.create_identity("wot-daemon")
    core.save_identity(identity, IDENTITY_PATH)
    print(f"Created daemon identity: {identity.cid}")
    return identity


def run_server(port: int, identity: core.Identity):
    """Run gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    service = WotPeerService(identity)
    pb_grpc.add_WotPeerServicer_to_server(service, server)

    address = f"[::]:{port}"
    server.add_insecure_port(address)
    server.start()

    print(f"=" * 60)
    print(f"WoT Daemon started on port {port}")
    print(f"Identity: {identity.cid}")
    print(f"=" * 60)
    print(f"\nTo connect from another instance:")
    print(f"  python daemon.py --connect localhost:{port}")
    print(f"\nPress Ctrl+C to stop\n")

    # Handle shutdown
    def shutdown(sig, frame):
        print("\nShutting down...")
        server.stop(grace=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.wait_for_termination()


def connect_and_sync(address: str, identity: core.Identity):
    """Connect to peer and sync thoughts."""
    print(f"Connecting to {address}...")

    client = WotPeerClient(address, identity)
    if not client.connect():
        return

    print("Syncing...")
    count = client.sync()
    print(f"Peer has {count} thoughts")

    client.close()


def push_thoughts(address: str, identity: core.Identity, limit: int = 100):
    """Push local thoughts to peer."""
    print(f"Connecting to {address}...")

    client = WotPeerClient(address, identity)
    if not client.connect():
        return

    thoughts = core.query_thoughts(limit=limit)
    print(f"Pushing {len(thoughts)} thoughts...")

    acks = client.push_thoughts(thoughts)
    accepted = sum(1 for a in acks if a.status == 1)  # ACK_ACCEPTED
    print(f"Pushed: {accepted} accepted, {len(acks) - accepted} rejected")

    client.close()


def query_peer(address: str, identity: core.Identity, query: str, top_k: int = 10):
    """Query peer's thought index."""
    print(f"Connecting to {address}...")

    client = WotPeerClient(address, identity)
    if not client.connect():
        return

    print(f"Querying: '{query}'...")
    results = client.query(query, top_k)

    print(f"\n{len(results)} results:")
    for i, r in enumerate(results):
        print(f"  {i+1}. (rel={r['similarity']:.3f}) {r['snippet'][:60]}...")

    client.close()


def seed_data(identity: core.Identity):
    """Create default pool and seed test thoughts."""
    print("Seeding test data...")

    # Create default pool
    pool = pool_mgmt.get_default_pool(identity)
    print(f"Pool: {pool.cid}")
    print(f"  Waterline: {pool.rules.waterline}")

    # Check existing thoughts
    existing = core.query_thoughts(limit=100)
    if len(existing) > 5:
        print(f"Already have {len(existing)} thoughts, skipping seed")
        return pool

    # Seed some test thoughts
    test_data = [
        ("WoT uses content-addressed thoughts connected by CIDs for provenance tracking.", "insight"),
        ("The because chain creates an audit trail of reasoning and context.", "insight"),
        ("Bloom filters enable efficient sync by identifying missing thoughts.", "finding"),
        ("Pool rules define waterline thresholds for relevance filtering.", "decision"),
        ("Attestations from trusted identities boost thought visibility.", "insight"),
        ("The subconscious layer uses 1-bit LLMs for fast candidate retrieval.", "finding"),
        ("Agents earn expanded capabilities through demonstrated safe behavior.", "insight"),
        ("Each thought is signed with ed25519 for authentication.", "finding"),
        ("Pools can spawn working areas for multi-agent deliberation.", "insight"),
        ("The conscious layer has full context and decision authority.", "insight"),
    ]

    for content, thought_type in test_data:
        thought = core.create_thought(
            content=content,
            thought_type=thought_type,
            identity=identity,
            visibility=f"pool:{pool.cid}",
            source="seed/test"
        )
        core.store_thought(thought)
        print(f"  Created: [{thought_type}] {content[:50]}...")

    print(f"Seeded {len(test_data)} thoughts")
    return pool


def set_waterline(pool_cid: str, waterline: float, identity: core.Identity):
    """Update pool waterline threshold."""
    if pool_mgmt.update_waterline(pool_cid, waterline, identity):
        print(f"Updated waterline to {waterline}")
    else:
        print(f"Failed to update waterline (pool not found?)")


def dedupe_thoughts():
    """Remove duplicate thoughts (keep oldest by CID)."""
    import blake3

    print("Deduplicating thoughts...")
    thoughts = core.query_thoughts(limit=50000)
    print(f"  Total thoughts: {len(thoughts)}")

    # Group by content hash
    by_hash = {}
    for t in thoughts:
        canonical = json.dumps({"type": t.type, "content": t.content}, sort_keys=True)
        h = blake3.blake3(canonical.encode()).hexdigest()[:32]
        if h not in by_hash:
            by_hash[h] = []
        by_hash[h].append(t)

    # Find duplicates (keep first/oldest)
    dupes = []
    for h, group in by_hash.items():
        if len(group) > 1:
            # Sort by created_at, keep oldest
            group.sort(key=lambda t: t.created_at)
            dupes.extend(group[1:])  # Mark all but first as dupes

    if not dupes:
        print("  No duplicates found")
        return

    print(f"  Found {len(dupes)} duplicates to remove")

    # Remove from DB
    import sqlite3
    conn = sqlite3.connect(core.DB_PATH)
    for t in dupes:
        conn.execute("DELETE FROM thoughts WHERE cid = ?", (t.cid,))
    conn.commit()
    conn.close()

    print(f"  Removed {len(dupes)} duplicate thoughts")
    print(f"  Remaining: {len(thoughts) - len(dupes)} thoughts")


def index_thoughts(pool_cid: str = None):
    """Index all thoughts in RAG for search."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "thread-2"))
        from wellspring_embeddings import WellspringRAG

        print("Indexing thoughts in RAG...")
        print(f"  DB: {core.DB_PATH}")
        if pool_cid:
            print(f"  Pool: {pool_cid[:40]}...")

        rag = WellspringRAG(
            thought_db_path=core.DB_PATH,
            vec_db_path=Path(__file__).parent / "wellspring_vec.db"
        )

        count = rag.index_all_thoughts(pool_cid=pool_cid)
        print(f"  Indexed: {count} thoughts")

        stats = rag.pipeline.get_stats()
        print(f"  Total embeddings: {stats['total_embeddings']}")
        print(f"  By type: {stats['by_type']}")

        rag.close()
    except ImportError as e:
        print(f"RAG not available: {e}")
        print("Install: pip install sentence-transformers numpy")


def reindex_for_pool(pool_name: str, identity: core.Identity):
    """Re-index existing thoughts into a specific pool."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "thread-2"))
        from wellspring_embeddings import WellspringRAG

        # Find or create pool
        pools = pool_mgmt.list_pools()
        pool = None
        for p in pools:
            if pool_name.lower() in p.name.lower():
                pool = p
                break

        if not pool:
            print(f"Pool '{pool_name}' not found. Creating...")
            pool = pool_mgmt.create_pool(
                name=pool_name,
                identity=identity,
                rules=pool_mgmt.PoolRules(waterline=0.3, require_because=False),
                description=f"Pool: {pool_name}"
            )

        print(f"Re-indexing thoughts into pool: {pool.name}")
        print(f"  Pool CID: {pool.cid[:40]}...")

        rag = WellspringRAG(
            thought_db_path=core.DB_PATH,
            vec_db_path=Path(__file__).parent / "wellspring_vec.db"
        )

        # Clear existing embeddings and re-index with pool_cid
        print("  Clearing vector DB...")
        rag.pipeline.vec_conn.execute("DELETE FROM thought_embeddings")
        rag.pipeline.vec_conn.execute("DELETE FROM embedding_metadata")
        rag.pipeline.vec_conn.commit()

        print("  Re-indexing all thoughts...")
        count = rag.index_all_thoughts(pool_cid=pool.cid)
        print(f"  Indexed: {count} thoughts into pool '{pool.name}'")

        stats = rag.pipeline.get_stats()
        print(f"  Total embeddings: {stats['total_embeddings']}")

        rag.close()
    except ImportError as e:
        print(f"RAG not available: {e}")


def main():
    parser = argparse.ArgumentParser(description="WoT Daemon")
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT,
                        help=f"Port to run server (default: {DEFAULT_PORT})")
    parser.add_argument('--connect', '-c', type=str,
                        help="Connect to peer and sync (e.g., localhost:50051)")
    parser.add_argument('--push', type=str,
                        help="Push thoughts to peer (e.g., localhost:50051)")
    parser.add_argument('--query', '-q', nargs=2, metavar=('ADDRESS', 'QUERY'),
                        help="Query peer's index")
    parser.add_argument('--limit', '-l', type=int, default=100,
                        help="Limit for push/query operations")
    parser.add_argument('--seed', action='store_true',
                        help="Create default pool and seed test thoughts")
    parser.add_argument('--waterline', '-w', type=float,
                        help="Set waterline threshold (0.0-1.0)")
    parser.add_argument('--index', action='store_true',
                        help="Index all thoughts in RAG for search")
    parser.add_argument('--reindex', type=str, metavar='POOL',
                        help="Re-index all thoughts into a specific pool (e.g., --reindex wot)")
    parser.add_argument('--dedupe', action='store_true',
                        help="Remove duplicate thoughts from DB")
    parser.add_argument('--chat', action='store_true',
                        help="Start interactive chat with WoT context injection")
    # Provider settings
    parser.add_argument('--provider',
                        choices=['anthropic', 'openai', 'azure-openai', 'azure-anthropic'],
                        default='anthropic',
                        help="LLM provider")
    parser.add_argument('--endpoint',
                        help="API endpoint URL")
    parser.add_argument('--api-key',
                        help="API key (or set WOT_API_KEY env var)")
    parser.add_argument('--deployment',
                        help="Deployment name for Azure")
    parser.add_argument('--model', '-m', default="claude-sonnet-4-20250514",
                        help="Model name to use")

    args = parser.parse_args()

    # Load identity
    identity = load_or_create_identity()

    if args.chat:
        import os
        from chat import run_chat_repl, ChatConfig
        # Resolve settings from args or env
        api_endpoint = args.endpoint or os.environ.get('WOT_API_ENDPOINT')
        api_key = args.api_key or os.environ.get('WOT_API_KEY')
        deployment = args.deployment or os.environ.get('WOT_DEPLOYMENT')

        config = ChatConfig(
            model=args.model,
            context_limit=args.limit,
            provider=args.provider,
            api_endpoint=api_endpoint,
            api_key=api_key,
            deployment_name=deployment
        )
        run_chat_repl(identity, config)
    elif args.dedupe:
        dedupe_thoughts()
    elif args.index:
        index_thoughts()
    elif args.reindex:
        reindex_for_pool(args.reindex, identity)
    elif args.seed:
        seed_data(identity)
    elif args.waterline is not None:
        # Get default pool and update waterline
        pool = pool_mgmt.get_default_pool(identity)
        set_waterline(pool.cid, args.waterline, identity)
    elif args.connect:
        connect_and_sync(args.connect, identity)
    elif args.push:
        push_thoughts(args.push, identity, args.limit)
    elif args.query:
        address, query = args.query
        query_peer(address, identity, query, args.limit)
    else:
        run_server(args.port, identity)


if __name__ == "__main__":
    main()
