"""Deterministic market state from observations that were available at a time."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite

from .contracts import EvidenceTier, digest
from .store import EventStore
from .atlas import build as build_atlas


@dataclass(frozen=True)
class Scenario:
    name: str
    volatility_multiplier: float = 1.0
    depth_multiplier: float = 1.0
    suppress_sources: tuple[str, ...] = ()
    macro_shift: float = 0.0

    def __post_init__(self):
        if not self.name or not 0 <= self.depth_multiplier <= 10 or not 0 < self.volatility_multiplier <= 20:
            raise ValueError("invalid scenario")
        if not isfinite(self.macro_shift):
            raise ValueError("invalid macro shift")


def _book(records: list[dict], invalid: bool) -> dict:
    if invalid:
        return {"status": "sequence_gap", "bids": [], "asks": [], "imbalance": None}
    bids: dict[float, float] = {}
    asks: dict[float, float] = {}
    initialized = False
    last_seq = None
    for item in sorted(records, key=lambda r: (r["event"]["sequence"], r["position"])):
        e = item["event"]
        p = e["payload"]
        sequence = e["sequence"]
        if last_seq is not None and sequence <= last_seq:
            return {"status": "sequence_conflict", "bids": [], "asks": [], "imbalance": None}
        last_seq = sequence
        if e["kind"] == "book_snapshot":
            bids = {float(px): float(qty) for px, qty in p["bids"] if float(qty) > 0}
            asks = {float(px): float(qty) for px, qty in p["asks"] if float(qty) > 0}
            initialized = True
        elif initialized:
            side = p["side"]
            if side not in ("bid", "ask") or p["action"] not in ("set", "delete"):
                raise ValueError("invalid book delta")
            levels = bids if side == "bid" else asks
            price = float(p["price"])
            size = float(p["size"])
            if p["action"] == "delete" or size == 0:
                levels.pop(price, None)
            elif size > 0:
                levels[price] = size
            else:
                raise ValueError("negative depth")
    if not initialized:
        return {"status": "missing_snapshot", "bids": [], "asks": [], "imbalance": None}
    best_bid = max(bids, default=None)
    best_ask = min(asks, default=None)
    bid_levels = sorted(bids.items(), reverse=True)[:10]
    ask_levels = sorted(asks.items())[:10]
    if best_bid is None or best_ask is None or best_bid >= best_ask:
        return {"status": "invalid_crossed_or_empty", "bids": bid_levels,
                "asks": ask_levels, "imbalance": None}
    b = sum(q for _, q in bid_levels)
    a = sum(q for _, q in ask_levels)
    return {"status": "true_depth", "best_bid": best_bid, "best_ask": best_ask,
            "spread": best_ask - best_bid, "bids": bid_levels, "asks": ask_levels,
            "imbalance": (b - a) / (b + a) if b + a else None, "sequence": last_seq}


def frame(store: EventStore, at_ns: int, *, symbol: str | None = None,
          flow_window_ns: int = 60_000_000_000, scenario: Scenario | None = None) -> dict:
    """Produce one immutable-input as-of snapshot; scenarios are visibly synthetic."""
    if type(flow_window_ns) is not int or flow_window_ns <= 0:
        raise ValueError("positive flow window required")
    items = store.asof(at_ns, symbol=symbol)
    if scenario:
        items = [i for i in items if i["source"] not in scenario.suppress_sources]
    synthetic_sources = sorted(source_id for source_id in {i["source"] for i in items}
                               if store.source(source_id).origin == "synthetic")
    bars: dict[tuple[str, str], dict] = {}
    trades: dict[str, list[dict]] = defaultdict(list)
    book_events: dict[str, list[dict]] = defaultdict(list)
    macro: dict[str, dict] = {}
    schedules: list[dict] = []
    for item in items:
        e = item["event"]
        k = e["kind"]
        if k == "bar":
            key = (item["symbol"], item["representation_id"])
            if key not in bars or (e["event_ns"], item["position"]) > (bars[key]["event_ns"], bars[key]["position"]):
                bars[key] = {"symbol": item["symbol"], "representation_id": item["representation_id"],
                             "source_id": item["source"], "event_ns": e["event_ns"],
                             "available_ns": e["available_ns"], "position": item["position"],
                             "open": e["payload"].get("open"), "high": e["payload"].get("high"),
                             "low": e["payload"].get("low"), "close": e["payload"].get("close"),
                             "volume": e["payload"].get("volume"), "event_hash": item["event_hash"],
                             "evidence_tier": e["evidence_tier"], "age_ns": at_ns - e["available_ns"]}
        elif k == "trade" and at_ns - flow_window_ns <= e["event_ns"] <= at_ns:
            trades[item["symbol"]].append(item)
        elif k.startswith("book_"):
            book_events[item["source"]].append(item)
        elif k == "macro":
            key = f"{item['source']}:{e['payload'].get('series', e['source_event_id'])}"
            if key not in macro or (e["available_ns"], item["position"]) > (macro[key]["available_ns"], macro[key]["position"]):
                macro[key] = {"source_id": item["source"], "symbol": item["symbol"],
                              "event_ns": e["event_ns"], "available_ns": e["available_ns"],
                              "published_ns": e["published_ns"], "position": item["position"],
                              "values": e["payload"], "revision": e["revision"],
                              "age_ns": at_ns - e["available_ns"]}
        elif k == "schedule":
            schedules.append({"event_ns": e["event_ns"], "known_ns": e["available_ns"],
                              "payload": e["payload"], "source_id": item["source"]})
    flow = {}
    for ticker, rows in trades.items():
        buys = sells = unknown = 0.0
        for item in rows:
            p = item["event"]["payload"]
            qty = float(p["size"])
            if qty <= 0 or not isfinite(qty):
                raise ValueError("invalid true trade size")
            side = p.get("side", "unknown")
            if side == "buy": buys += qty
            elif side == "sell": sells += qty
            else: unknown += qty
        flow[ticker] = {"buy": buys, "sell": sells, "unknown": unknown,
                        "delta": buys - sells, "evidence_tier": EvidenceTier.TRUE_TRADE,
                        "observations": len(rows)}
    gaps = {r["source_id"] for r in store.gaps_asof(at_ns)
            if (symbol is None or store.source(r["source_id"]).symbol == symbol)
            and (scenario is None or r["source_id"] not in scenario.suppress_sources)}
    books = {source: _book(rows, source in gaps) for source, rows in book_events.items()}
    for source in gaps:
        if source not in books and (symbol is None or store.source(source).symbol == symbol):
            books[source] = _book([], True)
    result = {"schema": 1, "asof_ns": at_ns, "symbol_filter": symbol,
              "prices": sorted(bars.values(), key=lambda x: (x["symbol"], x["representation_id"])),
              "flow": flow, "books": books,
              "macro": sorted(macro.values(), key=lambda x: (x["source_id"], str(x["values"].get("series")))),
              "schedule": sorted(schedules, key=lambda x: (x["event_ns"], x["source_id"])),
              "source_count": len({i["source"] for i in items}),
              "atlas": build_atlas(items, at_ns),
              "evidence_hashes": [i["event_hash"] for i in items],
              "quality": {"gap_sources": sorted(gaps), "missing_depth": not bool(books),
                          "missing_true_trades": not bool(flow), "synthetic_sources": synthetic_sources,
                          "suppressed_sources": list(scenario.suppress_sources) if scenario else []},
              "synthetic": scenario is not None or bool(synthetic_sources),
              "scenario": scenario.name if scenario else None,
              "execution_authorized": False}
    if scenario:
        result = deepcopy(result)
        for row in result["books"].values():
            row["bids"] = [(p, q * scenario.depth_multiplier) for p, q in row["bids"]]
            row["asks"] = [(p, q * scenario.depth_multiplier) for p, q in row["asks"]]
            # Equal scaling preserves the ratio; an empty book is invalidated.
            if scenario.depth_multiplier == 0:
                row["status"], row["imbalance"] = "synthetic_liquidity_drought", None
        for row in result["prices"]:
            if row["high"] is not None and row["low"] is not None:
                midpoint = (float(row["high"]) + float(row["low"])) / 2
                half = (float(row["high"]) - float(row["low"])) * scenario.volatility_multiplier / 2
                row["scenario_range"] = [midpoint - half, midpoint + half]
        for row in result["macro"]:
            row["scenario_shift"] = scenario.macro_shift
            if isinstance(row["values"].get("value"), (int, float)):
                row["scenario_value"] = row["values"]["value"] + scenario.macro_shift
        result["quality"]["scenario_evidence_only"] = True
    result["frame_hash"] = digest(result)
    return result


def compare(real: dict, alternative: dict) -> dict:
    if real["asof_ns"] != alternative["asof_ns"] or not alternative["synthetic"]:
        raise ValueError("comparison requires the same decision time and a labeled scenario")
    return {"asof_ns": real["asof_ns"], "base_hash": real["frame_hash"],
            "scenario_hash": alternative["frame_hash"], "scenario": alternative["scenario"],
            "source_delta": alternative["source_count"] - real["source_count"],
            "quality_delta": {key: [real["quality"].get(key), alternative["quality"].get(key)]
                              for key in sorted(set(real["quality"]) | set(alternative["quality"]))
                              if real["quality"].get(key) != alternative["quality"].get(key)},
            "alterations": {"range": any("scenario_range" in p for p in alternative["prices"]),
                            "depth": any(book.get("status") == "synthetic_liquidity_drought" for book in alternative["books"].values()),
                            "macro": any("scenario_value" in m and m["scenario_value"] != m["values"]["value"] for m in alternative["macro"]),
                            "sources": alternative["source_count"] != real["source_count"]},
            "empirical_counterfactual_fill": False}
