"""Outcome-gated shadow competence memory for ATHENA expert routing.

This is not an autonomous production learner. It updates research/shadow competence
only from outcomes whose event, availability, and actual recording times are causal,
and whose source has been independently marked verified.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

from .contracts import DataPlane, ExpertEvidence


def _clip(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("prediction and target values must be finite")
    return max(-1.0, min(1.0, value))


def _stable_id(field: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} is required")
    return value


@dataclass(frozen=True)
class OutcomeRecord:
    expert_id: str
    decision_ns: int
    outcome_available_ns: int
    prediction: float
    target: float
    outcome_source_id: str
    verified: bool
    state_id: str = "*"
    outcome_event_ns: int | None = None
    recorded_ns: int | None = None
    prediction_id: str | None = None
    plane: DataPlane = DataPlane.RESEARCH

    def __post_init__(self) -> None:
        _stable_id("expert_id", self.expert_id)
        _stable_id("outcome_source_id", self.outcome_source_id)
        _stable_id("state_id", self.state_id)
        if type(self.decision_ns) is not int or self.decision_ns < 0:
            raise ValueError("decision_ns must be non-negative")
        if type(self.outcome_available_ns) is not int or self.outcome_available_ns <= self.decision_ns:
            raise ValueError("outcome must become available after the decision")

        event_ns = self.outcome_available_ns if self.outcome_event_ns is None else self.outcome_event_ns
        recorded_ns = self.outcome_available_ns if self.recorded_ns is None else self.recorded_ns
        if type(event_ns) is not int or event_ns <= self.decision_ns:
            raise ValueError("outcome event must occur after the decision")
        if self.outcome_available_ns < event_ns:
            raise ValueError("outcome availability cannot precede outcome event")
        if type(recorded_ns) is not int or recorded_ns < self.outcome_available_ns:
            raise ValueError("recorded_ns cannot precede outcome availability")
        object.__setattr__(self, "outcome_event_ns", event_ns)
        object.__setattr__(self, "recorded_ns", recorded_ns)

        _clip(self.prediction)
        _clip(self.target)
        if type(self.verified) is not bool:
            raise TypeError("verified must be bool")
        if not isinstance(self.plane, DataPlane):
            raise TypeError("plane must be DataPlane")
        if self.plane is DataPlane.PRODUCTION:
            raise ValueError("online competence updates are research/shadow only")

        prediction_id = self.prediction_id
        if prediction_id is None:
            body = json.dumps({
                "expert_id": self.expert_id,
                "state_id": self.state_id,
                "decision_ns": self.decision_ns,
            }, sort_keys=True, separators=(",", ":"))
            prediction_id = hashlib.sha256(body.encode()).hexdigest()
            object.__setattr__(self, "prediction_id", prediction_id)
        _stable_id("prediction_id", prediction_id)

    @property
    def record_id(self) -> str:
        body = json.dumps({
            "prediction_id": self.prediction_id,
            "expert_id": self.expert_id,
            "state_id": self.state_id,
            "decision_ns": self.decision_ns,
            "outcome_event_ns": self.outcome_event_ns,
            "outcome_available_ns": self.outcome_available_ns,
            "recorded_ns": self.recorded_ns,
            "prediction": _clip(self.prediction),
            "target": _clip(self.target),
            "outcome_source_id": self.outcome_source_id,
            "verified": self.verified,
            "plane": self.plane.value,
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()


class CompetenceMemory:
    """Append-only causal outcome memory keyed by immutable prediction identity."""

    def __init__(self) -> None:
        self._records: dict[str, OutcomeRecord] = {}

    def append(self, record: OutcomeRecord) -> str:
        if not isinstance(record, OutcomeRecord):
            raise TypeError("record must be OutcomeRecord")
        key = record.prediction_id
        existing = self._records.get(key)
        if existing is not None:
            if existing != record:
                raise ValueError("prediction_id already has different immutable outcome evidence")
            return existing.record_id
        self._records[key] = record
        return record.record_id

    def records_asof(
        self,
        at_ns: int,
        *,
        verified_only: bool = True,
        state_id: str | None = None,
    ) -> tuple[OutcomeRecord, ...]:
        if type(at_ns) is not int or at_ns < 0:
            raise ValueError("at_ns must be non-negative")
        if state_id is not None:
            _stable_id("state_id", state_id)
        rows = [
            x for x in self._records.values()
            if x.outcome_available_ns <= at_ns
            and x.recorded_ns <= at_ns
            and (x.verified or not verified_only)
            and (state_id is None or x.state_id in (state_id, "*"))
        ]
        return tuple(sorted(
            rows,
            key=lambda x: (x.recorded_ns, x.outcome_available_ns, x.decision_ns, x.record_id),
        ))

    def metrics(
        self,
        at_ns: int,
        *,
        min_samples: int = 5,
        lookback_ns: int | None = None,
        state_id: str | None = None,
    ) -> dict[str, dict]:
        if type(min_samples) is not int or min_samples < 1:
            raise ValueError("min_samples must be positive")
        rows = self.records_asof(at_ns, verified_only=True, state_id=state_id)
        if lookback_ns is not None:
            if type(lookback_ns) is not int or lookback_ns <= 0:
                raise ValueError("lookback_ns must be positive or None")
            rows = tuple(x for x in rows if x.recorded_ns >= max(0, at_ns - lookback_ns))

        by_expert: dict[str, list[OutcomeRecord]] = {}
        for row in rows:
            by_expert.setdefault(row.expert_id, []).append(row)

        out: dict[str, dict] = {}
        for expert_id, group in sorted(by_expert.items()):
            errors = [abs(_clip(x.prediction) - _clip(x.target)) / 2.0 for x in group]
            mae = sum(errors) / len(errors)
            directional = sum(
                (x.prediction == 0 and x.target == 0) or (x.prediction * x.target > 0)
                for x in group
            ) / len(group)
            sufficiency = min(1.0, len(group) / min_samples)
            recent = group[-min(20, len(group)):]
            recent_directional = sum(
                (x.prediction == 0 and x.target == 0) or (x.prediction * x.target > 0)
                for x in recent
            ) / len(recent)
            out[expert_id] = {
                "samples": len(group),
                "score": max(0.0, min(1.0, (1.0 - mae) * directional * sufficiency)),
                "calibration_error": mae,
                "directional_agreement": directional,
                "recent_health": recent_directional,
                "sample_sufficiency": sufficiency,
                "ready": len(group) >= min_samples,
                "last_outcome_available_ns": group[-1].outcome_available_ns,
                "last_recorded_ns": group[-1].recorded_ns,
                "production_authorized": False,
            }
        return out

    def expert_evidence(
        self,
        at_ns: int,
        *,
        supported_states: dict[str, Iterable[str]] | None = None,
        ood_scores: dict[str, float] | None = None,
        min_samples: int = 5,
        lookback_ns: int | None = None,
        state_id: str | None = None,
    ) -> list[ExpertEvidence]:
        supported_states = supported_states or {}
        ood_scores = ood_scores or {}
        metrics = self.metrics(
            at_ns,
            min_samples=min_samples,
            lookback_ns=lookback_ns,
            state_id=state_id,
        )
        evidence = []
        for expert_id, row in metrics.items():
            # Absence of an OOD detector is not evidence of in-distribution state.
            ood = float(ood_scores.get(expert_id, 1.0))
            if not math.isfinite(ood) or not 0.0 <= ood <= 1.0:
                raise ValueError("OOD scores must be finite in [0,1]")
            evidence.append(ExpertEvidence(
                expert_id=expert_id,
                score=row["score"],
                calibration_error=row["calibration_error"],
                ood_score=ood,
                recent_health=row["recent_health"],
                supported_states=tuple(supported_states.get(expert_id, ())),
            ))
        return evidence
