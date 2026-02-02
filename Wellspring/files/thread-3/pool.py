"""
Pool Management for WoT Thread 3

Handles pool creation, rules, and waterline-based filtering.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

import core

# ============================================================================
# POOL SCHEMA
# ============================================================================

@dataclass
class PoolRules:
    """Rules governing a pool's behavior."""
    waterline: float = 0.5          # Minimum relevance score to surface (0.0-1.0)
    accept_schemas: List[str] = None  # Allowed thought types (None = all)
    require_because: bool = True    # Require because chain
    max_payload_bytes: int = 65536  # Max thought size
    timestamp_unit: str = "ms"      # Timestamp precision
    auto_annotate: List[str] = None  # Auto-generate annotations
    trust_decay: float = 0.0001     # Per-hour trust decay for old thoughts

    def __post_init__(self):
        if self.accept_schemas is None:
            self.accept_schemas = []
        if self.auto_annotate is None:
            self.auto_annotate = []


@dataclass
class Pool:
    """Pool thought with rules."""
    cid: str
    name: str
    rules: PoolRules
    admin_cid: str  # Identity CID of admin
    visibility: str = "private"  # private, public, invite_only
    description: Optional[str] = None


# ============================================================================
# POOL STORAGE
# ============================================================================

_pools: Dict[str, Pool] = {}
DEFAULT_POOL_CID = "pool:default"


def create_pool(
    name: str,
    identity: core.Identity,
    rules: Optional[PoolRules] = None,
    visibility: str = "private",
    description: Optional[str] = None
) -> Pool:
    """Create a new pool and store as thought."""
    if rules is None:
        rules = PoolRules()

    content = {
        "name": name,
        "visibility": visibility,
        "admin": identity.cid,
        "rules": asdict(rules)
    }
    if description:
        content["description"] = description

    thought = core.create_thought(
        content=content,
        thought_type="pool",
        identity=identity,
        source="pool/create"
    )
    core.store_thought(thought)

    pool = Pool(
        cid=thought.cid,
        name=name,
        rules=rules,
        admin_cid=identity.cid,
        visibility=visibility,
        description=description
    )

    _pools[thought.cid] = pool
    return pool


def get_pool(cid: str) -> Optional[Pool]:
    """Get pool by CID."""
    # Check cache
    if cid in _pools:
        return _pools[cid]

    # Load from thought storage
    thought = core.get_thought(cid)
    if not thought or thought.type != "pool":
        return None

    content = thought.content
    rules_data = content.get("rules", {})
    rules = PoolRules(**rules_data)

    pool = Pool(
        cid=cid,
        name=content.get("name", "unnamed"),
        rules=rules,
        admin_cid=content.get("admin", ""),
        visibility=content.get("visibility", "private"),
        description=content.get("description")
    )

    _pools[cid] = pool
    return pool


def get_default_pool(identity: core.Identity) -> Pool:
    """Get or create the default test pool."""
    # Check if default pool exists
    if DEFAULT_POOL_CID in _pools:
        return _pools[DEFAULT_POOL_CID]

    # Try to load existing default pool (check both "wot" and legacy "default" names)
    thoughts = core.query_thoughts(thought_type="pool", limit=100)
    for t in thoughts:
        name = t.content.get("name", "")
        if name in ("wot", "default"):
            pool = get_pool(t.cid)
            if pool:
                return pool

    # Create default pool with sensible defaults
    pool = create_pool(
        name="wot",
        identity=identity,
        rules=PoolRules(
            waterline=0.3,  # Low threshold for testing
            require_because=False,  # Relaxed for testing
            accept_schemas=["basic", "insight", "question", "decision", "trace", "message"],
        ),
        visibility="private",
        description="WoT development traces and conversation"
    )

    print(f"Created wot pool: {pool.cid}")
    return pool


def list_pools() -> List[Pool]:
    """List all available pools."""
    # First return cached pools
    pools = list(_pools.values())
    cached_cids = set(_pools.keys())

    # Then load any from storage not yet cached
    thoughts = core.query_thoughts(thought_type="pool", limit=100)
    for t in thoughts:
        if t.cid not in cached_cids:
            pool = get_pool(t.cid)
            if pool:
                pools.append(pool)

    return pools


def get_latest_config(pool_cid: str) -> Optional[core.Thought]:
    """Get the most recent pool_config thought for a pool."""
    configs = core.query_thoughts(thought_type="pool_config", limit=100)
    pool_configs = [c for c in configs if c.content.get("pool") == pool_cid]
    return pool_configs[0] if pool_configs else None


def update_waterline(pool_cid: str, waterline: float, identity: core.Identity) -> bool:
    """Update a pool's waterline threshold, chaining to previous config."""
    pool = get_pool(pool_cid)
    if not pool:
        return False

    # Find previous config to chain from
    previous_config = get_latest_config(pool_cid)
    because = [pool_cid]
    if previous_config:
        because.append(previous_config.cid)

    # Create waterline update thought
    content = {
        "pool": pool_cid,
        "waterline": waterline,
        "previous_waterline": pool.rules.waterline,
        "previous_config": previous_config.cid if previous_config else None
    }

    thought = core.create_thought(
        content=content,
        thought_type="pool_config",
        identity=identity,
        because=because,
        source="pool/waterline"
    )
    core.store_thought(thought)

    # Update in-memory pool
    pool.rules.waterline = waterline
    _pools[pool_cid] = pool

    print(f"  Config chain: {thought.cid[:30]}... ← {previous_config.cid[:30] + '...' if previous_config else 'pool root'}")

    return True


# ============================================================================
# WATERLINE FILTERING
# ============================================================================

def filter_by_waterline(
    results: List[Dict[str, Any]],
    pool_cid: Optional[str] = None,
    default_waterline: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Filter query results by pool's waterline threshold.

    Args:
        results: List of query results with 'relevance' scores
        pool_cid: Pool to get waterline from (None = use default)
        default_waterline: Fallback if pool not found

    Returns:
        Filtered results above waterline
    """
    waterline = default_waterline

    if pool_cid:
        pool = get_pool(pool_cid)
        if pool:
            waterline = pool.rules.waterline

    return [r for r in results if r.get('relevance', 0) >= waterline]


def apply_pool_rules(
    thought: core.Thought,
    pool_cid: str
) -> Dict[str, Any]:
    """
    Validate a thought against pool rules.

    Returns:
        {
            "valid": bool,
            "errors": [str],
            "appetite": str  # welcomed, unauthorized_claim, etc.
        }
    """
    pool = get_pool(pool_cid)
    if not pool:
        return {"valid": False, "errors": ["Pool not found"], "appetite": "flagged"}

    rules = pool.rules
    errors = []

    # Check schema
    if rules.accept_schemas and thought.type not in rules.accept_schemas:
        errors.append(f"Schema '{thought.type}' not allowed in pool")

    # Check because chain
    if rules.require_because and not thought.because:
        errors.append("Because chain required")

    # Check payload size
    content_size = len(json.dumps(thought.content).encode())
    if content_size > rules.max_payload_bytes:
        errors.append(f"Payload {content_size} exceeds max {rules.max_payload_bytes}")

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "appetite": "unauthorized_claim"
        }

    return {"valid": True, "errors": [], "appetite": "welcomed"}


# ============================================================================
# CLI
# ============================================================================

def main():
    """Test pool functionality."""
    print("=" * 60)
    print("Pool Management Test")
    print("=" * 60)

    # Create identity
    identity = core.create_identity("pool-test")
    print(f"\nIdentity: {identity.cid[:40]}...")

    # Create default pool
    pool = get_default_pool(identity)
    print(f"\nDefault pool: {pool.cid}")
    print(f"  Waterline: {pool.rules.waterline}")
    print(f"  Accept schemas: {pool.rules.accept_schemas}")

    # Test waterline update
    print("\nUpdating waterline to 0.5...")
    update_waterline(pool.cid, 0.5, identity)

    pool = get_pool(pool.cid)
    print(f"  New waterline: {pool.rules.waterline}")

    # Test filtering
    print("\nTesting waterline filter...")
    fake_results = [
        {"cid": "a", "relevance": 0.8, "snippet": "High relevance"},
        {"cid": "b", "relevance": 0.4, "snippet": "Below waterline"},
        {"cid": "c", "relevance": 0.6, "snippet": "Above waterline"},
        {"cid": "d", "relevance": 0.2, "snippet": "Low relevance"},
    ]

    filtered = filter_by_waterline(fake_results, pool.cid)
    print(f"  {len(fake_results)} results → {len(filtered)} after waterline filter")
    for r in filtered:
        print(f"    {r['relevance']}: {r['snippet']}")

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
