"""Private-source boundary for SuperMesh-X.

Private records may be used locally/inside authorized private runtimes, but raw content
must not be routed to public providers unless an explicit user-approved transform exists.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable


def can_route_payload(record: Dict[str, Any], target_class: str) -> Dict[str, Any]:
    source_class = record.get("source_class")
    if source_class in {"user_authorized_private", "derived_private_feature"} and target_class == "public_provider":
        return {"allowed": False, "reason": "private_to_public_blocked"}
    return {"allowed": True, "reason": "allowed"}


def redact_private_record(record: Dict[str, Any], allow_fields: Iterable[str]) -> Dict[str, Any]:
    allowed = set(allow_fields)
    out = {k: record[k] for k in allowed if k in record}
    out["source_class"] = "derived_private_feature"
    return out
