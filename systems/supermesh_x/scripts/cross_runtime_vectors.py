"""Small deterministic signature vectors for cross-runtime conformance tests.

The canonical profile is SuperMesh-specific JSON (sorted keys, compact
separators, ASCII escapes, no NaN). It is not represented as RFC 8785/JCS.
"""
from __future__ import annotations
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization


def canonical_json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def ed25519_signature_vector(seed_hex, statement):
    seed = bytes.fromhex(str(seed_hex))
    if len(seed) != 32:
        raise ValueError("Ed25519 seed must be 32 bytes")
    private = Ed25519PrivateKey.from_private_bytes(seed)
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    canonical = canonical_json_bytes(statement)
    signature = private.sign(canonical)
    return {
        "schema": 1,
        "canonical_profile": "supermesh-json-v1",
        "algorithm": "Ed25519",
        "public_key_hex": public.hex(),
        "canonical_hex": canonical.hex(),
        "signature_hex": signature.hex(),
    }


def verify_signature_vector(vector):
    try:
        public = bytes.fromhex(vector["public_key_hex"])
        canonical = bytes.fromhex(vector["canonical_hex"])
        signature = bytes.fromhex(vector["signature_hex"])
        if vector.get("algorithm") != "Ed25519" or vector.get("canonical_profile") != "supermesh-json-v1":
            return False
        Ed25519PublicKey.from_public_bytes(public).verify(signature, canonical)
        return True
    except Exception:
        return False
