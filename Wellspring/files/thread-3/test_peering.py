#!/usr/bin/env python3
"""
Test peer-to-peer thought sharing.

This script:
1. Starts a daemon server in a background thread
2. Creates a client connection
3. Pushes thoughts from client to server
4. Queries the server's index
5. Verifies the thoughts were received
"""

import time
import threading
from concurrent import futures
from pathlib import Path

import grpc

import core
import wot_peer_pb2 as pb
import wot_peer_pb2_grpc as pb_grpc
from peer_service import WotPeerService, WotPeerClient


def run_test():
    print("=" * 60)
    print("WoT Peer-to-Peer Test")
    print("=" * 60)

    # Create two identities (simulating two nodes)
    print("\n[1] Creating identities...")
    server_identity = core.create_identity("test-server")
    client_identity = core.create_identity("test-client")
    print(f"    Server: {server_identity.cid[:40]}...")
    print(f"    Client: {client_identity.cid[:40]}...")

    # Start server
    print("\n[2] Starting server on port 50098...")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    service = WotPeerService(server_identity)
    pb_grpc.add_WotPeerServicer_to_server(service, server)
    server.add_insecure_port("[::]:50098")
    server.start()
    print("    Server started")

    # Give server time to start
    time.sleep(0.5)

    try:
        # Create client
        print("\n[3] Connecting client...")
        client = WotPeerClient("localhost:50098", client_identity)
        assert client.connect(), "Failed to connect"
        print(f"    Connected: session={client.session_id}")

        # Create some test thoughts
        print("\n[4] Creating test thoughts...")
        thoughts = []
        for i in range(3):
            thought = core.create_thought(
                content=f"Test thought #{i+1} from peer test: The quick brown fox jumps over the lazy dog.",
                thought_type="basic",
                identity=client_identity,
                source="test/peering"
            )
            thoughts.append(thought)
            print(f"    Created: {thought.cid[:40]}...")

        # Push thoughts
        print("\n[5] Pushing thoughts to server...")
        acks = client.push_thoughts(thoughts)
        accepted = sum(1 for a in acks if a.status == pb.ACK_ACCEPTED)
        print(f"    Pushed {len(thoughts)} thoughts: {accepted} accepted")
        assert accepted == len(thoughts), f"Expected {len(thoughts)} accepted, got {accepted}"

        # Verify via heartbeat
        print("\n[6] Checking heartbeat...")
        stub = pb_grpc.WotPeerStub(client.channel)
        hb = stub.Heartbeat(pb.HeartbeatRequest(
            timestamp=int(time.time() * 1000),
            thought_count=0
        ))
        print(f"    Server has {hb.thought_count} thoughts")

        # Query (if RAG available)
        print("\n[7] Testing query...")
        results = client.query("quick brown fox", top_k=5)
        print(f"    Query returned {len(results)} results")
        for r in results:
            print(f"      - (sim={r['similarity']:.3f}) {r['snippet'][:50]}...")

        # Bloom exchange
        print("\n[8] Testing bloom filter exchange...")
        count = client.sync()
        print(f"    Sync complete: peer has {count} thoughts")

        client.close()

        print("\n" + "=" * 60)
        print("TEST PASSED")
        print("=" * 60)

    finally:
        print("\n[9] Shutting down server...")
        server.stop(grace=1)
        print("    Done")


if __name__ == "__main__":
    run_test()
