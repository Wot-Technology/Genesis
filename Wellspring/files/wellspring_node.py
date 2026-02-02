#!/usr/bin/env python3
"""
Dogfood 016: Multi-Instance Sync
Wellspring node with HTTP endpoints for distributed sync.
"""

import json
import hashlib
import asyncio
import argparse
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
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
# BLOOM FILTER (simple implementation)
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
        # Pack bits into bytes
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
# WELLSPRING NODE
# ============================================================================

class WellspringNode:
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

        # Stats
        self.received_count = 0
        self.sent_count = 0
        self.verified_count = 0
        self.rejected_count = 0

    def add_peer(self, url: str):
        if url not in self.peers:
            self.peers.append(url)

    def create_thought(self, type: str, content: dict, because: List[str] = None) -> SignedThought:
        thought = SignedThought(
            type=type,
            content=content,
            created_by=self.cid,
            because=because or []
        )
        thought.sign(self.private_key)
        self._store_thought(thought.to_dict())
        return thought

    def _store_thought(self, thought: dict) -> bool:
        """Store a thought if valid. Returns True if new."""
        cid = thought["cid"]
        if cid in self.thoughts:
            return False  # Already have it

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

        return True

    def _verify_signature(self, thought: dict) -> bool:
        created_by = thought["created_by"]

        if thought["type"] == "identity" and created_by == "GENESIS":
            pubkey_hex = thought["content"]["pubkey"]
        elif created_by in self.pubkeys:
            pubkey_hex = self.pubkeys[created_by]
        else:
            return False  # Unknown identity

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

    def get_missing_for_peer(self, peer_bloom_hex: str) -> List[dict]:
        """Return thoughts we have that peer probably doesn't, with dependencies."""
        peer_bloom = BloomFilter.from_hex(peer_bloom_hex)

        # First pass: find thoughts peer is missing
        missing_cids = set()
        for cid in self.thoughts:
            if not peer_bloom.maybe_contains(cid):
                missing_cids.add(cid)

        # Second pass: resolve identity dependencies
        # For each missing thought, ensure we include the identity that signed it
        needed_identities = set()
        for cid in missing_cids:
            thought = self.thoughts[cid]
            created_by = thought["created_by"]
            # If created_by is an identity CID (not GENESIS), we need that identity
            if created_by != "GENESIS" and created_by in self.thoughts:
                # Check if peer probably doesn't have this identity
                if not peer_bloom.maybe_contains(created_by):
                    needed_identities.add(created_by)

        # Combine: identities first (so receiver can verify), then content
        result = []

        # Add identities first (order matters for verification)
        for cid in needed_identities:
            if cid not in missing_cids:  # Don't double-add
                result.append(self.thoughts[cid])

        # Add missing thoughts (identities that were already in missing_cids come naturally)
        for cid in missing_cids:
            result.append(self.thoughts[cid])

        return result

    def receive_thoughts(self, thoughts: List[dict]) -> dict:
        """Receive thoughts from peer. Returns stats."""
        # Sort: identities first (need pubkeys before we can verify content)
        sorted_thoughts = sorted(thoughts, key=lambda t: (
            0 if t["type"] == "identity" else 1,
            t.get("created_at", "")
        ))

        new_count = 0
        deferred = []  # Thoughts we couldn't verify yet (missing identity)

        # First pass: process what we can
        for thought in sorted_thoughts:
            if self._store_thought(thought):
                new_count += 1
                self.received_count += 1
            elif thought["cid"] not in self.thoughts:
                # Couldn't verify - might need identity we haven't seen yet
                deferred.append(thought)

        # Second pass: retry deferred (in case identity came later in batch)
        for thought in deferred:
            if self._store_thought(thought):
                new_count += 1
                self.received_count += 1

        return {"received": len(thoughts), "new": new_count}

    def stats(self) -> dict:
        return {
            "name": self.name,
            "cid": self.cid[:20] + "...",
            "thoughts": len(self.thoughts),
            "peers": len(self.peers),
            "received": self.received_count,
            "sent": self.sent_count,
            "verified": self.verified_count,
            "rejected": self.rejected_count
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

# ============================================================================
# CREATE APP
# ============================================================================

def create_app(node: WellspringNode) -> FastAPI:
    app = FastAPI(title=f"Wellspring Node: {node.name}")

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
        """Receive peer's bloom, return thoughts they're missing."""
        # Learn about sender if new
        missing = node.get_missing_for_peer(request.bloom_hex)
        node.sent_count += len(missing)
        return {"thoughts": missing, "count": len(missing)}

    @app.post("/receive")
    async def receive(payload: ThoughtsPayload):
        """Receive thoughts from peer."""
        result = node.receive_thoughts(payload.thoughts)
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
        thought = node.create_thought(request.type, request.content, request.because)
        return thought.to_dict()

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
    parser = argparse.ArgumentParser(description="Wellspring Node")
    parser.add_argument("--name", required=True, help="Node name")
    parser.add_argument("--port", type=int, required=True, help="HTTP port")
    args = parser.parse_args()

    node = WellspringNode(args.name, args.port)
    app = create_app(node)

    print(f"Starting Wellspring node: {node.name}")
    print(f"Identity CID: {node.cid}")
    print(f"Endpoint: http://localhost:{args.port}")

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")

if __name__ == "__main__":
    main()
