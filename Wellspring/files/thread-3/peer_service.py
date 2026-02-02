"""
WotPeer gRPC Service Implementation

Handles peer-to-peer thought sharing between WoT daemon instances.
"""

import time
import json
import hashlib
import struct
from pathlib import Path
from typing import Optional, List, Iterator
from dataclasses import asdict

import grpc
import blake3

import wot_peer_pb2 as pb
import wot_peer_pb2_grpc as pb_grpc
import core
import pool as pool_mgmt

# Lazy imports for optional dependencies
_rag = None


def get_rag():
    """Get RAG instance if available."""
    global _rag
    if _rag is None:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "thread-2"))
            from wellspring_embeddings import WellspringRAG
            _rag = WellspringRAG(
                thought_db_path=core.DB_PATH,
                vec_db_path=Path(__file__).parent / "wellspring_vec.db"  # Same dir as daemon
            )
        except ImportError:
            _rag = False
    return _rag if _rag else None


# ============================================================================
# BLOOM FILTER
# ============================================================================

class BloomFilter:
    """Simple bloom filter for CID set membership."""

    def __init__(self, m: int = 95851, k: int = 7):
        self.m = m  # bits
        self.k = k  # hash functions
        self.bits = bytearray((m + 7) // 8)

    def _hashes(self, item: bytes) -> List[int]:
        """Generate k hash positions for item."""
        positions = []
        for i in range(self.k):
            h = hashlib.sha256(item + i.to_bytes(1, 'big')).digest()
            pos = int.from_bytes(h[:4], 'big') % self.m
            positions.append(pos)
        return positions

    def add(self, item: bytes):
        """Add item to filter."""
        for pos in self._hashes(item):
            self.bits[pos // 8] |= (1 << (pos % 8))

    def contains(self, item: bytes) -> bool:
        """Check if item might be in filter."""
        for pos in self._hashes(item):
            if not (self.bits[pos // 8] & (1 << (pos % 8))):
                return False
        return True

    def to_bytes(self) -> bytes:
        return bytes(self.bits)

    @classmethod
    def from_bytes(cls, data: bytes, m: int, k: int) -> 'BloomFilter':
        bf = cls(m, k)
        bf.bits = bytearray(data)
        return bf


# ============================================================================
# SERIALIZATION
# ============================================================================

def thought_to_payload(thought: core.Thought) -> pb.ThoughtPayload:
    """Convert Thought to wire format."""
    # Build signable content for CBOR
    signable = {
        "type": thought.type,
        "content": thought.content,
        "created_by": thought.created_by,
        "created_at": thought.created_at,
        "because": thought.because,
    }
    if thought.visibility:
        signable["visibility"] = thought.visibility
    if thought.source:
        signable["source"] = thought.source

    # Canonical JSON as CBOR stand-in (TODO: actual CBOR)
    cbor_bytes = core.canonicalize(signable).encode()

    # Proto encoding (simplified - just JSON for now)
    proto_bytes = json.dumps(asdict(thought)).encode()

    # CID bytes
    cid_bytes = core.compute_cid_bytes(signable)

    return pb.ThoughtPayload(
        cid=cid_bytes,
        schema_cid=b'',  # TODO: schema registry
        thought_cbor=cbor_bytes,
        thought_proto=proto_bytes,
        signature=bytes.fromhex(thought.signature),
        source=thought.source or ''
    )


def payload_to_thought(payload: pb.ThoughtPayload) -> Optional[core.Thought]:
    """Convert wire format to Thought."""
    try:
        # Verify CID matches content
        computed_cid = blake3.blake3(payload.thought_cbor).digest()
        received_cid = payload.cid[4:]  # Strip 4-byte header
        if computed_cid != received_cid:
            print(f"CID mismatch: computed {computed_cid.hex()[:16]}... != received {received_cid.hex()[:16]}...")
            return None

        # Parse thought from proto (JSON for now)
        data = json.loads(payload.thought_proto.decode())
        return core.Thought(**data)
    except Exception as e:
        print(f"Failed to parse thought: {e}")
        return None


# ============================================================================
# SERVICE IMPLEMENTATION
# ============================================================================

class WotPeerService(pb_grpc.WotPeerServicer):
    """gRPC service handler for WoT peer protocol."""

    def __init__(self, identity: core.Identity, pool_cid: Optional[str] = None):
        self.identity = identity
        self.pool_cid = pool_cid
        self.session_counter = 0
        self.peers = {}  # session_id -> peer info

    def Hello(self, request: pb.HelloRequest, context) -> pb.HelloResponse:
        """Handle peer handshake."""
        self.session_counter += 1
        session_id = f"session-{self.session_counter}-{int(time.time())}"

        # Accept all capabilities for now
        accepted = list(request.capabilities) or ["sync", "push", "query"]

        # Sign response (simplified - just identity CID)
        sig = core.sign_content(session_id, self.identity)

        self.peers[session_id] = {
            "identity_cid": request.identity_cid.hex(),
            "capabilities": accepted,
            "connected_at": time.time()
        }

        print(f"[Hello] New peer: {request.identity_cid.hex()[:16]}... → session {session_id}")

        return pb.HelloResponse(
            identity_cid=self.identity.cid.encode(),
            accepted_capabilities=accepted,
            session_id=session_id,
            signature=bytes.fromhex(sig)
        )

    def GetSchemas(self, request: pb.SchemaRequest, context) -> pb.SchemaResponse:
        """Return required schemas for pool."""
        # Minimal implementation - no schema enforcement yet
        return pb.SchemaResponse(
            pool_rules_cid=b'',
            required=[],
            rate_limits=pb.RateLimits(
                thoughts_per_minute=100,
                bytes_per_minute=1_000_000,
                max_payload_bytes=65536
            ),
            timestamp_unit="ms"
        )

    def ExchangeBloom(self, request: pb.BloomRequest, context) -> pb.BloomResponse:
        """Exchange bloom filters for sync."""
        # Build our bloom filter
        thoughts = core.query_thoughts(limit=10000)
        bf = BloomFilter(m=request.filter_m or 95851, k=request.filter_k or 7)

        for t in thoughts:
            cid_bytes = core.compute_cid_bytes({
                "type": t.type,
                "content": t.content,
                "created_by": t.created_by,
                "created_at": t.created_at,
                "because": t.because,
            })
            bf.add(cid_bytes)

        print(f"[Bloom] Exchanged filter: {len(thoughts)} thoughts")

        return pb.BloomResponse(
            filter_bytes=bf.to_bytes(),
            filter_k=bf.k,
            filter_m=bf.m,
            thought_count=len(thoughts)
        )

    def Want(self, request: pb.WantRequest, context) -> Iterator[pb.ThoughtPayload]:
        """Stream requested thoughts to peer."""
        print(f"[Want] Peer wants {len(request.cids)} thoughts")

        for cid_bytes in request.cids:
            # Convert bytes to string CID
            cid_hex = cid_bytes[4:].hex()  # Strip header
            cid_str = f"cid:blake3:{cid_hex}"

            thought = core.get_thought(cid_str)
            if thought:
                yield thought_to_payload(thought)

    def Push(self, request_iterator, context) -> Iterator[pb.ThoughtAck]:
        """Receive thoughts from peer."""
        rag = get_rag()

        for payload in request_iterator:
            thought = payload_to_thought(payload)

            if thought is None:
                yield pb.ThoughtAck(
                    cid=payload.cid,
                    status=pb.ACK_REJECTED,
                    message="Failed to parse or verify"
                )
                continue

            # Store thought
            try:
                core.store_thought(thought)

                # Index in RAG if available
                if rag:
                    rag.pipeline.embed_thought(thought, self.pool_cid)

                print(f"[Push] Received: {thought.cid[:40]}... [{thought.type}]")

                yield pb.ThoughtAck(
                    cid=payload.cid,
                    status=pb.ACK_ACCEPTED,
                    message="Stored"
                )
            except Exception as e:
                yield pb.ThoughtAck(
                    cid=payload.cid,
                    status=pb.ACK_REJECTED,
                    message=str(e)
                )

    def Query(self, request: pb.QueryRequest, context) -> pb.QueryResponse:
        """Semantic search via RAG with pool waterline filtering."""
        rag = get_rag()

        if not rag:
            return pb.QueryResponse(results=[])

        pool_cid = request.pool_cid.decode() if request.pool_cid else self.pool_cid

        try:
            # Fetch more than requested to account for waterline filtering
            results = rag.retrieve(
                query=request.query_text,
                top_k=(request.top_k or 10) * 3,
                pool_cid=pool_cid,
                include_thoughts=True
            )

            # Apply pool waterline filtering
            filtered = pool_mgmt.filter_by_waterline(results, pool_cid)

            # Limit to requested top_k
            filtered = filtered[:request.top_k or 10]

            pb_results = []
            for r in filtered:
                result = pb.QueryResult(
                    cid=r['cid'].encode() if isinstance(r['cid'], str) else r['cid'],
                    similarity=r.get('relevance', r.get('similarity', 0.0)),
                    snippet=r.get('snippet', '')[:200]
                )
                pb_results.append(result)

            # Log with waterline info
            pool = pool_mgmt.get_pool(pool_cid) if pool_cid else None
            waterline = pool.rules.waterline if pool else 0.3
            print(f"[Query] '{request.query_text[:30]}...' → {len(results)} raw, {len(filtered)} above waterline ({waterline})")

            return pb.QueryResponse(results=pb_results)

        except Exception as e:
            print(f"[Query] Error: {e}")
            return pb.QueryResponse(results=[])

    def Heartbeat(self, request: pb.HeartbeatRequest, context) -> pb.HeartbeatResponse:
        """Health check."""
        thoughts = core.query_thoughts(limit=1)
        thought_count = len(core.query_thoughts(limit=10000))

        return pb.HeartbeatResponse(
            timestamp=int(time.time() * 1000),
            thought_count=thought_count,
            sync_needed=request.thought_count != thought_count
        )


# ============================================================================
# CLIENT
# ============================================================================

class WotPeerClient:
    """Client for connecting to remote WoT peer."""

    def __init__(self, address: str, identity: core.Identity):
        self.address = address
        self.identity = identity
        self.channel = grpc.insecure_channel(address)
        self.stub = pb_grpc.WotPeerStub(self.channel)
        self.session_id = None

    def connect(self) -> bool:
        """Perform handshake with peer."""
        try:
            sig = core.sign_content(self.identity.cid, self.identity)

            response = self.stub.Hello(pb.HelloRequest(
                identity_cid=self.identity.cid.encode(),
                protocol_version=0x0001,
                capabilities=["sync", "push", "query"],
                timestamp=int(time.time() * 1000),
                signature=bytes.fromhex(sig)
            ))

            self.session_id = response.session_id
            print(f"Connected to {self.address}: session={self.session_id}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def push_thoughts(self, thoughts: List[core.Thought]) -> List[pb.ThoughtAck]:
        """Push thoughts to peer."""
        def thought_stream():
            for t in thoughts:
                yield thought_to_payload(t)

        acks = list(self.stub.Push(thought_stream()))
        return acks

    def query(self, query_text: str, top_k: int = 10) -> List[dict]:
        """Query peer's thought index."""
        response = self.stub.Query(pb.QueryRequest(
            query_text=query_text,
            top_k=top_k
        ))

        results = []
        for r in response.results:
            results.append({
                'cid': r.cid.decode() if isinstance(r.cid, bytes) else r.cid,
                'similarity': r.similarity,
                'snippet': r.snippet
            })
        return results

    def sync(self) -> int:
        """Sync thoughts with peer using bloom filter exchange."""
        # Build our bloom
        thoughts = core.query_thoughts(limit=10000)
        bf = BloomFilter()
        our_cids = set()

        for t in thoughts:
            cid_bytes = core.compute_cid_bytes({
                "type": t.type,
                "content": t.content,
                "created_by": t.created_by,
                "created_at": t.created_at,
                "because": t.because,
            })
            bf.add(cid_bytes)
            our_cids.add(cid_bytes)

        # Exchange blooms
        response = self.stub.ExchangeBloom(pb.BloomRequest(
            filter_bytes=bf.to_bytes(),
            filter_k=bf.k,
            filter_m=bf.m,
            thought_count=len(thoughts)
        ))

        their_bloom = BloomFilter.from_bytes(
            response.filter_bytes,
            response.filter_m,
            response.filter_k
        )

        # Find what they have that we don't
        # (This is approximate due to bloom filter false positives)
        # For now, request all if counts differ
        if response.thought_count > len(thoughts):
            print(f"Peer has {response.thought_count - len(thoughts)} more thoughts")

        return response.thought_count

    def close(self):
        """Close connection."""
        self.channel.close()
