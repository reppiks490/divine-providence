"""Multi-scale price terrain and cross-asset context; descriptive, time-correct."""
from __future__ import annotations

from collections import defaultdict
from statistics import mean

from .contracts import EvidenceTier


def build(items: list[dict], asof_ns: int, *, freshness_ns: int = 300_000_000_000) -> dict:
    families: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in items:
        e = row["event"]
        if e["kind"] == "bar":
            families[(row["symbol"], row["representation_id"])].append(row)
    terrain = []
    for (symbol, representation), bars in sorted(families.items()):
        bars.sort(key=lambda r: (r["event"]["event_ns"], r["position"]))
        bars = bars[-200:]
        closes = [float(r["event"]["payload"]["close"]) for r in bars]
        ranges = [float(r["event"]["payload"]["high"]) - float(r["event"]["payload"]["low"]) for r in bars]
        pivots = []
        # The right-hand bars must already have closed and become available.
        for i in range(2, len(bars) - 2):
            highs = [float(x["event"]["payload"]["high"]) for x in bars[i - 2:i + 3]]
            lows = [float(x["event"]["payload"]["low"]) for x in bars[i - 2:i + 3]]
            kind = "resistance" if highs[2] > max(highs[:2] + highs[3:]) else (
                   "support" if lows[2] < min(lows[:2] + lows[3:]) else None)
            if kind:
                pivots.append({"kind": kind, "price": highs[2] if kind == "resistance" else lows[2],
                               "origin_ns": bars[i]["event"]["event_ns"],
                               "confirmed_ns": bars[i + 2]["event"]["available_ns"],
                               "source_hash": bars[i]["event_hash"], "evidence_tier": EvidenceTier.CANDLE_PROXY})
        # A strictly labeled candle-pattern hypothesis, never true resting liquidity.
        origin = None
        if len(bars) >= 5:
            for i in range(len(bars) - 3, 1, -1):
                b = bars[i]["event"]["payload"]
                later = bars[i + 1:i + 3]
                prior_range = mean(ranges[max(0, i - 12):i])
                bullish = float(b["close"]) < float(b["open"]) and all(
                    float(r["event"]["payload"]["close"]) > float(r["event"]["payload"]["open"]) for r in later)
                displaced = (float(later[-1]["event"]["payload"]["close"]) - float(b["close"])) > 1.5 * max(prior_range, 1e-12)
                if bullish and displaced:
                    origin = {"name": "candle_origin_hypothesis", "lower": float(b["low"]),
                              "upper": float(b["high"]), "origin_ns": bars[i]["event"]["event_ns"],
                              "confirmed_ns": later[-1]["event"]["available_ns"],
                              "source_hash": bars[i]["event_hash"], "evidence_tier": EvidenceTier.CANDLE_PROXY,
                              "empirically_validated": False}
                    break
        last = bars[-1]["event"]
        terrain.append({"symbol": symbol, "representation_id": representation, "bars": len(bars),
                        "last_close": closes[-1], "net_change": closes[-1] - closes[0],
                        "average_range_14": mean(ranges[-14:]),
                        "direction": "up" if closes[-1] > closes[max(0, len(closes) - 4)] else (
                            "down" if closes[-1] < closes[max(0, len(closes) - 4)] else "flat"),
                        "last_available_ns": last["available_ns"],
                        "stale": asof_ns - last["available_ns"] > freshness_ns,
                        "confirmed_pivots": pivots[-8:], "candle_origin_hypothesis": origin})
    # Short-lived descriptive direction comparison. It makes no lead-lag or causal claim.
    by_symbol: dict[str, list[dict]] = defaultdict(list)
    for row in terrain:
        if not row["stale"] and row["bars"] >= 2:
            by_symbol[row["symbol"]].append(row)
    representatives = {symbol: min(rows, key=lambda r: (r["representation_id"] != "clock:1m", r["representation_id"]))
                       for symbol, rows in by_symbol.items()}
    relationships = []
    symbols = sorted(representatives)
    for i, a in enumerate(symbols):
        for b in symbols[i + 1:]:
            left, right = representatives[a], representatives[b]
            relationships.append({"symbols": [a, b],
                                  "observed_direction": "agree" if left["direction"] == right["direction"] else "diverge",
                                  "representations": [left["representation_id"], right["representation_id"]],
                                  "interpretation": "same-time descriptive context; no predictive lead-lag claim"})
    return {"terrain": terrain, "relationships": relationships,
            "confirmed_only": True, "book_depth_inferred": False}
