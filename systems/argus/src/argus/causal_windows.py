from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bookmap import DepthDynamics, depth_dynamics
from .contracts import BookLevel, BookSnapshot, EvidenceTier, Trade
from .flow_dynamics import FlowDynamics, flow_dynamics
from .journal import EventJournal
from .liquidity_field import LiquidityField, liquidity_field


@dataclass(frozen=True)
class TradeWindow:
    source_id: str
    at_received_ns: int
    latest_received_ns: int
    trades: tuple[Trade, ...]
    source_row_sha256s: tuple[str, ...]


@dataclass(frozen=True)
class DepthWindow:
    source_id: str
    at_received_ns: int
    latest_received_ns: int
    snapshots: tuple[BookSnapshot, ...]
    source_row_sha256s: tuple[str, ...]


@dataclass(frozen=True)
class CausalMicrostructureSnapshot:
    at_received_ns: int
    trade_source_id: str
    book_source_id: str
    flow: FlowDynamics
    depth: DepthDynamics
    liquidity: LiquidityField
    trade_latest_received_ns: int
    depth_latest_received_ns: int
    trade_staleness_ns: int
    depth_staleness_ns: int
    trade_row_sha256s: tuple[str, ...]
    depth_row_sha256s: tuple[str, ...]
    execution_authorized: bool = False
    production_decision_authorized: bool = False


def _positive_limit(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer or None")
    return value


def _causal_rows(
    journal: EventJournal,
    *,
    source_id: str,
    at_received_ns: int,
) -> list[dict[str, Any]]:
    rows = journal.events_asof(at_received_ns, source_id=source_id)
    if not rows:
        return []

    gap_active = False
    start = 0
    for index, row in enumerate(rows):
        if int(row["gap_before"]) > 0:
            gap_active = True
        body = row["body"]
        if (
            body["kind"] == "book_snapshot"
            and "provider_recovery" in tuple(body.get("quality_flags", ()))
        ):
            gap_active = False
            start = index

    if gap_active:
        raise ValueError("unresolved source sequence gap at decision time")
    return rows[start:]


def trade_window_asof(
    journal: EventJournal,
    *,
    source_id: str,
    at_received_ns: int,
    limit: int | None = None,
) -> TradeWindow:
    """Return receipt-time-causal authenticated trade prints.

    Rows are never reordered. A late event-time print on an unsequenced source
    therefore fails closed instead of being silently sorted into the past.
    """

    limit = _positive_limit("limit", limit)
    rows = _causal_rows(
        journal,
        source_id=source_id,
        at_received_ns=at_received_ns,
    )
    trade_rows = [row for row in rows if row["kind"] == "trade"]
    if not trade_rows:
        raise ValueError("no trade events available by decision time")
    if limit is not None:
        trade_rows = trade_rows[-limit:]

    previous_event_ns: int | None = None
    trades: list[Trade] = []
    for row in trade_rows:
        if row["evidence_tier"] != EvidenceTier.TRUE_TRADE.name:
            raise ValueError("journal trade row is not TRUE_TRADE evidence")
        body = row["body"]
        event_ns = int(body["event_time_ns"])
        if previous_event_ns is not None and event_ns < previous_event_ns:
            raise ValueError(
                "late trade event prevents a monotone event-time flow window"
            )
        previous_event_ns = event_ns

        payload = body["payload"]
        raw_side = payload.get("side", "unknown")
        side = 1 if raw_side == "buy" else -1 if raw_side == "sell" else None
        sequence = body.get("sequence")
        trades.append(
            Trade(
                event_time_ns=event_ns,
                price=float(payload["price"]),
                size=float(payload["size"]),
                side=side,
                sequence=int(sequence) if sequence is not None else 0,
            )
        )

    return TradeWindow(
        source_id=source_id,
        at_received_ns=at_received_ns,
        latest_received_ns=int(trade_rows[-1]["received_time_ns"]),
        trades=tuple(trades),
        source_row_sha256s=tuple(str(row["row_sha256"]) for row in trade_rows),
    )


def _book_snapshot(
    *,
    event_time_ns: int,
    sequence: int,
    bids: dict[float, float],
    asks: dict[float, float],
) -> BookSnapshot:
    bid_levels = tuple(
        BookLevel(price, size)
        for price, size in sorted(bids.items(), reverse=True)
        if size > 0
    )
    ask_levels = tuple(
        BookLevel(price, size)
        for price, size in sorted(asks.items())
        if size > 0
    )
    if not bid_levels or not ask_levels:
        raise ValueError("reconstructed depth is empty on one side")
    if bid_levels[0].price >= ask_levels[0].price:
        raise ValueError("reconstructed depth is crossed or locked")
    return BookSnapshot(
        event_time_ns=event_time_ns,
        bids=bid_levels,
        asks=ask_levels,
        sequence=sequence,
    )


def depth_window_asof(
    journal: EventJournal,
    *,
    source_id: str,
    at_received_ns: int,
    limit: int | None = None,
) -> DepthWindow:
    """Reconstruct a receipt-time-causal book-state history.

    Every valid snapshot or delta after the active reconstruction baseline emits
    one derived BookSnapshot. Unresolved source gaps fail closed. A provider
    recovery snapshot starts a new valid reconstruction segment.
    """

    limit = _positive_limit("limit", limit)
    rows = _causal_rows(
        journal,
        source_id=source_id,
        at_received_ns=at_received_ns,
    )
    book_rows = [
        row
        for row in rows
        if row["kind"] in ("book_snapshot", "book_delta")
    ]
    if not book_rows:
        raise ValueError("no depth events available by decision time")

    bids: dict[float, float] = {}
    asks: dict[float, float] = {}
    have_snapshot = False
    snapshots: list[BookSnapshot] = []
    snapshot_dependencies: list[tuple[str, ...]] = []
    active_hashes: list[str] = []
    latest_received_ns: int | None = None

    for row in book_rows:
        if row["evidence_tier"] != EvidenceTier.TRUE_DEPTH.name:
            raise ValueError("journal depth row is not TRUE_DEPTH evidence")
        body = row["body"]
        payload = body["payload"]

        if body["kind"] == "book_snapshot":
            bid_pairs = [(float(price), float(size)) for price, size in payload["bids"]]
            ask_pairs = [(float(price), float(size)) for price, size in payload["asks"]]
            if len({price for price, _ in bid_pairs}) != len(bid_pairs):
                raise ValueError("duplicate bid price in raw depth snapshot")
            if len({price for price, _ in ask_pairs}) != len(ask_pairs):
                raise ValueError("duplicate ask price in raw depth snapshot")
            bids = dict(bid_pairs)
            asks = dict(ask_pairs)
            have_snapshot = True
            active_hashes = [str(row["row_sha256"])]
        else:
            if not have_snapshot:
                continue
            side = payload["side"]
            levels = bids if side == "bid" else asks
            price = float(payload["price"])
            size = float(payload["size"])
            if payload["action"] == "delete" or size == 0:
                levels.pop(price, None)
            else:
                levels[price] = size
            active_hashes.append(str(row["row_sha256"]))

        if not have_snapshot:
            continue
        sequence = body.get("sequence")
        if sequence is None:
            raise ValueError("book reconstruction requires source sequence")
        snapshots.append(
            _book_snapshot(
                event_time_ns=int(body["event_time_ns"]),
                sequence=int(sequence),
                bids=bids,
                asks=asks,
            )
        )
        snapshot_dependencies.append(tuple(active_hashes))
        latest_received_ns = int(row["received_time_ns"])

    if not snapshots or latest_received_ns is None:
        raise ValueError("no reconstructable depth snapshot available by decision time")

    if limit is not None:
        snapshots = snapshots[-limit:]
        snapshot_dependencies = snapshot_dependencies[-limit:]

    lineage: list[str] = []
    seen_hashes: set[str] = set()
    for dependencies in snapshot_dependencies:
        for row_hash in dependencies:
            if row_hash not in seen_hashes:
                lineage.append(row_hash)
                seen_hashes.add(row_hash)

    return DepthWindow(
        source_id=source_id,
        at_received_ns=at_received_ns,
        latest_received_ns=latest_received_ns,
        snapshots=tuple(snapshots),
        source_row_sha256s=tuple(lineage),
    )


def microstructure_snapshot_asof(
    journal: EventJournal,
    *,
    trade_source_id: str,
    book_source_id: str,
    at_received_ns: int,
    tick_size: float,
    trade_limit: int | None = 256,
    depth_limit: int | None = 64,
    depth_levels: int = 10,
    liquidity_near_ticks: int | None = None,
    allow_inferred_trade_side: bool = True,
) -> CausalMicrostructureSnapshot:
    """Build the current ARGUS feature pair from receipt-time journal evidence."""

    validated_depth_levels = _positive_limit("depth_levels", depth_levels)
    if validated_depth_levels is None:
        raise ValueError("depth_levels must be a positive integer")
    if type(allow_inferred_trade_side) is not bool:
        raise TypeError("allow_inferred_trade_side must be bool")

    trades = trade_window_asof(
        journal,
        source_id=trade_source_id,
        at_received_ns=at_received_ns,
        limit=trade_limit,
    )
    depth = depth_window_asof(
        journal,
        source_id=book_source_id,
        at_received_ns=at_received_ns,
        limit=depth_limit,
    )

    flow = flow_dynamics(
        list(trades.trades),
        tick_size=tick_size,
        allow_inferred=allow_inferred_trade_side,
    )
    depth_features = depth_dynamics(
        list(depth.snapshots),
        tick_size=tick_size,
        levels=validated_depth_levels,
    )
    near_ticks = (
        min(3, validated_depth_levels)
        if liquidity_near_ticks is None
        else liquidity_near_ticks
    )
    liquidity = liquidity_field(
        depth_features,
        near_ticks=near_ticks,
    )

    return CausalMicrostructureSnapshot(
        at_received_ns=at_received_ns,
        trade_source_id=trade_source_id,
        book_source_id=book_source_id,
        flow=flow,
        depth=depth_features,
        liquidity=liquidity,
        trade_latest_received_ns=trades.latest_received_ns,
        depth_latest_received_ns=depth.latest_received_ns,
        trade_staleness_ns=at_received_ns - trades.latest_received_ns,
        depth_staleness_ns=at_received_ns - depth.latest_received_ns,
        trade_row_sha256s=trades.source_row_sha256s,
        depth_row_sha256s=depth.source_row_sha256s,
        execution_authorized=False,
        production_decision_authorized=False,
    )
