from __future__ import annotations

import pytest

from argus.causal_windows import (
    depth_window_asof,
    microstructure_snapshot_asof,
    trade_window_asof,
)
from argus.contracts import EvidenceTier
from argus.journal import EventJournal, JournalEvent, SourceContract


def trade_contract(source_id="trades", sequence_policy="monotone"):
    return SourceContract(
        source_id=source_id,
        max_evidence_tier=EvidenceTier.TRUE_TRADE,
        sequence_policy=sequence_policy,
        provider_reference="unit-test-provider",
        capability_reference="authenticated trades",
        allowed_kinds=("trade",),
        identity_verified=True,
        source_identity_reference="unit-test-provider-contract:v1",
    )


def depth_contract():
    return SourceContract(
        source_id="depth",
        max_evidence_tier=EvidenceTier.TRUE_DEPTH,
        sequence_policy="contiguous",
        provider_reference="unit-test-provider",
        capability_reference="authenticated mbp depth",
        allowed_kinds=("book_snapshot", "book_delta"),
        identity_verified=True,
        source_identity_reference="unit-test-depth-contract:v1",
    )


def trade(
    seq,
    event_ns,
    received_ns,
    *,
    price=100.0,
    size=1.0,
    side="buy",
    source_id="trades",
):
    return JournalEvent(
        source_id=source_id,
        kind="trade",
        event_time_ns=event_ns,
        received_time_ns=received_ns,
        sequence=seq,
        evidence_tier=EvidenceTier.TRUE_TRADE,
        payload={"price": price, "size": size, "side": side},
    )


def snapshot(
    seq,
    event_ns,
    received_ns,
    *,
    bids=((99.0, 5.0), (98.0, 3.0)),
    asks=((100.0, 4.0), (101.0, 2.0)),
    flags=(),
):
    return JournalEvent(
        source_id="depth",
        kind="book_snapshot",
        event_time_ns=event_ns,
        received_time_ns=received_ns,
        sequence=seq,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
        payload={
            "bids": [[price, size] for price, size in bids],
            "asks": [[price, size] for price, size in asks],
        },
        quality_flags=flags,
    )


def delta(seq, event_ns, received_ns, *, side="bid", action="set", price=99.0, size=7.0):
    return JournalEvent(
        source_id="depth",
        kind="book_delta",
        event_time_ns=event_ns,
        received_time_ns=received_ns,
        sequence=seq,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
        payload={"side": side, "action": action, "price": price, "size": size},
    )


def test_trade_window_is_receipt_time_causal_and_keeps_lineage(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    first = journal.append(trade(1, 10, 11, price=100.0, size=2.0, side="buy"))
    second = journal.append(trade(2, 20, 21, price=101.0, size=3.0, side="sell"))

    early = trade_window_asof(
        journal,
        source_id="trades",
        at_received_ns=20,
    )
    assert len(early.trades) == 1
    assert early.trades[0].price == 100.0
    assert early.latest_received_ns == 11
    assert early.source_row_sha256s == (first["row_sha256"],)

    later = trade_window_asof(
        journal,
        source_id="trades",
        at_received_ns=21,
    )
    assert [item.price for item in later.trades] == [100.0, 101.0]
    assert later.source_row_sha256s == (
        first["row_sha256"],
        second["row_sha256"],
    )


def test_trade_window_limit_is_applied_after_causal_cutoff(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    for seq in range(1, 5):
        journal.append(
            trade(
                seq,
                seq,
                seq,
                price=99.0 + seq,
                side="buy" if seq % 2 else "sell",
            )
        )

    window = trade_window_asof(
        journal,
        source_id="trades",
        at_received_ns=4,
        limit=2,
    )
    assert [item.sequence for item in window.trades] == [3, 4]
    assert len(window.source_row_sha256s) == 2


def test_unknown_aggressor_side_survives_as_unknown_for_flow_downgrade(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    journal.append(trade(1, 10, 10, side="unknown"))
    journal.append(trade(2, 11, 11, price=101.0, side="unknown"))

    window = trade_window_asof(
        journal,
        source_id="trades",
        at_received_ns=11,
    )
    assert [item.side for item in window.trades] == [None, None]

    journal.register(depth_contract())
    journal.append(snapshot(1, 10, 10))
    result = microstructure_snapshot_asof(
        journal,
        trade_source_id="trades",
        book_source_id="depth",
        at_received_ns=11,
        tick_size=1.0,
    )
    assert result.flow.evidence_tier is EvidenceTier.INFERRED_TRADE
    assert result.aggressive_runs
    assert result.aggressive_runs[0].evidence_tier is EvidenceTier.INFERRED_TRADE
    assert result.depth.evidence_tier is EvidenceTier.TRUE_DEPTH
    assert result.trade_latest_received_ns == 11
    assert result.depth_latest_received_ns == 10
    assert result.trade_staleness_ns == 0
    assert result.depth_staleness_ns == 1
    assert result.execution_authorized is False
    assert result.production_decision_authorized is False


def test_unsequenced_late_trade_fails_closed_instead_of_reordering(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract("late-trades", sequence_policy="none"))
    journal.append(
        trade(
            None,
            100,
            200,
            price=100.0,
            side="buy",
            source_id="late-trades",
        )
    )
    journal.append(
        trade(
            None,
            90,
            201,
            price=99.0,
            side="sell",
            source_id="late-trades",
        )
    )

    with pytest.raises(ValueError, match="late trade event"):
        trade_window_asof(
            journal,
            source_id="late-trades",
            at_received_ns=201,
        )


def test_depth_window_reconstructs_every_visible_state_and_lineage(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    first = journal.append(snapshot(1, 10, 11))
    second = journal.append(delta(2, 12, 13, price=99.0, size=7.0))

    window = depth_window_asof(
        journal,
        source_id="depth",
        at_received_ns=13,
    )

    assert len(window.snapshots) == 2
    assert window.snapshots[0].bids[0].size == 5.0
    assert window.snapshots[1].bids[0].size == 7.0
    assert window.latest_received_ns == 13
    assert window.source_row_sha256s == (
        first["row_sha256"],
        second["row_sha256"],
    )


def test_depth_lineage_tracks_only_dependencies_of_retained_states(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    first = journal.append(snapshot(1, 10, 11))
    journal.append(delta(2, 12, 13, price=99.0, size=7.0))
    replacement = journal.append(
        snapshot(
            3,
            14,
            15,
            bids=((99.0, 9.0),),
            asks=((100.0, 8.0),),
        )
    )

    window = depth_window_asof(
        journal,
        source_id="depth",
        at_received_ns=15,
        limit=1,
    )

    assert len(window.snapshots) == 1
    assert window.snapshots[0].sequence == 3
    assert window.source_row_sha256s == (replacement["row_sha256"],)
    assert first["row_sha256"] not in window.source_row_sha256s


def test_duplicate_raw_snapshot_levels_fail_closed_before_dict_collapse(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    journal.append(
        snapshot(
            1,
            10,
            11,
            bids=((99.0, 5.0), (99.0, 7.0)),
            asks=((100.0, 4.0),),
        )
    )

    with pytest.raises(ValueError, match="duplicate bid price"):
        depth_window_asof(
            journal,
            source_id="depth",
            at_received_ns=11,
        )


def test_depth_window_never_sees_future_delta(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    journal.append(snapshot(1, 10, 11))
    journal.append(delta(2, 20, 21, price=99.0, size=9.0))

    early = depth_window_asof(
        journal,
        source_id="depth",
        at_received_ns=20,
    )
    assert len(early.snapshots) == 1
    assert early.snapshots[-1].bids[0].size == 5.0


def test_unresolved_depth_gap_fails_closed_until_provider_recovery(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    journal.append(snapshot(1, 10, 11))
    journal.append(delta(3, 12, 13, price=99.0, size=8.0))

    with pytest.raises(ValueError, match="unresolved source sequence gap"):
        depth_window_asof(
            journal,
            source_id="depth",
            at_received_ns=13,
        )

    recovery = journal.append(
        snapshot(
            4,
            14,
            15,
            bids=((99.0, 6.0),),
            asks=((100.0, 5.0),),
            flags=("provider_recovery",),
        )
    )
    recovered = depth_window_asof(
        journal,
        source_id="depth",
        at_received_ns=15,
    )
    assert len(recovered.snapshots) == 1
    assert recovered.snapshots[0].sequence == 4
    assert recovered.source_row_sha256s == (recovery["row_sha256"],)


def test_provider_recovery_resets_history_even_without_observed_gap(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    journal.append(snapshot(1, 10, 11))
    journal.append(delta(2, 12, 13, price=99.0, size=7.0))
    recovery = journal.append(
        snapshot(
            3,
            14,
            15,
            bids=((99.0, 6.0),),
            asks=((100.0, 5.0),),
            flags=("provider_recovery",),
        )
    )
    after = journal.append(delta(4, 16, 17, price=99.0, size=8.0))

    window = depth_window_asof(
        journal,
        source_id="depth",
        at_received_ns=17,
    )

    assert [item.sequence for item in window.snapshots] == [3, 4]
    assert window.snapshots[0].bids[0].size == 6.0
    assert window.snapshots[1].bids[0].size == 8.0
    assert window.source_row_sha256s == (
        recovery["row_sha256"],
        after["row_sha256"],
    )


def test_depth_delta_without_baseline_snapshot_is_not_silently_promoted(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    journal.append(delta(1, 10, 11))

    with pytest.raises(ValueError, match="no reconstructable depth snapshot"):
        depth_window_asof(
            journal,
            source_id="depth",
            at_received_ns=11,
        )


def test_crossed_reconstructed_book_fails_closed(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(depth_contract())
    journal.append(snapshot(1, 10, 11))
    journal.append(delta(2, 12, 13, side="bid", price=100.0, size=1.0))

    with pytest.raises(ValueError, match="crossed or locked"):
        depth_window_asof(
            journal,
            source_id="depth",
            at_received_ns=13,
        )


def test_microstructure_snapshot_binds_feature_evidence_to_journal_rows(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    journal.register(depth_contract())

    t1 = journal.append(trade(1, 10, 11, price=100.0, size=2.0, side="buy"))
    t2 = journal.append(trade(2, 12, 13, price=101.0, size=1.0, side="buy"))
    d1 = journal.append(snapshot(1, 10, 11))
    d2 = journal.append(delta(2, 12, 13, price=99.0, size=7.0))

    result = microstructure_snapshot_asof(
        journal,
        trade_source_id="trades",
        book_source_id="depth",
        at_received_ns=13,
        tick_size=1.0,
        depth_levels=2,
    )

    assert result.flow.evidence_tier is EvidenceTier.TRUE_TRADE
    assert len(result.aggressive_runs) == 1
    assert result.aggressive_runs[0].side == 1
    assert result.aggressive_runs[0].trade_count == 2
    assert result.aggressive_runs[0].evidence_tier is EvidenceTier.TRUE_TRADE
    assert len(result.depth.bid_depth_by_tick) == 2
    assert len(result.depth.ask_depth_by_tick) == 2
    assert result.depth.evidence_tier is EvidenceTier.TRUE_DEPTH
    assert result.liquidity.evidence_tier is EvidenceTier.TRUE_DEPTH
    assert result.liquidity.near_ticks == 2
    assert result.flow.event_time_ns == 12
    assert result.depth.event_time_ns == 12
    assert result.trade_row_sha256s == (
        t1["row_sha256"],
        t2["row_sha256"],
    )
    assert result.depth_row_sha256s == (
        d1["row_sha256"],
        d2["row_sha256"],
    )
    assert result.trade_latest_received_ns == 13
    assert result.depth_latest_received_ns == 13
    assert result.trade_staleness_ns == 0
    assert result.depth_staleness_ns == 0
    assert result.execution_authorized is False
    assert result.production_decision_authorized is False


@pytest.mark.parametrize("limit", [0, -1, True])
def test_invalid_window_limits_fail_closed(tmp_path, limit):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    journal.append(trade(1, 10, 11))
    with pytest.raises(ValueError, match="positive integer"):
        trade_window_asof(
            journal,
            source_id="trades",
            at_received_ns=11,
            limit=limit,
        )


@pytest.mark.parametrize("depth_levels", [0, -1, True, None])
def test_invalid_depth_levels_fail_closed(tmp_path, depth_levels):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    journal.register(depth_contract())
    journal.append(trade(1, 10, 11))
    journal.append(snapshot(1, 10, 11))

    with pytest.raises(ValueError, match="depth_levels"):
        microstructure_snapshot_asof(
            journal,
            trade_source_id="trades",
            book_source_id="depth",
            at_received_ns=11,
            tick_size=1.0,
            depth_levels=depth_levels,
        )


def test_inference_control_requires_boolean(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    journal.register(depth_contract())
    journal.append(trade(1, 10, 11))
    journal.append(snapshot(1, 10, 11))

    with pytest.raises(TypeError, match="allow_inferred_trade_side"):
        microstructure_snapshot_asof(
            journal,
            trade_source_id="trades",
            book_source_id="depth",
            at_received_ns=11,
            tick_size=1.0,
            allow_inferred_trade_side="yes",
        )


def test_causal_snapshot_exposes_configurable_liquidity_near_window(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    journal.register(depth_contract())
    journal.append(trade(1, 10, 11))
    journal.append(
        snapshot(
            1,
            10,
            11,
            bids=((99.0, 5.0), (98.0, 3.0), (97.0, 2.0)),
            asks=((100.0, 4.0), (101.0, 3.0), (102.0, 3.0)),
        )
    )

    result = microstructure_snapshot_asof(
        journal,
        trade_source_id="trades",
        book_source_id="depth",
        at_received_ns=11,
        tick_size=1.0,
        depth_levels=3,
        liquidity_near_ticks=1,
    )

    assert result.liquidity.near_ticks == 1
    assert result.liquidity.bid_near_touch_depth == pytest.approx(5.0)
    assert result.liquidity.ask_near_touch_depth == pytest.approx(4.0)


def test_invalid_liquidity_near_window_fails_closed(tmp_path):
    journal = EventJournal(tmp_path / "argus.sqlite3")
    journal.register(trade_contract())
    journal.register(depth_contract())
    journal.append(trade(1, 10, 11))
    journal.append(snapshot(1, 10, 11))

    with pytest.raises(ValueError, match="near_ticks"):
        microstructure_snapshot_asof(
            journal,
            trade_source_id="trades",
            book_source_id="depth",
            at_received_ns=11,
            tick_size=1.0,
            depth_levels=2,
            liquidity_near_ticks=3,
        )
