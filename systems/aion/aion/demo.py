"""A fully labeled synthetic scene for exploring the cockpit without market claims."""
from __future__ import annotations

from hashlib import sha256

from .contracts import EvidenceTier as Tier, Observation, SourceSpec
from .store import EventStore
from .replay import frame


SECOND = 1_000_000_000
START = 1_790_081_700 * SECOND


def install(store: EventStore) -> dict:
    specs = [
        SourceSpec("DEMO:NQ:1m", "clock:1m", "NQ", ("bar",), Tier.CANDLE_PROXY, sha256(b"demo-nq-bars").hexdigest(), origin="synthetic"),
        SourceSpec("DEMO:ES:1m", "clock:1m", "ES", ("bar",), Tier.CANDLE_PROXY, sha256(b"demo-es-bars").hexdigest(), origin="synthetic"),
        SourceSpec("DEMO:NQ:trades", "trade:event", "NQ", ("trade",), Tier.TRUE_TRADE, sha256(b"demo-trades").hexdigest(), sequence_policy="contiguous", origin="synthetic"),
        SourceSpec("DEMO:NQ:book", "book:l2", "NQ", ("book_snapshot", "book_delta"), Tier.TRUE_DEPTH, sha256(b"demo-book").hexdigest(), sequence_policy="contiguous", origin="synthetic"),
        SourceSpec("DEMO:macro", "macro:vintage", "MACRO", ("schedule", "macro"), Tier.CANDLE_PROXY, sha256(b"demo-macro").hexdigest(), origin="synthetic"),
    ]
    for source in specs:
        store.register(source)
    inserted = []

    def add(source, event_id, kind, offset, payload, tier, *, seq=None, available_offset=None, published_offset=None):
        event_ns = START + offset * SECOND
        available_ns = START + (offset if available_offset is None else available_offset) * SECOND
        e = Observation(source, event_id, 1, kind, event_ns, available_ns, available_ns,
                        tier, payload, published_ns=START + published_offset * SECOND if published_offset is not None else None,
                        sequence=seq, quality_flags=("synthetic",), availability_basis="synthetic")
        inserted.append(store.append(e)["event_hash"])

    add("DEMO:macro", "scheduled-fomc", "schedule", 240,
        {"name": "Policy statement", "scheduled": True}, Tier.CANDLE_PROXY, available_offset=0)
    for i in range(6):
        close = 20124 + (0, 3, 8, 5, 13, 19)[i]
        add("DEMO:NQ:1m", f"nq-{i}", "bar", i * 60,
            {"open": close - 4, "high": close + 5, "low": close - 7, "close": close, "volume": 130 + i * 12}, Tier.CANDLE_PROXY,
            available_offset=i * 60 + 2)
        add("DEMO:ES:1m", f"es-{i}", "bar", i * 60,
            {"open": 5740 + i * 0.5, "high": 5742 + i * 0.5,
             "low": 5739 + i * 0.5, "close": 5741 + i * 0.5, "volume": 230 + i * 8}, Tier.CANDLE_PROXY,
            available_offset=i * 60 + 3)
    add("DEMO:NQ:book", "book-1", "book_snapshot", 170,
        {"bids": [[20128, 78], [20127.75, 112], [20127.5, 70]],
         "asks": [[20128.25, 62], [20128.5, 34], [20128.75, 85]]}, Tier.TRUE_DEPTH, seq=1, available_offset=171)
    add("DEMO:NQ:book", "book-2", "book_delta", 190,
        {"side": "bid", "price": 20127.75, "size": 152, "action": "set"}, Tier.TRUE_DEPTH, seq=2, available_offset=191)
    for i, side in enumerate(("buy", "buy", "sell", "buy", "sell"), start=1):
        add("DEMO:NQ:trades", f"trade-{i}", "trade", 172 + i * 8,
            {"price": 20128 + i * .25, "size": (4, 7, 3, 9, 2)[i - 1], "side": side},
            Tier.TRUE_TRADE, seq=i, available_offset=173 + i * 8)
    add("DEMO:macro", "fomc-release", "macro", 240,
        {"series": "policy_surprise", "value": .25, "vintage": "demo-v1"}, Tier.CANDLE_PROXY,
        available_offset=243, published_offset=240)
    decision_ns = START + 232 * SECOND
    before = store.asof(decision_ns, symbol="NQ")
    prediction = store.predict(decision_ns=decision_ns, horizon_ns=START + 360 * SECOND,
                               model_id="DEMO:watcher-v1", symbol="NQ", forecast=.54,
                               confidence=.58, abstain=False,
                               reason_codes=["synthetic_flow_pressure", "book_sequence_intact"],
                               evidence_hashes=[i["event_hash"] for i in before[-4:]],
                               frame_hash=frame(store, decision_ns)["frame_hash"])
    store.settle(prediction["prediction_id"], outcome_ns=START + 361 * SECOND,
                 realized_move=10.0, costs=1.5, slippage=.5, outcome_reference="synthetic-demo-outcome")
    return {"events": len(inserted), "prediction_id": prediction["prediction_id"],
            "label": "SYNTHETIC SCENE — no historical market or execution claim"}
