#!/usr/bin/env python3
"""
Dogfood 021: Visibility-Aware Sync
Wellspring node with pool-based visibility filtering and sync provenance tracking.
"""

import json
import hashlib
import asyncio
import argparse
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import base64
import mmh3  # MurmurHash for bloom filter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# ============================================================================
# CRYPTO UTILITIES
# ============================================================================

def pubkey_to_hex(pubkey: Ed25519PublicKey) -> str:
    return pubkey.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    ).hex()

def hex_to_pubkey(hex_str: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_str))

def compute_cid(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    hash_bytes = hashlib.sha256(canonical.encode()).hexdigest()
    return f"baf_{hash_bytes[:32]}"

# ============================================================================
# BLOOM FILTER
# ============================================================================

class BloomFilter:
    def __init__(self, size: int = 1024, hash_count: int = 3):
        self.size = size
        self.hash_count = hash_count
        self.bits = [0] * size

    def add(self, item: str):
        for i in range(self.hash_count):
            idx = mmh3.hash(item, i) % self.size
            self.bits[idx] = 1

    def maybe_contains(self, item: str) -> bool:
        for i in range(self.hash_count):
            idx = mmh3.hash(item, i) % self.size
            if self.bits[idx] == 0:
                return False
        return True

    def to_hex(self) -> str:
        byte_arr = []
        for i in range(0, len(self.bits), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(self.bits):
                    byte_val |= (self.bits[i + j] << j)
            byte_arr.append(byte_val)
        return bytes(byte_arr).hex()

    @classmethod
    def from_hex(cls, hex_str: str, size: int = 1024, hash_count: int = 3):
        bf = cls(size, hash_count)
        byte_arr = bytes.fromhex(hex_str)
        bf.bits = []
        for byte_val in byte_arr:
            for j in range(8):
                bf.bits.append((byte_val >> j) & 1)
        bf.bits = bf.bits[:size]
        return bf

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

    @classmethod
    def from_dict(cls, d: dict) -> 'SignedThought':
        t = cls(
            type=d["type"],
            content=d["content"],
            created_by=d["created_by"],
            because=d.get("because", []),
            visibility=d.get("visibility"),
            created_at=d["created_at"],
            signature=d["signature"]
        )
        t.cid = d["cid"]
        return t

# ============================================================================
# WELLSPRING NODE V2 - with visibility filtering
# ============================================================================

class WellspringNodeV2:
    def __init__(self, name: str, port: int):
        self.name = name
        self.port = port
        self.peers: List[str] = []  # URLs of peer nodes

        # Identity
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.pubkey_hex = pubkey_to_hex(self.public_key)

        self.identity_thought = SignedThought(
            type="identity",
            content={"name": name, "pubkey": self.pubkey_hex, "endpoint": f"http://localhost:{port}"},
            created_by="GENESIS"
        )
        self.identity_thought.sign(self.private_key)
        self.cid = self.identity_thought.cid

        # Storage
        self.thoughts: Dict[str, dict] = {self.cid: self.identity_thought.to_dict()}
        self.pubkeys: Dict[str, str] = {self.cid: self.pubkey_hex}
        self.bloom = BloomFilter()
        self.bloom.add(self.cid)

        # === NEW: Pool and peer relationship tracking ===

        # Pool memberships: pool_cid -> set of member identity CIDs
        self.pool_memberships: Dict[str, Set[str]] = {}

        # Peer shared pools: peer_cid -> set of pool_cids we share with them
        # This is the peering agreement - what pools we sync with this peer
        self.peer_shared_pools: Dict[str, Set[str]] = {}

        # Known peer identities: peer_cid -> identity dict
        self.known_peers: Dict[str, dict] = {}

        # Sync provenance (local_forever): thought_cid -> received_via peer_cid
        # These are stored as actual thoughts with visibility: local_forever
        self.received_via: Dict[str, str] = {}

        # Stats
        self.received_count = 0
        self.sent_count = 0
        self.verified_count = 0
        self.rejected_count = 0
        self.filtered_count = 0  # Thoughts not synced due to visibility

    # ========================================================================
    # POOL MANAGEMENT
    # ========================================================================

    def create_pool(self, name: str, visibility: str = "members_only",
                    access: str = "invite") -> SignedThought:
        """Create a pool thought."""
        thought = SignedThought(
            type="pool",
            content={
                "name": name,
                "visibility": visibility,
                "access": access,
                "admin": self.cid
            },
            created_by=self.cid,
            because=[self.cid]
        )
        thought.sign(self.private_key)
        self._store_thought(thought.to_dict())

        # Auto-add self as member
        self.pool_memberships[thought.cid] = {self.cid}

        return thought

    def add_pool_member(self, pool_cid: str, member_cid: str):
        """Add a member to a pool we admin."""
        if pool_cid not in self.pool_memberships:
            self.pool_memberships[pool_cid] = set()
        self.pool_memberships[pool_cid].add(member_cid)

    def is_pool_member(self, pool_cid: str, identity_cid: str) -> bool:
        """Check if an identity is a member of a pool."""
        return identity_cid in self.pool_memberships.get(pool_cid, set())

    # ========================================================================
    # PEER RELATIONSHIP MANAGEMENT
    # ========================================================================

    def register_peer(self, peer_identity: dict):
        """Register a peer's identity."""
        peer_cid = peer_identity["cid"]
        self.known_peers[peer_cid] = peer_identity

        # Store pubkey for verification
        if peer_identity["type"] == "identity":
            self.pubkeys[peer_cid] = peer_identity["content"]["pubkey"]

    def establish_peering(self, peer_cid: str, shared_pools: List[str]):
        """
        Establish what pools we share with a peer.
        This is the peering agreement - what we'll sync.
        """
        if peer_cid not in self.peer_shared_pools:
            self.peer_shared_pools[peer_cid] = set()
        self.peer_shared_pools[peer_cid].update(shared_pools)

    def get_shared_pools(self, peer_cid: str) -> Set[str]:
        """Get pools shared with a specific peer."""
        return self.peer_shared_pools.get(peer_cid, set())

    # ========================================================================
    # VISIBILITY FILTERING
    # ========================================================================

    def _can_share_with_peer(self, thought: dict, peer_cid: str) -> Tuple[bool, str]:
        """
        Determine if a thought can be shared with a specific peer.
        Returns (can_share, reason).

        Visibility rules:
        - None/absent: public, share with everyone
        - "local_forever": never share
        - "pool:<cid>": share if peer has access to that pool
        - "public": share with everyone
        - "participants_only": check content.participants list
        """
        visibility = thought.get("visibility")

        # No visibility = public
        if visibility is None:
            return True, "public"

        # Explicit public
        if visibility == "public":
            return True, "public"

        # Never share local_forever
        if visibility == "local_forever":
            return False, "local_forever"

        # Pool-scoped visibility
        if visibility.startswith("pool:"):
            pool_cid = visibility[5:]  # Remove "pool:" prefix

            # Check if peer is a member of this pool
            if self.is_pool_member(pool_cid, peer_cid):
                return True, f"peer_is_member:{pool_cid}"

            # Check if we have a peering agreement for this pool
            if pool_cid in self.get_shared_pools(peer_cid):
                return True, f"shared_pool:{pool_cid}"

            return False, f"no_pool_access:{pool_cid}"

        # Participants-only: check if peer is in participants list
        if visibility == "participants_only":
            participants = thought.get("content", {}).get("participants", [])
            # Check by name or CID
            peer_name = self.known_peers.get(peer_cid, {}).get("content", {}).get("name")
            if peer_cid in participants or peer_name in participants:
                return True, "is_participant"
            return False, "not_participant"

        # Unknown visibility type - default to not sharing (safe)
        return False, f"unknown_visibility:{visibility}"

    # ========================================================================
    # THOUGHT MANAGEMENT
    # ========================================================================

    def add_peer(self, url: str):
        if url not in self.peers:
            self.peers.append(url)

    def create_thought(self, type: str, content: dict, because: List[str] = None,
                       visibility: str = None) -> SignedThought:
        thought = SignedThought(
            type=type,
            content=content,
            created_by=self.cid,
            because=because or [],
            visibility=visibility
        )
        thought.sign(self.private_key)
        self._store_thought(thought.to_dict())
        return thought

    def _store_thought(self, thought: dict) -> bool:
        """Store a thought if valid. Returns True if new."""
        cid = thought["cid"]
        if cid in self.thoughts:
            return False

        # Verify signature
        if not self._verify_signature(thought):
            self.rejected_count += 1
            return False

        self.thoughts[cid] = thought
        self.bloom.add(cid)
        self.verified_count += 1

        # Track identity pubkeys
        if thought["type"] == "identity" and thought["created_by"] == "GENESIS":
            self.pubkeys[cid] = thought["content"]["pubkey"]

        # Track pool memberships from attestations
        self._process_pool_membership(thought)

        return True

    def _process_pool_membership(self, thought: dict):
        """Extract pool membership info from attestation thoughts."""
        if thought["type"] != "attestation":
            return

        content = thought.get("content", {})

        # Look for membership attestations
        if content.get("aspect_type") == "membership":
            pool_cid = content.get("pool")
            member_cid = content.get("member") or thought.get("created_by")
            if pool_cid and member_cid:
                if pool_cid not in self.pool_memberships:
                    self.pool_memberships[pool_cid] = set()
                self.pool_memberships[pool_cid].add(member_cid)

    def _verify_signature(self, thought: dict) -> bool:
        created_by = thought["created_by"]

        if thought["type"] == "identity" and created_by == "GENESIS":
            pubkey_hex = thought["content"]["pubkey"]
        elif created_by in self.pubkeys:
            pubkey_hex = self.pubkeys[created_by]
        else:
            return False

        try:
            pubkey = hex_to_pubkey(pubkey_hex)
            sign_data = {
                "type": thought["type"],
                "content": thought["content"],
                "created_by": thought["created_by"],
                "because": thought["because"],
                "created_at": thought["created_at"]
            }
            if "visibility" in thought and thought["visibility"]:
                sign_data["visibility"] = thought["visibility"]

            message = json.dumps(sign_data, sort_keys=True, separators=(',', ':')).encode()
            sig_bytes = base64.b64decode(thought["signature"])
            pubkey.verify(sig_bytes, message)
            return True
        except:
            return False

    def get_bloom_hex(self) -> str:
        return self.bloom.to_hex()

    # ========================================================================
    # SYNC WITH VISIBILITY FILTERING
    # ========================================================================

    def get_missing_for_peer(self, peer_bloom_hex: str, peer_cid: str) -> Tuple[List[dict], dict]:
        """
        Return thoughts we have that peer probably doesn't, FILTERED by visibility.
        Returns (thoughts, stats).
        """
        peer_bloom = BloomFilter.from_hex(peer_bloom_hex)

        stats = {
            "total_checked": 0,
            "missing": 0,
            "filtered_local_forever": 0,
            "filtered_pool_access": 0,
            "filtered_participants": 0,
            "shared": 0
        }

        # First pass: find thoughts peer is missing
        missing_cids = set()
        for cid in self.thoughts:
            stats["total_checked"] += 1
            if not peer_bloom.maybe_contains(cid):
                missing_cids.add(cid)
                stats["missing"] += 1

        # Second pass: filter by visibility
        shareable_cids = set()
        for cid in missing_cids:
            thought = self.thoughts[cid]
            can_share, reason = self._can_share_with_peer(thought, peer_cid)

            if can_share:
                shareable_cids.add(cid)
            else:
                self.filtered_count += 1
                if "local_forever" in reason:
                    stats["filtered_local_forever"] += 1
                elif "pool_access" in reason:
                    stats["filtered_pool_access"] += 1
                elif "participant" in reason:
                    stats["filtered_participants"] += 1

        # Third pass: resolve identity dependencies for shareable thoughts
        needed_identities = set()
        for cid in shareable_cids:
            thought = self.thoughts[cid]
            created_by = thought["created_by"]
            if created_by != "GENESIS" and created_by in self.thoughts:
                if not peer_bloom.maybe_contains(created_by):
                    # Check if we can share this identity
                    identity_thought = self.thoughts[created_by]
                    can_share_id, _ = self._can_share_with_peer(identity_thought, peer_cid)
                    if can_share_id:
                        needed_identities.add(created_by)

        # Combine: identities first, then content
        result = []

        for cid in needed_identities:
            if cid not in shareable_cids:
                result.append(self.thoughts[cid])
                stats["shared"] += 1

        for cid in shareable_cids:
            result.append(self.thoughts[cid])
            stats["shared"] += 1

        return result, stats

    def receive_thoughts(self, thoughts: List[dict], sender_cid: str = None) -> dict:
        """Receive thoughts from peer. Returns stats."""
        # Sort: identities first
        sorted_thoughts = sorted(thoughts, key=lambda t: (
            0 if t["type"] == "identity" else 1,
            t.get("created_at", "")
        ))

        new_count = 0
        deferred = []

        for thought in sorted_thoughts:
            if self._store_thought(thought):
                new_count += 1
                self.received_count += 1

                # Record provenance (as local_forever thought)
                if sender_cid:
                    self._record_received_via(thought["cid"], sender_cid)

            elif thought["cid"] not in self.thoughts:
                deferred.append(thought)

        for thought in deferred:
            if self._store_thought(thought):
                new_count += 1
                self.received_count += 1
                if sender_cid:
                    self._record_received_via(thought["cid"], sender_cid)

        return {"received": len(thoughts), "new": new_count}

    def _record_received_via(self, thought_cid: str, sender_cid: str):
        """
        Record sync provenance as a local_forever connection thought.
        This is never synced - it's our local record of where we got this thought.
        """
        # Quick lookup cache
        self.received_via[thought_cid] = sender_cid

        # Create actual thought for full audit trail
        provenance = SignedThought(
            type="connection",
            content={
                "connection_type": "received_via",
                "thought": thought_cid,
                "via": sender_cid,
                "received_at": datetime.utcnow().isoformat()
            },
            created_by=self.cid,
            because=[thought_cid, sender_cid],
            visibility="local_forever"
        )
        provenance.sign(self.private_key)

        # Store without syncing (local_forever will prevent sync anyway)
        self.thoughts[provenance.cid] = provenance.to_dict()
        self.bloom.add(provenance.cid)

    def get_provenance(self, thought_cid: str) -> Optional[str]:
        """Get the peer we received a thought from."""
        return self.received_via.get(thought_cid)

    def stats(self) -> dict:
        return {
            "name": self.name,
            "cid": self.cid[:20] + "...",
            "thoughts": len(self.thoughts),
            "pools": len(self.pool_memberships),
            "peers": len(self.peers),
            "known_peer_identities": len(self.known_peers),
            "peer_agreements": len(self.peer_shared_pools),
            "received": self.received_count,
            "sent": self.sent_count,
            "verified": self.verified_count,
            "rejected": self.rejected_count,
            "filtered": self.filtered_count
        }

# ============================================================================
# API MODELS
# ============================================================================

class SyncRequest(BaseModel):
    bloom_hex: str
    sender_cid: str

class ThoughtsPayload(BaseModel):
    thoughts: List[dict]
    sender_cid: str

class CreateThoughtRequest(BaseModel):
    type: str
    content: dict
    because: List[str] = []
    visibility: Optional[str] = None

class PeeringRequest(BaseModel):
    peer_identity: dict
    shared_pools: List[str] = []

# ============================================================================
# CREATE APP
# ============================================================================

def create_app(node: WellspringNodeV2) -> FastAPI:
    app = FastAPI(title=f"Wellspring Node V2: {node.name}")

    @app.get("/")
    async def root():
        return node.stats()

    @app.get("/identity")
    async def get_identity():
        return node.identity_thought.to_dict()

    @app.get("/bloom")
    async def get_bloom():
        return {"bloom_hex": node.get_bloom_hex(), "thought_count": len(node.thoughts)}

    @app.post("/sync")
    async def sync(request: SyncRequest):
        """Receive peer's bloom, return thoughts they're missing (visibility-filtered)."""
        missing, stats = node.get_missing_for_peer(request.bloom_hex, request.sender_cid)
        node.sent_count += len(missing)
        return {"thoughts": missing, "count": len(missing), "filter_stats": stats}

    @app.post("/receive")
    async def receive(payload: ThoughtsPayload):
        """Receive thoughts from peer."""
        result = node.receive_thoughts(payload.thoughts, payload.sender_cid)
        return result

    @app.get("/thoughts")
    async def list_thoughts():
        return {"thoughts": list(node.thoughts.values()), "count": len(node.thoughts)}

    @app.get("/thoughts/{cid}")
    async def get_thought(cid: str):
        if cid in node.thoughts:
            return node.thoughts[cid]
        raise HTTPException(status_code=404, detail="Thought not found")

    @app.post("/thoughts")
    async def create_thought(request: CreateThoughtRequest):
        thought = node.create_thought(request.type, request.content, request.because, request.visibility)
        return thought.to_dict()

    @app.post("/pools")
    async def create_pool(name: str, visibility: str = "members_only"):
        pool = node.create_pool(name, visibility)
        return pool.to_dict()

    @app.post("/pools/{pool_cid}/members")
    async def add_member(pool_cid: str, member_cid: str):
        node.add_pool_member(pool_cid, member_cid)
        return {"pool": pool_cid, "members": list(node.pool_memberships.get(pool_cid, []))}

    @app.get("/pools/{pool_cid}/members")
    async def list_members(pool_cid: str):
        return {"pool": pool_cid, "members": list(node.pool_memberships.get(pool_cid, []))}

    @app.post("/peering")
    async def establish_peering(request: PeeringRequest):
        """Establish peering agreement with another node."""
        node.register_peer(request.peer_identity)
        peer_cid = request.peer_identity["cid"]
        node.establish_peering(peer_cid, request.shared_pools)
        return {
            "peer": peer_cid,
            "shared_pools": list(node.get_shared_pools(peer_cid))
        }

    @app.get("/peering/{peer_cid}")
    async def get_peering(peer_cid: str):
        return {
            "peer": peer_cid,
            "shared_pools": list(node.get_shared_pools(peer_cid)),
            "known": peer_cid in node.known_peers
        }

    @app.get("/provenance/{thought_cid}")
    async def get_provenance(thought_cid: str):
        via = node.get_provenance(thought_cid)
        return {"thought": thought_cid, "received_via": via}

    @app.post("/peers")
    async def add_peer(url: str):
        node.add_peer(url)
        return {"peers": node.peers}

    @app.get("/peers")
    async def list_peers():
        return {"peers": node.peers}

    return app

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Wellspring Node V2")
    parser.add_argument("--name", required=True, help="Node name")
    parser.add_argument("--port", type=int, required=True, help="HTTP port")
    args = parser.parse_args()

    node = WellspringNodeV2(args.name, args.port)
    app = create_app(node)

    print(f"Starting Wellspring node V2: {node.name}")
    print(f"Identity CID: {node.cid}")
    print(f"Endpoint: http://localhost:{args.port}")

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")

if __name__ == "__main__":
    main()
