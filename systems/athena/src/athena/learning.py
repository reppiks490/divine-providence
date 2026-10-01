"""Outcome-gated shadow competence memory for ATHENA expert routing.

This is not an autonomous production learner. It updates research/shadow competence
only from outcomes whose availability time has actually arrived and whose source has
been independently marked verified.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

from .contracts import ExpertEvidence


def _clip(value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("prediction and target values must be finite")
    return max(-1.0, min(1.0, value))


@dataclass(frozen=True)
class OutcomeRecord:
    expert_id: str
    decision_ns: int
    outcome_available_ns: int
    prediction: float
    target: float
    outcome_source_id: str
    verified: bool

    def __post_init__(self) -> None:
        if not isinstance(self.expert_id, str) or not self.expert_id:
            raise ValueError("expert_id is required")
        if not isinstance(self.outcome_source_id, str) or not self.outcome_source_id:
            raise ValueError("outcome_source_id is required")
        if type(self.decision_ns) is not int or self.decision_ns < 0:
            raise ValueError("decision_ns must be non-negative")
        if type(self.outcome_available_ns) is not int or self.outcome_available_ns <= self.decision_ns:
            raise ValueError("outcome must become available after the decision")
        _clip(self.prediction)
        _clip(self.target)
        if type(self.verified) is not bool:
            raise TypeError("verified must be bool")

    @property
    def record_id(self) -> str:
        body = json.dumps({
            "expert_id": self.expert_id,
            "decision_ns": self.decision_ns,
            "outcome_available_ns": self.outcome_available_ns,
            "prediction": _clip(self.prediction),
            "target": _clip(self.target),
            "outcome_source_id": self.outcome_source_id,
            "verified": self.verified,
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()


class CompetenceMemory:
    def __init__(self) -> None:
        self._records: dict[str, OutcomeRecord] = {}

    def append(self, record: OutcomeRecord) -> str:
        rid = record.record_id
        existing = self._records.get(rid)
        if existing is not None and existing != record:
            raise ValueError("outcome identity collision")
        self._records[rid] = record
        return rid

    def records_asof(self, at_ns: int, *, verified_only: bool = True) -> tuple[OutcomeRecord, ...]:
        if type(at_ns) is not int or at_ns < 0:
            raise ValueError("at_ns must be non-negative")
        rows = [
            x for x in self._records.values()
            if x.outcome_available_ns <= at_ns and (x.verified or not verified_only)
        ]
        return tuple(sorted(rows, key=lambda x: (x.outcome_available_ns, x.decision_ns, x.record_id)))

    def metrics(self, at_ns: int, *, min_samples: int = 5, lookback_ns: int | None = None) -> dict[str, dict]:
        if type(min_samples) is not int or min_samples < 1:
            raise ValueError("min_samples must be positive")
        rows = self.records_asof(at_ns, verified_only=True)
        if lookback_ns is not None:
            if type(lookback_ns) is not int or lookback_ns <= 0:
                raise ValueError("lookback_ns must be positive or None")
            rows = tuple(x for x in rows if x.outcome_available_ns >= max(0, at_ns - lookback_ns))

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
            out[expert_id] = {
                "samples": len(group),
                "score": max(0.0, 1.0 - mae),
                "calibration_error": mae,
                "directional_agreement": directional,
                "recent_health": min(1.0, len(group) / min_samples),
                "ready": len(group) >= min_samples,
                "last_outcome_available_ns": group[-1].outcome_available_ns,
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
    ) -> list[ExpertEvidence]:
        supported_states = supported_states or {}
        ood_scores = ood_scores or {}
        metrics = self.metrics(at_ns, min_samples=min_samples, lookback_ns=lookback_ns)
        evidence = []
        for expert_id, row in metrics.items():
            ood = float(ood_scores.get(expert_id, 0.0))
            if not 0.0 <= ood <= 1.0:
                raise ValueError("OOD scores must be in [0,1]")
            evidence.append(ExpertEvidence(
                expert_id=expert_id,
                score=row["score"],
                calibration_error=row["calibration_error"],
                ood_score=ood,
                recent_health=row["recent_health"],
                supported_states=tuple(supported_states.get(expert_id, ())),
            ))
        return evidence
