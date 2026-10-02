from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

from .impact import DepthImpactCurve
from .impact_calibration import (
    ImpactCalibrationObservation,
    ImpactCalibrationSummary,
    RealizedExecution,
    calibrate_impact,
    summarize_impact_calibration,
)


class ExecutionEvidenceKind(str, Enum):
    BROKER_CONFIRMED = "BROKER_CONFIRMED"
    ICARUS_PAPER_EMULATOR = "ICARUS_PAPER_EMULATOR"


@dataclass(frozen=True)
class ExecutionEvidenceReceipt:
    receipt_id: str
    evidence_kind: ExecutionEvidenceKind
    source_system: str
    source_repo: str
    source_commit: str
    source_run_id: str
    source_execution_id: str
    symbol: str
    decision_time_ns: int
    completion_time_ns: int
    observed_time_ns: int
    side: int
    requested_size: float
    filled_size: float
    average_price: float | None
    source_payload_sha256: str
    broker_name: str | None
    broker_order_id: str | None
    broker_fill_id: str | None
    market_fill_confirmed: bool
    broker_confirmed: bool
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class LineagedImpactCalibrationObservation:
    lineage_id: str
    receipt: ExecutionEvidenceReceipt
    calibration: ImpactCalibrationObservation
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class ImpactCalibrationEvidenceStratum:
    evidence_kind: ExecutionEvidenceKind
    market_fill_confirmed: bool
    broker_confirmed: bool
    observations: int
    summary: ImpactCalibrationSummary


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as ex:
        raise ValueError("source_payload must be canonical JSON data") from ex


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(name: str, value: str, *, max_len: int = 240) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    if len(value) > max_len:
        raise ValueError(f"{name} exceeds {max_len} characters")
    return value


def _sha40(name: str, value: str) -> str:
    out = _text(name, value, max_len=40)
    if len(out) != 40 or any(ch not in "0123456789abcdef" for ch in out):
        raise ValueError(f"{name} must be an exact 40-character lowercase hex SHA")
    return out


def _nonnegative_ns(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _positive(name: str, value: float) -> float:
    out = _finite(name, value)
    if out <= 0:
        raise ValueError(f"{name} must be positive")
    return out


def _nonnegative(name: str, value: float) -> float:
    out = _finite(name, value)
    if out < 0:
        raise ValueError(f"{name} must be non-negative")
    return out


def _optional_text(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _text(name, value)


def create_execution_evidence_receipt(
    *,
    evidence_kind: ExecutionEvidenceKind,
    source_system: str,
    source_repo: str,
    source_commit: str,
    source_run_id: str,
    source_execution_id: str,
    symbol: str,
    decision_time_ns: int,
    completion_time_ns: int,
    observed_time_ns: int,
    side: int,
    requested_size: float,
    filled_size: float,
    average_price: float | None,
    source_payload: Mapping[str, Any],
    broker_name: str | None = None,
    broker_order_id: str | None = None,
    broker_fill_id: str | None = None,
) -> ExecutionEvidenceReceipt:
    """Create a content-addressed execution-evidence receipt.

    BROKER_CONFIRMED means an external broker/exchange execution confirmation.
    ICARUS_PAPER_EMULATOR is explicitly simulation evidence even when the engine
    processed the bar during a live market session.
    """

    if not isinstance(evidence_kind, ExecutionEvidenceKind):
        raise TypeError("evidence_kind must be ExecutionEvidenceKind")

    system = _text("source_system", source_system)
    repo = _text("source_repo", source_repo)
    if "/" not in repo:
        raise ValueError("source_repo must be owner/repository")
    commit = _sha40("source_commit", source_commit)
    run_id = _text("source_run_id", source_run_id)
    execution_id = _text("source_execution_id", source_execution_id)
    asset = _text("symbol", symbol, max_len=64).upper()

    decision = _nonnegative_ns("decision_time_ns", decision_time_ns)
    completion = _nonnegative_ns("completion_time_ns", completion_time_ns)
    observed = _nonnegative_ns("observed_time_ns", observed_time_ns)
    if completion < decision:
        raise ValueError("completion_time_ns cannot precede decision_time_ns")
    if observed < completion:
        raise ValueError("observed_time_ns cannot precede completion_time_ns")

    if isinstance(side, bool) or side not in (-1, 1):
        raise ValueError("side must be +/-1")
    requested = _positive("requested_size", requested_size)
    filled = _nonnegative("filled_size", filled_size)
    if filled > requested + 1e-12:
        raise ValueError("filled_size cannot exceed requested_size")

    if filled == 0:
        if average_price is not None:
            raise ValueError("zero-fill execution cannot carry average_price")
        average: float | None = None
    else:
        average = _positive("average_price", average_price)

    if not isinstance(source_payload, Mapping):
        raise TypeError("source_payload must be a mapping")
    payload = dict(source_payload)
    payload_sha = _digest(payload)

    broker = _optional_text("broker_name", broker_name)
    order_id = _optional_text("broker_order_id", broker_order_id)
    fill_id = _optional_text("broker_fill_id", broker_fill_id)

    if evidence_kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        if not all((broker, order_id, fill_id)):
            raise ValueError(
                "BROKER_CONFIRMED requires broker_name, broker_order_id, and broker_fill_id"
            )
        market_confirmed = True
        broker_confirmed = True
    else:
        if any(value is not None for value in (broker, order_id, fill_id)):
            raise ValueError(
                "ICARUS_PAPER_EMULATOR cannot carry broker confirmation fields"
            )
        market_confirmed = False
        broker_confirmed = False

    identity = {
        "schema": "argus-execution-evidence-v1",
        "evidence_kind": evidence_kind.value,
        "source_system": system,
        "source_repo": repo,
        "source_commit": commit,
        "source_run_id": run_id,
        "source_execution_id": execution_id,
        "symbol": asset,
        "decision_time_ns": decision,
        "completion_time_ns": completion,
        "observed_time_ns": observed,
        "side": side,
        "requested_size": requested,
        "filled_size": filled,
        "average_price": average,
        "source_payload_sha256": payload_sha,
        "broker_name": broker,
        "broker_order_id": order_id,
        "broker_fill_id": fill_id,
        "market_fill_confirmed": market_confirmed,
        "broker_confirmed": broker_confirmed,
    }
    receipt_id = "execution-evidence:" + _digest(identity)

    return ExecutionEvidenceReceipt(
        receipt_id=receipt_id,
        evidence_kind=evidence_kind,
        source_system=system,
        source_repo=repo,
        source_commit=commit,
        source_run_id=run_id,
        source_execution_id=execution_id,
        symbol=asset,
        decision_time_ns=decision,
        completion_time_ns=completion,
        observed_time_ns=observed,
        side=side,
        requested_size=requested,
        filled_size=filled,
        average_price=average,
        source_payload_sha256=payload_sha,
        broker_name=broker,
        broker_order_id=order_id,
        broker_fill_id=fill_id,
        market_fill_confirmed=market_confirmed,
        broker_confirmed=broker_confirmed,
    )


def _receipt_identity(receipt: ExecutionEvidenceReceipt) -> dict[str, Any]:
    return {
        "schema": "argus-execution-evidence-v1",
        "evidence_kind": receipt.evidence_kind.value,
        "source_system": receipt.source_system,
        "source_repo": receipt.source_repo,
        "source_commit": receipt.source_commit,
        "source_run_id": receipt.source_run_id,
        "source_execution_id": receipt.source_execution_id,
        "symbol": receipt.symbol,
        "decision_time_ns": receipt.decision_time_ns,
        "completion_time_ns": receipt.completion_time_ns,
        "observed_time_ns": receipt.observed_time_ns,
        "side": receipt.side,
        "requested_size": receipt.requested_size,
        "filled_size": receipt.filled_size,
        "average_price": receipt.average_price,
        "source_payload_sha256": receipt.source_payload_sha256,
        "broker_name": receipt.broker_name,
        "broker_order_id": receipt.broker_order_id,
        "broker_fill_id": receipt.broker_fill_id,
        "market_fill_confirmed": receipt.market_fill_confirmed,
        "broker_confirmed": receipt.broker_confirmed,
    }


def _source_execution_identity(
    receipt: ExecutionEvidenceReceipt,
) -> tuple[str, str, str, str, str, str]:
    """Canonical namespace for one upstream execution event.

    Adapter repository/commit identify representation provenance, not the
    execution itself. Broker-confirmed evidence therefore keys identity from
    external broker order/fill lineage, while paper evidence keys from its
    source-system/run/execution lineage.
    """

    if receipt.evidence_kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        return (
            receipt.evidence_kind.value,
            "broker",
            str(receipt.broker_name).casefold(),
            str(receipt.broker_order_id),
            str(receipt.broker_fill_id),
            receipt.symbol,
        )
    return (
        receipt.evidence_kind.value,
        "source",
        receipt.source_system.casefold(),
        receipt.source_run_id,
        receipt.source_execution_id,
        receipt.symbol,
    )


def validate_execution_evidence_receipt(
    receipt: ExecutionEvidenceReceipt,
) -> None:
    if not isinstance(receipt, ExecutionEvidenceReceipt):
        raise TypeError("receipt must be ExecutionEvidenceReceipt")

    if not isinstance(receipt.evidence_kind, ExecutionEvidenceKind):
        raise TypeError("receipt evidence_kind must be ExecutionEvidenceKind")
    _text("source_system", receipt.source_system)
    repo = _text("source_repo", receipt.source_repo)
    if "/" not in repo:
        raise ValueError("source_repo must be owner/repository")
    _sha40("source_commit", receipt.source_commit)
    _text("source_run_id", receipt.source_run_id)
    _text("source_execution_id", receipt.source_execution_id)
    if _text("symbol", receipt.symbol, max_len=64) != receipt.symbol.upper():
        raise ValueError("symbol must be canonical uppercase")

    decision = _nonnegative_ns("decision_time_ns", receipt.decision_time_ns)
    completion = _nonnegative_ns("completion_time_ns", receipt.completion_time_ns)
    observed = _nonnegative_ns("observed_time_ns", receipt.observed_time_ns)
    if completion < decision or observed < completion:
        raise ValueError("receipt time ordering is invalid")

    if isinstance(receipt.side, bool) or receipt.side not in (-1, 1):
        raise ValueError("receipt side must be +/-1")
    requested = _positive("requested_size", receipt.requested_size)
    filled = _nonnegative("filled_size", receipt.filled_size)
    if filled > requested + 1e-12:
        raise ValueError("receipt filled_size cannot exceed requested_size")
    if filled == 0:
        if receipt.average_price is not None:
            raise ValueError("zero-fill receipt cannot carry average_price")
    else:
        _positive("average_price", receipt.average_price)

    payload_sha = _text(
        "source_payload_sha256",
        receipt.source_payload_sha256,
        max_len=64,
    )
    if len(payload_sha) != 64 or any(
        ch not in "0123456789abcdef" for ch in payload_sha
    ):
        raise ValueError("source_payload_sha256 must be lowercase sha256")

    if receipt.evidence_kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        for name in ("broker_name", "broker_order_id", "broker_fill_id"):
            if getattr(receipt, name) is None:
                raise ValueError("BROKER_CONFIRMED receipt is missing broker lineage")
            _text(name, getattr(receipt, name))
        if not receipt.market_fill_confirmed or not receipt.broker_confirmed:
            raise ValueError("BROKER_CONFIRMED flags are inconsistent")
    else:
        if any(
            getattr(receipt, name) is not None
            for name in ("broker_name", "broker_order_id", "broker_fill_id")
        ):
            raise ValueError("paper receipt cannot carry broker lineage")
        if receipt.market_fill_confirmed or receipt.broker_confirmed:
            raise ValueError("paper receipt cannot claim market/broker confirmation")

    if receipt.execution_authorized or receipt.production_decision_authorized:
        raise ValueError("execution-evidence receipt unexpectedly carries authority")

    expected = "execution-evidence:" + _digest(_receipt_identity(receipt))
    if receipt.receipt_id != expected:
        raise ValueError("receipt_id does not match receipt content")


def _icarus_runtime_run_id(value: str) -> str:
    """Validate the exact decimal ICARUS runtime run_id representation."""

    run_id = _text("source_run_id", value)
    if (
        not run_id.isascii()
        or not run_id.isdigit()
        or int(run_id) <= 0
        or str(int(run_id)) != run_id
    ):
        raise ValueError(
            "source_run_id must be the canonical positive decimal ICARUS "
            "runtime run_id"
        )
    return run_id


def _icarus_paper_execution_id(
    *,
    source_run_id: str,
    symbol: str,
    ts: int,
    entry_id: str,
    side: str,
    qty: int,
    price: float,
    kind: str,
    comment: str,
    position_after: int,
) -> str:
    """Canonical identity shared by ICARUS in-memory and journal fill views.

    The fields intentionally match the durable Journal.fills uniqueness
    semantics. Representation-only fields such as SQLite row id, bar index,
    live flag and profit annotation are excluded so the same paper execution
    observed through two ICARUS surfaces cannot be counted twice.
    """

    semantic_identity = {
        "schema": "icarus-paper-execution-identity-v1",
        "run_id": str(source_run_id),
        "symbol": symbol,
        "ts": ts,
        "entry_id": entry_id,
        "side": side,
        "qty": int(qty),
        "price": float(price),
        "kind": kind,
        "comment": comment,
        "position_after": position_after,
    }
    return "icarus-paper-fill:" + _digest(semantic_identity)


def receipt_from_icarus_paper_fill(
    fill: Mapping[str, Any],
    *,
    source_commit: str,
    source_run_id: str,
    symbol: str,
    decision_time_ns: int,
    observed_time_ns: int,
) -> ExecutionEvidenceReceipt:
    """Wrap one ICARUS paper-emulator fill without strengthening its evidence.

    ICARUS runtime Fill.ts is the simulated bar/event timestamp in whole
    seconds. It is converted to nanoseconds for ARGUS. The adapter requires the
    caller to supply the order-decision time because the current fill row does
    not preserve PendingEntry.placed_bar/decision time.

    live=true means the paper emulator processed the fill during the live
    engine epoch. It does NOT mean broker-confirmed execution.
    """

    if not isinstance(fill, Mapping):
        raise TypeError("fill must be a mapping")
    allowed = {
        "ts",
        "bar",
        "id",
        "side",
        "qty",
        "price",
        "kind",
        "comment",
        "profit",
        "pos",
        "live",
    }
    if set(fill) != allowed:
        raise ValueError(
            "ICARUS paper fill requires exactly: " + ", ".join(sorted(allowed))
        )

    ts = fill["ts"]
    if isinstance(ts, bool) or not isinstance(ts, int) or ts < 0:
        raise ValueError("fill ts must be a non-negative integer")
    bar = fill["bar"]
    if isinstance(bar, bool) or not isinstance(bar, int) or bar < 0:
        raise ValueError("fill bar must be a non-negative integer")
    entry_id = _text("fill id", fill["id"])
    fill_side = fill["side"]
    if fill_side not in ("buy", "sell"):
        raise ValueError("fill side must be buy or sell")
    qty = _positive("fill qty", fill["qty"])
    if not float(qty).is_integer():
        raise ValueError("fill qty must be a whole number")
    qty_int = int(qty)
    price = _positive("fill price", fill["price"])
    kind = _text("fill kind", fill["kind"])
    if not isinstance(fill["comment"], str):
        raise TypeError("fill comment must be a string")
    comment = fill["comment"]
    if fill["profit"] is not None:
        _finite("fill profit", fill["profit"])
    pos = fill["pos"]
    if isinstance(pos, bool) or not isinstance(pos, int):
        raise ValueError("fill pos must be an integer")
    if type(fill["live"]) is not bool:
        raise TypeError("fill live must be bool")

    completion_ns = ts * 1_000_000_000
    asset = _text("symbol", symbol, max_len=64).upper()
    runtime_run_id = _icarus_runtime_run_id(source_run_id)
    source_execution_id = _icarus_paper_execution_id(
        source_run_id=runtime_run_id,
        symbol=asset,
        ts=ts,
        entry_id=entry_id,
        side=fill_side,
        qty=qty_int,
        price=price,
        kind=kind,
        comment=comment,
        position_after=pos,
    )

    return create_execution_evidence_receipt(
        evidence_kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        source_system="icarus-paper-emulator",
        source_repo="reppiks490/Icarus",
        source_commit=source_commit,
        source_run_id=runtime_run_id,
        source_execution_id=source_execution_id,
        symbol=asset,
        decision_time_ns=decision_time_ns,
        completion_time_ns=completion_ns,
        observed_time_ns=observed_time_ns,
        side=1 if fill_side == "buy" else -1,
        requested_size=qty_int,
        filled_size=qty_int,
        average_price=price,
        source_payload=dict(fill),
    )


def receipt_from_icarus_journal_fill(
    fill: Mapping[str, Any],
    *,
    source_commit: str,
    decision_time_ns: int,
    observed_time_ns: int,
) -> ExecutionEvidenceReceipt:
    """Wrap one durable ICARUS Journal.fills row as paper execution evidence.

    The adapter mirrors the current SQLite fill schema rather than the
    in-memory chart response. It deliberately requires a separately proven
    decision timestamp because the durable fill row does not store the
    originating PendingEntry decision time.

    The upstream execution identity is derived from the exact fields used by
    ICARUS's durable fills unique index, not from the SQLite row id. Reinserted
    representations of the same indexed fill therefore resolve to the same
    source execution identity and are rejected as duplicates by the evidence
    aggregation firewall.
    """

    if not isinstance(fill, Mapping):
        raise TypeError("fill must be a mapping")
    allowed = {
        "id",
        "run_id",
        "live",
        "symbol",
        "ts",
        "entry_id",
        "side",
        "qty",
        "price",
        "kind",
        "comment",
        "profit",
        "position_after",
    }
    if set(fill) != allowed:
        raise ValueError(
            "ICARUS journal fill requires exactly: "
            + ", ".join(sorted(allowed))
        )

    row_id = fill["id"]
    if (
        isinstance(row_id, bool)
        or not isinstance(row_id, int)
        or row_id <= 0
    ):
        raise ValueError("journal fill id must be a positive integer")

    run_id = fill["run_id"]
    if (
        isinstance(run_id, bool)
        or not isinstance(run_id, int)
        or run_id <= 0
    ):
        raise ValueError(
            "journal fill run_id must be a positive integer; "
            "legacy run_id=0 is not provenance-safe"
        )

    live = fill["live"]
    if isinstance(live, bool) or live not in (0, 1):
        raise ValueError("journal fill live must be integer 0 or 1")

    symbol = _text("journal fill symbol", fill["symbol"], max_len=64).upper()
    ts = fill["ts"]
    if isinstance(ts, bool) or not isinstance(ts, int) or ts < 0:
        raise ValueError("journal fill ts must be a non-negative integer")

    entry_id = _text("journal fill entry_id", fill["entry_id"])
    fill_side = fill["side"]
    if fill_side not in ("buy", "sell"):
        raise ValueError("journal fill side must be buy or sell")

    qty = fill["qty"]
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise ValueError("journal fill qty must be a positive integer")

    price = _positive("journal fill price", fill["price"])
    kind = _text("journal fill kind", fill["kind"])
    comment = fill["comment"]
    if not isinstance(comment, str):
        raise TypeError("journal fill comment must be a string")
    if fill["profit"] is not None:
        _finite("journal fill profit", fill["profit"])

    position_after = fill["position_after"]
    if isinstance(position_after, bool) or not isinstance(position_after, int):
        raise ValueError("journal fill position_after must be an integer")

    source_execution_id = _icarus_paper_execution_id(
        source_run_id=str(run_id),
        symbol=symbol,
        ts=ts,
        entry_id=entry_id,
        side=fill_side,
        qty=qty,
        price=price,
        kind=kind,
        comment=comment,
        position_after=position_after,
    )

    return create_execution_evidence_receipt(
        evidence_kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        source_system="icarus-paper-emulator",
        source_repo="reppiks490/Icarus",
        source_commit=source_commit,
        source_run_id=str(run_id),
        source_execution_id=source_execution_id,
        symbol=symbol,
        decision_time_ns=decision_time_ns,
        completion_time_ns=ts * 1_000_000_000,
        observed_time_ns=observed_time_ns,
        side=1 if fill_side == "buy" else -1,
        requested_size=qty,
        filled_size=qty,
        average_price=price,
        source_payload=dict(fill),
    )


def lineaged_realized_execution(
    receipt: ExecutionEvidenceReceipt,
) -> RealizedExecution:
    validate_execution_evidence_receipt(receipt)
    return RealizedExecution(
        execution_id=receipt.receipt_id,
        decision_time_ns=receipt.decision_time_ns,
        completion_time_ns=receipt.completion_time_ns,
        side=receipt.side,
        requested_size=receipt.requested_size,
        filled_size=receipt.filled_size,
        average_price=receipt.average_price,
    )


def _calibration_identity(
    calibration: ImpactCalibrationObservation,
) -> dict[str, Any]:
    return {
        "execution_id": calibration.execution_id,
        "curve_event_time_ns": calibration.curve_event_time_ns,
        "curve_sequence": calibration.curve_sequence,
        "side": calibration.side,
        "requested_size": calibration.requested_size,
        "visible_opposite_size": calibration.visible_opposite_size,
        "requested_to_visible_ratio": calibration.requested_to_visible_ratio,
        "snapshot_age_ns": calibration.snapshot_age_ns,
        "completion_latency_ns": calibration.completion_latency_ns,
        "predicted_fill_fraction": calibration.predicted_fill_fraction,
        "realized_fill_fraction": calibration.realized_fill_fraction,
        "fill_fraction_error": calibration.fill_fraction_error,
        "predicted_average_slippage_ticks": calibration.predicted_average_slippage_ticks,
        "realized_average_slippage_ticks": calibration.realized_average_slippage_ticks,
        "slippage_error_ticks": calibration.slippage_error_ticks,
        "absolute_slippage_error_ticks": calibration.absolute_slippage_error_ticks,
        "underpredicted_slippage": calibration.underpredicted_slippage,
        "predicted_book_exhausted": calibration.predicted_book_exhausted,
        "realized_complete_fill": calibration.realized_complete_fill,
        "evidence_tier": calibration.evidence_tier.name,
        "assumption": calibration.assumption,
        "execution_authorized": calibration.execution_authorized,
        "production_decision_authorized": calibration.production_decision_authorized,
    }


def _lineage_id(
    receipt: ExecutionEvidenceReceipt,
    calibration: ImpactCalibrationObservation,
) -> str:
    return "impact-calibration-lineage:" + _digest(
        {
            "receipt_id": receipt.receipt_id,
            "calibration": _calibration_identity(calibration),
        }
    )


def calibrate_lineaged_impact(
    curve: DepthImpactCurve,
    receipt: ExecutionEvidenceReceipt,
) -> LineagedImpactCalibrationObservation:
    """Calibrate while retaining execution-source evidence class and lineage."""

    validate_execution_evidence_receipt(receipt)
    calibration = calibrate_impact(
        curve,
        lineaged_realized_execution(receipt),
    )
    return LineagedImpactCalibrationObservation(
        lineage_id=_lineage_id(receipt, calibration),
        receipt=receipt,
        calibration=calibration,
    )


def calibration_by_execution_evidence(
    rows: Iterable[LineagedImpactCalibrationObservation],
) -> tuple[ImpactCalibrationEvidenceStratum, ...]:
    """Summarize evidence classes separately; never pool paper and broker fills."""

    observations = tuple(rows)
    if not observations:
        raise ValueError("at least one lineaged calibration observation is required")

    seen: set[str] = set()
    seen_source_executions: set[
        tuple[str, str, str, str, str, str]
    ] = set()
    grouped: dict[
        ExecutionEvidenceKind,
        list[LineagedImpactCalibrationObservation],
    ] = {}
    for row in observations:
        if not isinstance(row, LineagedImpactCalibrationObservation):
            raise TypeError(
                "rows must contain LineagedImpactCalibrationObservation values"
            )
        validate_execution_evidence_receipt(row.receipt)
        if row.receipt.receipt_id in seen:
            raise ValueError("duplicate receipt_id in lineaged calibration")
        seen.add(row.receipt.receipt_id)

        source_execution = _source_execution_identity(row.receipt)
        if source_execution in seen_source_executions:
            raise ValueError(
                "duplicate source execution identity in lineaged calibration"
            )
        seen_source_executions.add(source_execution)

        if row.execution_authorized or row.production_decision_authorized:
            raise ValueError("lineaged calibration unexpectedly carries authority")

        calibration = row.calibration
        if not isinstance(calibration, ImpactCalibrationObservation):
            raise TypeError("calibration must be ImpactCalibrationObservation")
        if row.lineage_id != _lineage_id(row.receipt, calibration):
            raise ValueError("lineage_id does not match receipt/calibration content")
        if calibration.execution_id != row.receipt.receipt_id:
            raise ValueError("calibration execution_id does not match receipt")
        if calibration.side != row.receipt.side:
            raise ValueError("calibration side does not match receipt")
        if not math.isclose(
            calibration.requested_size,
            row.receipt.requested_size,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("calibration requested_size does not match receipt")
        expected_fraction = (
            row.receipt.filled_size / row.receipt.requested_size
        )
        if not math.isclose(
            calibration.realized_fill_fraction,
            expected_fraction,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("calibration realized fill fraction does not match receipt")
        expected_age = (
            row.receipt.decision_time_ns - calibration.curve_event_time_ns
        )
        if expected_age < 0 or calibration.snapshot_age_ns != expected_age:
            raise ValueError("calibration snapshot age does not match receipt")
        expected_latency = (
            row.receipt.completion_time_ns - row.receipt.decision_time_ns
        )
        if calibration.completion_latency_ns != expected_latency:
            raise ValueError("calibration completion latency does not match receipt")

        grouped.setdefault(row.receipt.evidence_kind, []).append(row)

    strata: list[ImpactCalibrationEvidenceStratum] = []
    for kind in ExecutionEvidenceKind:
        selected = grouped.get(kind, [])
        if not selected:
            continue
        summary = summarize_impact_calibration(
            row.calibration for row in selected
        )
        confirmed = kind is ExecutionEvidenceKind.BROKER_CONFIRMED
        strata.append(
            ImpactCalibrationEvidenceStratum(
                evidence_kind=kind,
                market_fill_confirmed=confirmed,
                broker_confirmed=confirmed,
                observations=len(selected),
                summary=summary,
            )
        )
    return tuple(strata)
