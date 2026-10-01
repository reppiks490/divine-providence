from __future__ import annotations

from dataclasses import replace

import pytest

from argus.contracts import BookLevel, BookSnapshot
from argus.execution_evidence import (
    ExecutionEvidenceKind,
    calibrate_lineaged_impact,
    calibration_by_execution_evidence,
    create_execution_evidence_receipt,
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
    with pytest.raises(ValueError, match="execution_id"):
        calibration_by_execution_evidence((bad_execution_id,))

    bad_fraction = replace(
        row,
        calibration=replace(
            row.calibration,
            realized_fill_fraction=0.5,
        ),
    )
    with pytest.raises(ValueError, match="realized fill fraction"):
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
