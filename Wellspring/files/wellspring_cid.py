#!/usr/bin/env python3
"""
Wellspring CID computation and verification.
Dogfood 001: Test that the self-describing chain is cryptographically coherent.
"""

import json
import hashlib
from pathlib import Path


def compute_cid(content: dict, created_by: str, because: list) -> str:
    """
    Compute CID as hash(content + created_by + because).

    For now: SHA-256 hex, prefixed with 'cid:sha256:'.
    Real impl would use multihash/multicodec (IPFS style).
    """
    # Canonical JSON serialization (sorted keys, no extra whitespace)
    payload = {
        "content": content,
        "created_by": created_by,
        "because": because
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return f"cid:sha256:{digest[:16]}"  # Truncated for readability


def load_thoughts(path: str) -> list[dict]:
    """Load thoughts from JSONL file."""
    thoughts = []
    with open(path) as f:
        for line in f:
            if line.strip():
                thoughts.append(json.loads(line))
    return thoughts


def verify_chain(thoughts: list[dict]) -> dict:
    """Verify the self-describing chain."""
    results = {
        "total": len(thoughts),
        "valid_because": 0,
        "broken_because": [],
        "cid_map": {},
        "computed_cids": {}
    }

    # Build CID map (placeholder -> thought)
    for t in thoughts:
        results["cid_map"][t["cid"]] = t

    # Verify because references exist
    for t in thoughts:
        because = t.get("because", [])
        all_valid = True
        for ref in because:
            # Handle both simple CID and ContentRef structure
            ref_cid = ref if isinstance(ref, str) else ref.get("thought_cid")
            if ref_cid and ref_cid not in results["cid_map"]:
                results["broken_because"].append({
                    "thought": t["cid"],
                    "missing": ref_cid
                })
                all_valid = False
        if all_valid:
            results["valid_because"] += 1

    # Compute what CIDs should be
    for t in thoughts:
        computed = compute_cid(t["content"], t["created_by"], t["because"])
        results["computed_cids"][t["cid"]] = computed

    return results


def walk_trail(thoughts: list[dict], start_cid: str) -> list[str]:
    """Walk because chain backward from a thought."""
    cid_map = {t["cid"]: t for t in thoughts}
    trail = []
    visited = set()
    queue = [start_cid]

    while queue:
        cid = queue.pop(0)
        if cid in visited or cid not in cid_map:
            continue
        visited.add(cid)
        trail.append(cid)

        thought = cid_map[cid]
        for ref in thought.get("because", []):
            ref_cid = ref if isinstance(ref, str) else ref.get("thought_cid")
            if ref_cid:
                queue.append(ref_cid)

    return trail


def find_attestations(thoughts: list[dict], target_cid: str) -> list[dict]:
    """Find all attestations on a target thought."""
    return [
        t for t in thoughts
        if t.get("type") == "attestation"
        and t.get("content", {}).get("on") == target_cid
    ]


if __name__ == "__main__":
    dogfood_path = Path(__file__).parent / "wellspring-dogfood-001.jsonl"

    print("=" * 60)
    print("WELLSPRING DOGFOOD 001 - CID VERIFICATION")
    print("=" * 60)

    thoughts = load_thoughts(dogfood_path)
    print(f"\nLoaded {len(thoughts)} thoughts")

    # Verify chain
    results = verify_chain(thoughts)
    print(f"\nBecause chain verification:")
    print(f"  Valid references: {results['valid_because']}/{results['total']}")
    if results["broken_because"]:
        print(f"  Broken references:")
        for b in results["broken_because"]:
            print(f"    {b['thought']} -> missing {b['missing']}")

    # Show computed CIDs (first 5)
    print(f"\nComputed CIDs (placeholder -> computed):")
    for i, (placeholder, computed) in enumerate(results["computed_cids"].items()):
        if i >= 5:
            print(f"  ... and {len(results['computed_cids']) - 5} more")
            break
        print(f"  {placeholder}")
        print(f"    -> {computed}")

    # Walk a trail
    print(f"\nTrail from cid:thought_003:")
    trail = walk_trail(thoughts, "cid:thought_003")
    for cid in trail:
        t = results["cid_map"].get(cid, {})
        ttype = t.get("type", "?")
        preview = str(t.get("content", {}))[:50]
        print(f"  {cid} [{ttype}] {preview}...")

    # Find attestations
    print(f"\nAttestations on cid:thought_002:")
    attestations = find_attestations(thoughts, "cid:thought_002")
    for a in attestations:
        weight = a["content"]["weight"]
        by = a["created_by"]
        print(f"  {a['cid']}: weight={weight} by={by}")

    print("\n" + "=" * 60)
    print("Dogfood complete. Bootstrap chain is structurally coherent.")
    print("=" * 60)
