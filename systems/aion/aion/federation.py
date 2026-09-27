"""Versioned, read-only exports for the existing sibling systems."""
from __future__ import annotations

from .contracts import EvidenceTier


def export_views(frame: dict) -> dict[str, dict]:
    common = {"schema": "aion-evidence-v1", "asof_ns": frame["asof_ns"],
              "frame_hash": frame["frame_hash"], "source_hashes": frame["evidence_hashes"],
              "synthetic": frame["synthetic"], "quality": frame["quality"],
              "production_authorized": False, "execution_authorized": False}
    return {
        "athena": {**common, "packet_type": "state_input", "prices": frame["prices"],
                   "flow": frame["flow"], "books": frame["books"], "macro": frame["macro"]},
        "argus": {**common, "packet_type": "microstructure_evidence",
                  "true_trades": {symbol: info for symbol, info in frame["flow"].items()
                                  if info["evidence_tier"] == EvidenceTier.TRUE_TRADE},
                  "depth": {source: book for source, book in frame["books"].items()
                            if book["status"] == "true_depth"}},
        "daedalus": {**common, "packet_type": "research_context",
                     "representations": [{"symbol": p["symbol"], "representation_id": p["representation_id"],
                                          "event_hash": p["event_hash"]} for p in frame["prices"]],
                     "protected_holdout_spent": False},
        "icarus": {**common, "packet_type": "shadow_preview", "suggested_order": None,
                   "advisory_only": True},
    }
