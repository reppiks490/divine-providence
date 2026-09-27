"""Fuse public market events with private portfolio context without mixing provenance."""

from __future__ import annotations

from typing import Any, Dict


def fuse_public_event_with_private_context(public_event: Dict[str, Any], private_context: Dict[str, Any]) -> Dict[str, Any]:
    combined = dict(public_event)
    combined["portfolio_id"] = private_context.get("portfolio_id")
    combined["portfolio_overlay_score"] = private_context.get("overlay_score")
    return {
        "combined": combined,
        "public_evidence_ids": list(public_event.get("evidence_ids", []) or []),
        "private_evidence_ids": list(private_context.get("evidence_ids", []) or []),
        "private_context_exportable": False,
    }
