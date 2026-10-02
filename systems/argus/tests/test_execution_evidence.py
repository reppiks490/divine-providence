from __future__ import annotations

from dataclasses import replace

import pytest

from argus.contracts import BookLevel, BookSnapshot
from argus.execution_evidence import (
    ExecutionEvidenceKind,
    calibrate_lineaged_impact,
    calibration_by_execution_evidence,
    create_execution_evidence_receipt,
    receipt_from_icarus_journal_fill,
    receipt_from_icarus_paper_fill,
    validate_execution_evidence_receipt,
)
from argus.impact import depth_impact_curve


ICARUS_COMMIT = "599525174cab64d88df81206d1fcb2c3234e9d16"
BROKER_COMMIT = "a" * 40


def curve(side=1):
    book = BookSnapshot(
        event_time_ns=100_000_000_000,
        sequence=7,
        bids=(BookLevel(99.0, 10.0), BookLevel(98.0, 20.0)),
        asks=(BookLevel(101.0, 8.0), BookLevel(102.0, 20.0)),
    )
    return depth_impact_curve(
        book,
        side=side,
        sizes=(5.0, 15.0),
        tick_size=1.0,
        capacity_threshold_ticks=(0.0, 1.0),
    )


def broker_receipt(execution_id="broker-fill-1", *, side=1):
    return create_execution_evidence_receipt(
        evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
        source_system="example-broker",
        source_repo="broker/example-adapter",
        source_commit=BROKER_COMMIT,
        source_run_id="session-1",
        source_execution_id=execution_id,
        symbol="NQ",
        decision_time_ns=105_000_000_000,
        completion_time_ns=110_000_000_000,
        observed_time_ns=111_000_000_000,
        side=side,
        requested_size=5.0,
        filled_size=5.0,
        average_price=101.5 if side == 1 else 98.5,
        source_payload={
            "order_id": "order-1",
            "fill_id": execution_id,
            "qty": 5,
        },
        broker_name="Example Broker",
        broker_order_id="order-1",
        broker_fill_id=execution_id,
    )


def paper_fill(*, live=True):
    return {
        "ts": 110,
        "bar": 42,
        "id": "TrendL",
        "side": "buy",
        "qty": 5,
        "price": 101.25,
        "kind": "entry",
        "comment": "TrendL",
        "profit": None,
        "pos": 5,
        "live": live,
    }


def journal_fill(*, row_id=17, run_id=1_700_000_000, live=1):
    return {
        "id": row_id,
        "run_id": run_id,
        "live": live,
        "symbol": "NQ",
        "ts": 110,
        "entry_id": "TrendL",
        "side": "buy",
        "qty": 5,
        "price": 101.25,
        "kind": "entry",
        "comment": "TrendL",
        "profit": None,
        "position_after": 5,
    }


def paper_receipt(*, live=True):
    return receipt_from_icarus_paper_fill(
        paper_fill(live=live),
        source_commit=ICARUS_COMMIT,
        source_run_id="icarus-run-123",
        symbol="NQ",
        decision_time_ns=105_000_000_000,
        observed_time_ns=111_000_000_000,
    )


def test_broker_receipt_is_content_addressed_and_confirmed():
    first = broker_receipt()
    second = broker_receipt()

    assert first == second
    assert first.receipt_id.startswith("execution-evidence:")
    assert first.evidence_kind is ExecutionEvidenceKind.BROKER_CONFIRMED
    assert first.market_fill_confirmed is True
    assert first.broker_confirmed is True
    assert first.broker_name == "Example Broker"
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    validate_execution_evidence_receipt(first)


def test_broker_receipt_requires_full_broker_lineage():
    kwargs = dict(
        evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
        source_system="example-broker",
        source_repo="broker/example-adapter",
        source_commit=BROKER_COMMIT,
        source_run_id="session-1",
        source_execution_id="fill-1",
        symbol="NQ",
        decision_time_ns=105,
        completion_time_ns=110,
        observed_time_ns=111,
        side=1,
        requested_size=5.0,
        filled_size=5.0,
        average_price=101.5,
        source_payload={"fill": 1},
        broker_name="Example Broker",
        broker_order_id="order-1",
        broker_fill_id=None,
    )
    with pytest.raises(ValueError, match="requires broker_name"):
        create_execution_evidence_receipt(**kwargs)


def test_icarus_live_epoch_fill_remains_paper_emulator_evidence():
    receipt = paper_receipt(live=True)

    assert receipt.evidence_kind is ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
    assert receipt.source_system == "icarus-paper-emulator"
    assert receipt.source_repo == "reppiks490/Icarus"
    assert receipt.completion_time_ns == 110_000_000_000
    assert receipt.market_fill_confirmed is False
    assert receipt.broker_confirmed is False
    assert receipt.broker_name is None
    assert receipt.broker_order_id is None
    assert receipt.broker_fill_id is None
    validate_execution_evidence_receipt(receipt)


def test_icarus_paper_adapter_requires_decision_time_instead_of_inventing_it():
    with pytest.raises(ValueError, match="completion_time_ns"):
        receipt_from_icarus_paper_fill(
            paper_fill(),
            source_commit=ICARUS_COMMIT,
            source_run_id="icarus-run-123",
            symbol="NQ",
            decision_time_ns=111_000_000_000,
            observed_time_ns=112_000_000_000,
        )


def test_icarus_journal_fill_adapter_matches_durable_schema_and_stays_paper():
    receipt = receipt_from_icarus_journal_fill(
        journal_fill(),
        source_commit=ICARUS_COMMIT,
        decision_time_ns=105_000_000_000,
        observed_time_ns=111_000_000_000,
    )

    assert receipt.evidence_kind is ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
    assert receipt.source_system == "icarus-paper-emulator"
    assert receipt.source_repo == "reppiks490/Icarus"
    assert receipt.source_run_id == "1700000000"
    assert receipt.source_execution_id.startswith("icarus-journal-fill:")
    assert receipt.completion_time_ns == 110_000_000_000
    assert receipt.symbol == "NQ"
    assert receipt.side == 1
    assert receipt.requested_size == 5.0
    assert receipt.filled_size == 5.0
    assert receipt.average_price == 101.25
    assert receipt.market_fill_confirmed is False
    assert receipt.broker_confirmed is False
    validate_execution_evidence_receipt(receipt)


def test_icarus_journal_fill_identity_uses_durable_unique_index_semantics():
    first = receipt_from_icarus_journal_fill(
        journal_fill(row_id=17),
        source_commit=ICARUS_COMMIT,
        decision_time_ns=105_000_000_000,
        observed_time_ns=111_000_000_000,
    )
    replayed_representation = receipt_from_icarus_journal_fill(
        {
            **journal_fill(row_id=99),
            "profit": 12.5,
        },
        source_commit=ICARUS_COMMIT,
        decision_time_ns=105_000_000_000,
        observed_time_ns=112_000_000_000,
    )

    assert first.receipt_id != replayed_representation.receipt_id
    assert (
        first.source_execution_id
        == replayed_representation.source_execution_id
    )

    rows = (
        calibrate_lineaged_impact(curve(), first),
        calibrate_lineaged_impact(curve(), replayed_representation),
    )
    with pytest.raises(
        ValueError,
        match="duplicate source execution identity",
    ):
        calibration_by_execution_evidence(rows)


def test_icarus_journal_adapter_rejects_legacy_or_invented_provenance():
    with pytest.raises(ValueError, match="legacy run_id=0"):
        receipt_from_icarus_journal_fill(
            journal_fill(run_id=0),
            source_commit=ICARUS_COMMIT,
            decision_time_ns=105_000_000_000,
            observed_time_ns=111_000_000_000,
        )

    with pytest.raises(ValueError, match="completion_time_ns"):
        receipt_from_icarus_journal_fill(
            journal_fill(),
            source_commit=ICARUS_COMMIT,
            decision_time_ns=111_000_000_000,
            observed_time_ns=112_000_000_000,
        )

    malformed = dict(journal_fill())
    malformed["bar"] = 42
    with pytest.raises(ValueError, match="journal fill requires exactly"):
        receipt_from_icarus_journal_fill(
            malformed,
            source_commit=ICARUS_COMMIT,
            decision_time_ns=105_000_000_000,
            observed_time_ns=111_000_000_000,
        )


def test_icarus_journal_adapter_does_not_accept_closed_trade_rows_as_fills():
    trade_row = {
        "id": 17,
        "run_id": 1_700_000_000,
        "live": 1,
        "symbol": "NQ",
        "entry_id": "TrendL",
        "direction": 1,
        "qty": 5,
        "entry_price": 101.0,
        "entry_ts": 105,
        "exit_price": 101.25,
        "exit_ts": 110,
        "exit_comment": "TP",
        "profit": 12.5,
        "piece": 0,
        "lot_id": 9,
        "entry_qty": 5,
        "strategy_fingerprint": "a" * 64,
        "strategy_context_json": "{}",
    }

    with pytest.raises(ValueError, match="journal fill requires exactly"):
        receipt_from_icarus_journal_fill(
            trade_row,
            source_commit=ICARUS_COMMIT,
            decision_time_ns=105_000_000_000,
            observed_time_ns=111_000_000_000,
        )


def test_paper_receipt_cannot_claim_broker_lineage():
    with pytest.raises(ValueError, match="cannot carry broker"):
        create_execution_evidence_receipt(
            evidence_kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            source_system="icarus-paper-emulator",
            source_repo="reppiks490/Icarus",
            source_commit=ICARUS_COMMIT,
            source_run_id="run",
            source_execution_id="fill",
            symbol="NQ",
            decision_time_ns=105,
            completion_time_ns=110,
            observed_time_ns=111,
            side=1,
            requested_size=1.0,
            filled_size=1.0,
            average_price=101.0,
            source_payload={"fill": 1},
            broker_name="Not Allowed",
        )


def test_receipt_tampering_fails_closed():
    receipt = broker_receipt()

    with pytest.raises(ValueError, match="receipt_id"):
        validate_execution_evidence_receipt(
            replace(receipt, requested_size=6.0)
        )

    with pytest.raises(ValueError, match="flags"):
        validate_execution_evidence_receipt(
            replace(receipt, broker_confirmed=False)
        )


def test_lineaged_calibration_keeps_broker_and_paper_evidence_separate():
    broker = calibrate_lineaged_impact(
        curve(),
        broker_receipt(),
    )
    paper = calibrate_lineaged_impact(
        curve(),
        paper_receipt(),
    )

    assert broker.receipt.market_fill_confirmed is True
    assert broker.lineage_id.startswith("impact-calibration-lineage:")
    assert broker.calibration.execution_id == broker.receipt.receipt_id
    assert broker.calibration.snapshot_age_ns == 5_000_000_000
    assert broker.calibration.completion_latency_ns == 5_000_000_000

    assert paper.receipt.market_fill_confirmed is False
    assert paper.calibration.execution_id == paper.receipt.receipt_id

    strata = calibration_by_execution_evidence((broker, paper))
    assert [row.evidence_kind for row in strata] == [
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    ]
    assert [row.observations for row in strata] == [1, 1]
    assert strata[0].broker_confirmed is True
    assert strata[1].broker_confirmed is False


def test_lineaged_summary_rejects_duplicate_source_execution_identity():
    first_receipt = broker_receipt("broker-fill-1")
    second_receipt = create_execution_evidence_receipt(
        evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
        source_system="example-broker",
        source_repo="broker/example-adapter",
        source_commit=BROKER_COMMIT,
        source_run_id="session-1",
        source_execution_id="broker-fill-1",
        symbol="NQ",
        decision_time_ns=105_000_000_000,
        completion_time_ns=110_000_000_000,
        observed_time_ns=111_000_000_000,
        side=1,
        requested_size=5.0,
        filled_size=5.0,
        average_price=101.75,
        source_payload={
            "order_id": "order-1",
            "fill_id": "broker-fill-1",
            "qty": 5,
            "representation_revision": 2,
        },
        broker_name="Example Broker",
        broker_order_id="order-1",
        broker_fill_id="broker-fill-1",
    )
    assert first_receipt.receipt_id != second_receipt.receipt_id

    first = calibrate_lineaged_impact(curve(), first_receipt)
    second = calibrate_lineaged_impact(curve(), second_receipt)

    with pytest.raises(ValueError, match="duplicate source execution identity"):
        calibration_by_execution_evidence((first, second))


def test_source_execution_identity_is_symbol_scoped():
    nq_receipt = broker_receipt("broker-fill-1")
    es_receipt = create_execution_evidence_receipt(
        evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
        source_system="example-broker",
        source_repo="broker/example-adapter",
        source_commit=BROKER_COMMIT,
        source_run_id="session-1",
        source_execution_id="broker-fill-1",
        symbol="ES",
        decision_time_ns=105_000_000_000,
        completion_time_ns=110_000_000_000,
        observed_time_ns=111_000_000_000,
        side=1,
        requested_size=5.0,
        filled_size=5.0,
        average_price=101.5,
        source_payload={
            "order_id": "order-es-1",
            "fill_id": "broker-fill-1",
            "qty": 5,
            "symbol": "ES",
        },
        broker_name="Example Broker",
        broker_order_id="order-es-1",
        broker_fill_id="broker-fill-1",
    )

    rows = (
        calibrate_lineaged_impact(curve(), nq_receipt),
        calibrate_lineaged_impact(curve(), es_receipt),
    )
    strata = calibration_by_execution_evidence(rows)

    assert len(strata) == 1
    assert strata[0].observations == 2


def test_lineaged_summary_rejects_duplicate_or_tampered_links():
    row = calibrate_lineaged_impact(curve(), broker_receipt())

    with pytest.raises(ValueError, match="duplicate receipt_id"):
        calibration_by_execution_evidence((row, row))

    bad_execution_id = replace(
        row,
        calibration=replace(
            row.calibration,
            execution_id="not-the-receipt",
        ),
    )
    with pytest.raises(ValueError, match="lineage_id"):
        calibration_by_execution_evidence((bad_execution_id,))

    bad_fraction = replace(
        row,
        calibration=replace(
            row.calibration,
            realized_fill_fraction=0.5,
        ),
    )
    with pytest.raises(ValueError, match="lineage_id"):
        calibration_by_execution_evidence((bad_fraction,))


def test_icarus_fill_shape_is_exact_and_live_flag_is_boolean():
    bad = dict(paper_fill())
    bad["unexpected"] = 1
    with pytest.raises(ValueError, match="requires exactly"):
        receipt_from_icarus_paper_fill(
            bad,
            source_commit=ICARUS_COMMIT,
            source_run_id="run",
            symbol="NQ",
            decision_time_ns=105_000_000_000,
            observed_time_ns=111_000_000_000,
        )

    bad_live = dict(paper_fill())
    bad_live["live"] = 1
    with pytest.raises(TypeError, match="fill live"):
        receipt_from_icarus_paper_fill(
            bad_live,
            source_commit=ICARUS_COMMIT,
            source_run_id="run",
            symbol="NQ",
            decision_time_ns=105_000_000_000,
            observed_time_ns=111_000_000_000,
        )


def test_lineaged_calibration_identity_changes_with_execution_evidence():
    first = calibrate_lineaged_impact(curve(), broker_receipt("broker-fill-1"))
    second = calibrate_lineaged_impact(curve(), broker_receipt("broker-fill-2"))

    assert first.receipt.receipt_id != second.receipt.receipt_id
    assert first.lineage_id != second.lineage_id
