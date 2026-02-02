#!/usr/bin/env python3
"""
WoT CID Computation Test Vector Generator

Generates concrete test vectors for CID computation conformance testing.
"""

import json
import unicodedata
from typing import Any

import cbor2
from blake3 import blake3

# Constants
SELF_MARKER = b'\x00' * 32
SAMPLE_CREATOR = b'\x01' * 32  # All 0x01 bytes for predictable testing


def normalize_string(s: str) -> str:
    """NFC normalize a string."""
    return unicodedata.normalize('NFC', s)


def normalize_content(obj: Any) -> Any:
    """Recursively NFC normalize all strings in an object."""
    if isinstance(obj, str):
        return normalize_string(obj)
    elif isinstance(obj, dict):
        return {k: normalize_content(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_content(v) for v in obj]
    return obj


def canonical_cbor(obj: Any) -> bytes:
    """
    Produce deterministic CBOR encoding.

    cbor2 with canonical=True:
    - Sorts map keys lexicographically
    - Uses shortest integer encoding
    - No indefinite-length items
    """
    return cbor2.dumps(obj, canonical=True)


def compute_cid(thought: dict) -> bytes:
    """
    Compute CID for a thought.

    CID = blake3(canonical_cbor({type, content, created_by, because}))
    """
    # Extract CID-relevant fields only
    cid_input = {
        "type": thought["type"],
        "content": thought["content"],
        "created_by": thought["created_by"],
        "because": thought["because"],
    }

    # Normalize any strings in content
    cid_input = normalize_content(cid_input)

    # Canonical CBOR encoding
    cbor_bytes = canonical_cbor(cid_input)

    # BLAKE3 hash
    return blake3(cbor_bytes).digest()


def generate_test_vectors() -> list[dict]:
    """Generate a suite of test vectors."""
    vectors = []

    # Vector 1: Minimal basic thought
    thought1 = {
        "type": "basic",
        "content": "Hello, WoT!",
        "created_by": SAMPLE_CREATOR,
        "because": [],
    }
    cbor1 = canonical_cbor(normalize_content({
        "type": thought1["type"],
        "content": thought1["content"],
        "created_by": thought1["created_by"],
        "because": thought1["because"],
    }))
    cid1 = compute_cid(thought1)

    vectors.append({
        "name": "basic_hello",
        "description": "Minimal basic thought with simple string content",
        "input": {
            "type": "basic",
            "content": "Hello, WoT!",
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [],
        },
        "cbor_hex": cbor1.hex(),
        "cid_hex": cid1.hex(),
    })

    # Vector 2: Empty content
    thought2 = {
        "type": "basic",
        "content": "",
        "created_by": SAMPLE_CREATOR,
        "because": [],
    }
    cbor2_bytes = canonical_cbor(normalize_content({
        "type": thought2["type"],
        "content": thought2["content"],
        "created_by": thought2["created_by"],
        "because": thought2["because"],
    }))
    cid2 = compute_cid(thought2)

    vectors.append({
        "name": "empty_content",
        "description": "Basic thought with empty string content",
        "input": {
            "type": "basic",
            "content": "",
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [],
        },
        "cbor_hex": cbor2_bytes.hex(),
        "cid_hex": cid2.hex(),
    })

    # Vector 3: Unicode (NFC normalized)
    thought3 = {
        "type": "basic",
        "content": "café résumé naïve",  # Various accented chars
        "created_by": SAMPLE_CREATOR,
        "because": [],
    }
    cbor3 = canonical_cbor(normalize_content({
        "type": thought3["type"],
        "content": thought3["content"],
        "created_by": thought3["created_by"],
        "because": thought3["because"],
    }))
    cid3 = compute_cid(thought3)

    vectors.append({
        "name": "unicode_accents",
        "description": "Content with accented characters (NFC normalized)",
        "input": {
            "type": "basic",
            "content": "café résumé naïve",
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [],
        },
        "cbor_hex": cbor3.hex(),
        "cid_hex": cid3.hex(),
    })

    # Vector 4: Structured content (attestation)
    attestation_content = {
        "on": b'\x02' * 32,  # Target thought CID
        "weight": 0.8,
        "aspect": b'\x03' * 32,  # Aspect CID
    }
    thought4 = {
        "type": "attestation",
        "content": attestation_content,
        "created_by": SAMPLE_CREATOR,
        "because": [b'\x02' * 32],  # References the target
    }
    cbor4 = canonical_cbor(normalize_content({
        "type": thought4["type"],
        "content": thought4["content"],
        "created_by": thought4["created_by"],
        "because": thought4["because"],
    }))
    cid4 = compute_cid(thought4)

    vectors.append({
        "name": "attestation_structured",
        "description": "Attestation with structured content (nested map)",
        "input": {
            "type": "attestation",
            "content": {
                "on": (b'\x02' * 32).hex(),
                "weight": 0.8,
                "aspect": (b'\x03' * 32).hex(),
            },
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [(b'\x02' * 32).hex()],
        },
        "cbor_hex": cbor4.hex(),
        "cid_hex": cid4.hex(),
    })

    # Vector 5: Self-referential identity
    identity_content = {
        "name": "Keif",
        "pubkey": "ed25519:" + ("ab" * 32),  # Fake pubkey hex
    }
    thought5 = {
        "type": "identity",
        "content": identity_content,
        "created_by": SELF_MARKER,  # Self-referential
        "because": [],
    }
    cbor5 = canonical_cbor(normalize_content({
        "type": thought5["type"],
        "content": thought5["content"],
        "created_by": thought5["created_by"],
        "because": thought5["because"],
    }))
    cid5 = compute_cid(thought5)

    vectors.append({
        "name": "identity_self_ref",
        "description": "Identity thought with SELF_MARKER (32 zero bytes) as created_by",
        "input": {
            "type": "identity",
            "content": {
                "name": "Keif",
                "pubkey": "ed25519:" + ("ab" * 32),
            },
            "created_by": SELF_MARKER.hex(),
            "because": [],
        },
        "cbor_hex": cbor5.hex(),
        "cid_hex": cid5.hex(),
        "note": "After CID computation, replace created_by with the computed CID",
    })

    # Vector 6: Connection thought
    connection_content = {
        "from": b'\x04' * 32,
        "to": b'\x05' * 32,
        "relation": "supports",
    }
    thought6 = {
        "type": "connection",
        "content": connection_content,
        "created_by": SAMPLE_CREATOR,
        "because": [b'\x04' * 32, b'\x05' * 32],
    }
    cbor6 = canonical_cbor(normalize_content({
        "type": thought6["type"],
        "content": thought6["content"],
        "created_by": thought6["created_by"],
        "because": thought6["because"],
    }))
    cid6 = compute_cid(thought6)

    vectors.append({
        "name": "connection_supports",
        "description": "Connection thought linking two thoughts with 'supports' relation",
        "input": {
            "type": "connection",
            "content": {
                "from": (b'\x04' * 32).hex(),
                "to": (b'\x05' * 32).hex(),
                "relation": "supports",
            },
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [(b'\x04' * 32).hex(), (b'\x05' * 32).hex()],
        },
        "cbor_hex": cbor6.hex(),
        "cid_hex": cid6.hex(),
    })

    # Vector 7: Multiple because references
    thought7 = {
        "type": "basic",
        "content": "Synthesized from multiple sources",
        "created_by": SAMPLE_CREATOR,
        "because": [b'\x06' * 32, b'\x07' * 32, b'\x08' * 32],
    }
    cbor7 = canonical_cbor(normalize_content({
        "type": thought7["type"],
        "content": thought7["content"],
        "created_by": thought7["created_by"],
        "because": thought7["because"],
    }))
    cid7 = compute_cid(thought7)

    vectors.append({
        "name": "multiple_because",
        "description": "Thought with three entries in because chain",
        "input": {
            "type": "basic",
            "content": "Synthesized from multiple sources",
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [
                (b'\x06' * 32).hex(),
                (b'\x07' * 32).hex(),
                (b'\x08' * 32).hex(),
            ],
        },
        "cbor_hex": cbor7.hex(),
        "cid_hex": cid7.hex(),
    })

    # Vector 8: Emoji content
    thought8 = {
        "type": "basic",
        "content": "I love WoT! 🌐🔗💭",
        "created_by": SAMPLE_CREATOR,
        "because": [],
    }
    cbor8 = canonical_cbor(normalize_content({
        "type": thought8["type"],
        "content": thought8["content"],
        "created_by": thought8["created_by"],
        "because": thought8["because"],
    }))
    cid8 = compute_cid(thought8)

    vectors.append({
        "name": "emoji_content",
        "description": "Content with emoji characters (multi-byte UTF-8)",
        "input": {
            "type": "basic",
            "content": "I love WoT! 🌐🔗💭",
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [],
        },
        "cbor_hex": cbor8.hex(),
        "cid_hex": cid8.hex(),
    })

    # Vector 9: NFD to NFC normalization test
    # "café" in NFD (decomposed): c a f e + combining acute accent
    nfd_cafe = "cafe\u0301"  # NFD form
    nfc_cafe = unicodedata.normalize('NFC', nfd_cafe)  # NFC form: "café"

    thought9 = {
        "type": "basic",
        "content": nfd_cafe,  # Input is NFD
        "created_by": SAMPLE_CREATOR,
        "because": [],
    }
    # After normalization, should match NFC
    cbor9 = canonical_cbor(normalize_content({
        "type": thought9["type"],
        "content": thought9["content"],
        "created_by": thought9["created_by"],
        "because": thought9["because"],
    }))
    cid9 = compute_cid(thought9)

    vectors.append({
        "name": "nfd_to_nfc_normalization",
        "description": "Input in NFD form MUST be normalized to NFC before hashing",
        "input": {
            "type": "basic",
            "content": nfd_cafe,
            "content_note": "Input is NFD: 'cafe' + U+0301 (combining acute)",
            "created_by": SAMPLE_CREATOR.hex(),
            "because": [],
        },
        "expected_nfc_content": nfc_cafe,
        "cbor_hex": cbor9.hex(),
        "cid_hex": cid9.hex(),
    })

    return vectors


def main():
    """Generate and output test vectors."""
    vectors = generate_test_vectors()

    output = {
        "version": "0.1",
        "generated": "2026-01-31",
        "description": "WoT CID computation test vectors",
        "hash_algorithm": "BLAKE3-256",
        "serialization": "Canonical CBOR (RFC 8949 deterministic)",
        "string_normalization": "NFC (Unicode Normalization Form C)",
        "vectors": vectors,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
