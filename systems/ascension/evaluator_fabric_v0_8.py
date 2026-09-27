"""ASCENSION Evaluator Fabric v0.8.

Strict RFC 9162-style Merkle inclusion verification layered on the known-good
v0.7 compact-consistency and signed-witness primitives. Read-only CANDIDATE.
"""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from evaluator_fabric_v0_7 import (
    canonical_json,
    verify_compact_consistency,
    verify_signed_witness_observations,
    verify_transparency_transition,
)

MAX_UINT64 = (1 << 64) - 1


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def merkle_leaf_hash(data: Any) -> bytes:
    """RFC 9162 leaf hash: SHA-256(0x00 || data)."""
    if isinstance(data, memoryview):
        data = data.tobytes()
    elif isinstance(data, bytearray):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError("leaf data must be bytes-like")
    return _h(b"\x00" + data)


def _node(left: bytes, right: bytes) -> bytes:
    return _h(b"\x01" + left + right)


def _hash32(value: Any) -> bytes:
    if isinstance(value, memoryview):
        value = value.tobytes()
    elif isinstance(value, bytearray):
        value = bytes(value)
    elif isinstance(value, str):
        value = bytes.fromhex(value)
    if not isinstance(value, bytes):
        raise TypeError("hash must be bytes-like or a hex string")
    if len(value) != 32:
        raise ValueError("hash must be exactly 32 bytes")
    return value


def _uint64(value: Any, *, name: str, allow_zero: bool) -> int:
    # bool is an int subclass in Python; rejecting it prevents type-confusion.
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum or value > MAX_UINT64:
        raise ValueError(f"{name} outside uint64 domain")
    return value


def _path_nodes(inclusion_path: Any) -> list[bytes]:
    if isinstance(inclusion_path, (str, bytes, bytearray, memoryview)) or not isinstance(inclusion_path, Sequence):
        raise TypeError("inclusion_path must be a sequence of hashes")
    return [_hash32(node) for node in inclusion_path]


def expected_inclusion_path_length(leaf_index: Any, tree_size: Any) -> int:
    """Return the exact RFC 9162 audit-path node count for index/size.

    The count is derived by the same structural index walk used by RFC 9162
    section 2.1.3.2, without consuming any proof hashes.
    """
    size = _uint64(tree_size, name="tree_size", allow_zero=False)
    index = _uint64(leaf_index, name="leaf_index", allow_zero=True)
    if index >= size:
        raise ValueError("leaf_index out of range")

    fn = index
    sn = size - 1
    count = 0
    while sn != 0:
        if (fn & 1) or fn == sn:
            if not (fn & 1):
                while fn != 0 and not (fn & 1):
                    fn >>= 1
                    sn >>= 1
        count += 1
        fn >>= 1
        sn >>= 1
    return count


def verify_strict_inclusion(
    leaf_hash: Any,
    leaf_index: Any,
    tree_size: Any,
    root_hash: Any,
    inclusion_path: Any,
):
    """Verify an RFC 9162 Merkle inclusion proof with strict geometry.

    The caller supplies the already domain-separated leaf hash. Use
    :func:`merkle_leaf_hash` when starting from raw leaf bytes.
    """
    reasons: list[str] = []
    try:
        size = _uint64(tree_size, name="tree_size", allow_zero=False)
    except (TypeError, ValueError, OverflowError):
        return {"valid": False, "reasons": ["tree_size_invalid"]}

    try:
        index = _uint64(leaf_index, name="leaf_index", allow_zero=True)
    except (TypeError, ValueError, OverflowError):
        return {"valid": False, "reasons": ["leaf_index_invalid"], "tree_size": size}

    if index >= size:
        return {
            "valid": False,
            "reasons": ["leaf_index_out_of_range"],
            "leaf_index": index,
            "tree_size": size,
        }

    try:
        current = _hash32(leaf_hash)
    except (TypeError, ValueError, OverflowError):
        return {
            "valid": False,
            "reasons": ["leaf_hash_invalid"],
            "leaf_index": index,
            "tree_size": size,
        }

    try:
        expected_root = _hash32(root_hash)
    except (TypeError, ValueError, OverflowError):
        return {
            "valid": False,
            "reasons": ["root_hash_invalid"],
            "leaf_index": index,
            "tree_size": size,
        }

    try:
        path = _path_nodes(inclusion_path)
    except (TypeError, ValueError, OverflowError):
        return {
            "valid": False,
            "reasons": ["inclusion_path_invalid"],
            "leaf_index": index,
            "tree_size": size,
        }

    expected_nodes = expected_inclusion_path_length(index, size)
    if len(path) != expected_nodes:
        return {
            "valid": False,
            "reasons": ["inclusion_path_length_mismatch"],
            "leaf_index": index,
            "tree_size": size,
            "proof_nodes": len(path),
            "expected_proof_nodes": expected_nodes,
        }

    fn = index
    sn = size - 1
    r = current
    for sibling in path:
        # With exact geometry this guard should never fire, but retaining the RFC
        # condition makes the implementation fail closed if invariants drift.
        if sn == 0:
            reasons.append("inclusion_path_too_long")
            break
        if (fn & 1) or fn == sn:
            r = _node(sibling, r)
            if not (fn & 1):
                while fn != 0 and not (fn & 1):
                    fn >>= 1
                    sn >>= 1
        else:
            r = _node(r, sibling)
        fn >>= 1
        sn >>= 1

    if not reasons:
        if sn != 0:
            reasons.append("inclusion_path_too_short")
        if r != expected_root:
            reasons.append("inclusion_root_mismatch")

    return {
        "valid": not reasons,
        "reasons": sorted(set(reasons)),
        "leaf_index": index,
        "tree_size": size,
        "proof_nodes": len(path),
        "expected_proof_nodes": expected_nodes,
        "computed_root": r.hex(),
        "expected_root": expected_root.hex(),
    }


def verify_transparency_evidence(
    leaf_hash: Any,
    leaf_index: Any,
    second_size: Any,
    second_root: Any,
    inclusion_path: Any,
    first_size: Any,
    first_root: Any,
    consistency_path: Any,
    observations: Any,
    witness_keys: Any,
    minimum_witnesses: Any,
    expected_log_id: Any,
    now_iso: Any,
    max_age_seconds: Any,
    future_tolerance_seconds: int = 300,
):
    """Compose strict inclusion with the v0.7 consistency+witness gate.

    Both sub-gates are evaluated read-only. Any malformed evidence yields an
    invalid result rather than escaping an exception from this boundary.
    """
    try:
        inclusion = verify_strict_inclusion(
            leaf_hash, leaf_index, second_size, second_root, inclusion_path
        )
    except Exception:
        inclusion = {"valid": False, "reasons": ["inclusion_internal_error"]}

    try:
        transition = verify_transparency_transition(
            first_size,
            second_size,
            first_root,
            second_root,
            consistency_path,
            observations,
            witness_keys,
            minimum_witnesses,
            expected_log_id,
            now_iso,
            max_age_seconds,
            future_tolerance_seconds,
        )
    except Exception:
        transition = {"valid": False, "reasons": ["transition_internal_error"]}

    reasons = ["inclusion:" + r for r in inclusion.get("reasons", [])]
    reasons.extend("transition:" + r for r in transition.get("reasons", []))
    return {
        "valid": bool(inclusion.get("valid")) and bool(transition.get("valid")) and not reasons,
        "reasons": sorted(set(reasons)),
        "inclusion": inclusion,
        "transition": transition,
    }
