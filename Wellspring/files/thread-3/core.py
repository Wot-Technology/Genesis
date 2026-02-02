"""
Wellspring Core - Thread 3 local copy with fixed paths.

Provides the minimal primitives needed to create, sign, store,
and retrieve thoughts.
"""

import json
import time
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder
import blake3

# ============================================================================
# CONFIGURATION - Relative paths for portability
# ============================================================================

_THIS_DIR = Path(__file__).parent.resolve()
_COWORK_SESSION = Path("/sessions/magical-exciting-newton")

if _COWORK_SESSION.exists():
    # Running in Cowork VM
    SESSION_DIR = _COWORK_SESSION
    WORKSPACE_DIR = SESSION_DIR / "mnt" / "Wellspring Eternal" / "files"
    DB_PATH = SESSION_DIR / "wellspring.db"
else:
    # Running locally - use relative paths
    WORKSPACE_DIR = _THIS_DIR.parent  # files/
    DB_PATH = _THIS_DIR / "wellspring.db"

JSONL_PATH = WORKSPACE_DIR / "thoughts.jsonl"


# ============================================================================
# IDENTITY
# ============================================================================

@dataclass
class Identity:
    """Ed25519 identity for signing thoughts."""
    name: str
    pubkey: str  # hex-encoded
    cid: str
    _privkey: Optional[str] = None  # hex-encoded, local_forever


def create_identity(name: str) -> Identity:
    """Generate new ed25519 identity."""
    signing_key = SigningKey.generate()
    privkey_hex = signing_key.encode(encoder=HexEncoder).decode()
    pubkey_hex = signing_key.verify_key.encode(encoder=HexEncoder).decode()

    identity_content = {
        "type": "identity",
        "name": name,
        "pubkey": f"ed25519:{pubkey_hex}"
    }
    cid = compute_cid(identity_content)

    return Identity(
        name=name,
        pubkey=f"ed25519:{pubkey_hex}",
        cid=cid,
        _privkey=privkey_hex
    )


def load_identity(path: Path) -> Identity:
    """Load identity from JSON file."""
    with open(path) as f:
        data = json.load(f)
    return Identity(**data)


def save_identity(identity: Identity, path: Path):
    """Save identity to JSON file (includes private key!)."""
    with open(path, 'w') as f:
        json.dump(asdict(identity), f, indent=2)


# ============================================================================
# CID COMPUTATION - IPFS Compatible
# ============================================================================
#
# CIDv1 format: multibase + version + codec + multihash
# We use: base32 + cidv1 (0x01) + dag-cbor (0x71) + blake3-256 (0x1e) + digest
# Simplified: "cid:blake3:<hex>" for readability, full multiformat for wire

def canonicalize(obj: Any) -> str:
    """Canonical JSON serialization for CID computation."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'))


def compute_cid(content: Any) -> str:
    """
    Compute IPFS-compatible content identifier using blake3.
    Returns human-readable format. Use compute_cid_bytes() for wire format.
    """
    canonical = canonicalize(content)
    digest = blake3.blake3(canonical.encode()).hexdigest()
    return f"cid:blake3:{digest}"


def compute_cid_bytes(content: Any) -> bytes:
    """
    Compute full IPFS-compatible CID as bytes (36 bytes).
    Format: CIDv1 (0x01) + dag-cbor (0x71) + blake3-256 (0x1e) + 32-byte digest
    """
    canonical = canonicalize(content)
    digest = blake3.blake3(canonical.encode()).digest()  # 32 bytes
    # CIDv1 multiformat header
    header = bytes([0x01, 0x71, 0x1e, 0x20])  # version, codec, hash-type, hash-len
    return header + digest


# ============================================================================
# THOUGHT CREATION
# ============================================================================

@dataclass
class Thought:
    """The one primitive. Everything is a thought."""
    cid: str
    type: str
    content: Any
    created_by: str  # identity CID
    created_at: int  # unix timestamp ms
    because: List[str]  # list of thought CIDs
    signature: str
    visibility: Optional[str] = None
    source: Optional[str] = None


def create_thought(
    content: Any,
    thought_type: str,
    identity: Identity,
    because: Optional[List[str]] = None,
    visibility: Optional[str] = None,
    source: Optional[str] = None
) -> Thought:
    """Create and sign a new thought."""
    if because is None:
        because = []

    created_at = int(time.time() * 1000)

    signable = {
        "type": thought_type,
        "content": content,
        "created_by": identity.cid,
        "created_at": created_at,
        "because": because,
    }
    if visibility:
        signable["visibility"] = visibility
    if source:
        signable["source"] = source

    cid = compute_cid(signable)
    signature = sign_content(cid, identity)

    return Thought(
        cid=cid,
        type=thought_type,
        content=content,
        created_by=identity.cid,
        created_at=created_at,
        because=because,
        signature=signature,
        visibility=visibility,
        source=source
    )


def sign_content(cid: str, identity: Identity) -> str:
    """Sign a CID with identity's private key."""
    if not identity._privkey:
        raise ValueError("Cannot sign without private key")

    signing_key = SigningKey(identity._privkey, encoder=HexEncoder)
    signed = signing_key.sign(cid.encode())
    return signed.signature.hex()


def verify_signature(thought: Thought, pubkey: str) -> bool:
    """Verify thought signature against pubkey."""
    try:
        key_hex = pubkey.replace("ed25519:", "")
        verify_key = VerifyKey(key_hex, encoder=HexEncoder)
        verify_key.verify(thought.cid.encode(), bytes.fromhex(thought.signature))
        return True
    except Exception:
        return False


# ============================================================================
# STORAGE
# ============================================================================

def init_db(db_path: Path = DB_PATH):
    """Initialize SQLite database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS thoughts (
            cid TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            because TEXT NOT NULL,
            signature TEXT NOT NULL,
            visibility TEXT,
            source TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON thoughts(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_created_by ON thoughts(created_by)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON thoughts(created_at)")
    conn.commit()
    conn.close()


def store_thought(thought: Thought, db_path: Path = DB_PATH):
    """Store thought in SQLite and append to JSONL."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT OR REPLACE INTO thoughts
        (cid, type, content, created_by, created_at, because, signature, visibility, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        thought.cid,
        thought.type,
        json.dumps(thought.content),
        thought.created_by,
        thought.created_at,
        json.dumps(thought.because),
        thought.signature,
        thought.visibility,
        thought.source
    ))
    conn.commit()
    conn.close()

    # Also append to JSONL
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSONL_PATH, 'a') as f:
        f.write(json.dumps(asdict(thought)) + '\n')


def get_thought(cid: str, db_path: Path = DB_PATH) -> Optional[Thought]:
    """Retrieve thought by CID."""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT * FROM thoughts WHERE cid = ?", (cid,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    return Thought(
        cid=row[0],
        type=row[1],
        content=json.loads(row[2]),
        created_by=row[3],
        created_at=row[4],
        because=json.loads(row[5]),
        signature=row[6],
        visibility=row[7],
        source=row[8]
    )


def query_thoughts(
    thought_type: Optional[str] = None,
    created_by: Optional[str] = None,
    limit: int = 100,
    db_path: Path = DB_PATH
) -> List[Thought]:
    """Query thoughts with optional filters."""
    conn = sqlite3.connect(db_path)

    query = "SELECT * FROM thoughts WHERE 1=1"
    params = []

    if thought_type:
        query += " AND type = ?"
        params.append(thought_type)

    if created_by:
        query += " AND created_by = ?"
        params.append(created_by)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    return [
        Thought(
            cid=row[0],
            type=row[1],
            content=json.loads(row[2]),
            created_by=row[3],
            created_at=row[4],
            because=json.loads(row[5]),
            signature=row[6],
            visibility=row[7],
            source=row[8]
        )
        for row in rows
    ]


# ============================================================================
# HELPERS
# ============================================================================

def create_connection(
    from_cid: str,
    to_cid: str,
    relation: str,
    identity: Identity,
    because: Optional[List[str]] = None
) -> Thought:
    """Create a connection thought between two thoughts."""
    content = {
        "from": from_cid,
        "to": to_cid,
        "relation": relation
    }
    return create_thought(
        content=content,
        thought_type="connection",
        identity=identity,
        because=because or [from_cid, to_cid]
    )


def create_attestation(
    about_cid: str,
    weight: float,
    identity: Identity,
    because: Optional[List[str]] = None,
    note: Optional[str] = None
) -> Thought:
    """Create an attestation thought about another thought."""
    content = {
        "about": about_cid,
        "weight": weight
    }
    if note:
        content["note"] = note

    return create_thought(
        content=content,
        thought_type="attestation",
        identity=identity,
        because=because or [about_cid]
    )


# Initialize DB when imported
init_db()
