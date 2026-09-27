from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence, Optional, Tuple
import hashlib, json, math


@dataclass(frozen=True)
class Sample:
    timestamp: float
    score: float
    confidence: float


@dataclass(frozen=True)
class AttributionObservation:
    component: str
    action_fingerprint: str
    intervention_ts: float
    treated_pre: Tuple[Sample, ...]
    treated_post: Tuple[Sample, ...]
    control_component: Optional[str] = None
    control_pre: Tuple[Sample, ...] = ()
    control_post: Tuple[Sample, ...] = ()
    mutation_events: Tuple[str, ...] = ()
    protected_scope_events: Tuple[str, ...] = ()
    proof_valid: bool = True


@dataclass(frozen=True)
class AttributionPolicy:
    min_samples: int = 2
    min_confidence: float = 0.55
    min_attributable_delta: float = 0.01
    local_trend_confidence_ceiling: float = 0.65
    explicit_control_confidence_ceiling: float = 0.90
    stability_tolerance: float = 0.08


@dataclass(frozen=True)
class AttributionResult:
    observed_delta: float = 0.0
    counterfactual_delta: float = 0.0
    attributable_delta: float = 0.0
    attribution_confidence: float = 0.0
    evidence_method: str = "insufficient"
    contaminated: bool = False
    reasons: Tuple[str, ...] = ()
    evidence_hash: str = ""
    positive_learning_eligible: bool = False


class CounterfactualAttributor:
    """Deterministic, learning-only counterfactual estimator.

    This class has no mutation/authorization callback. Missing or malformed evidence
    fails closed for positive learning and never raises.
    """
    def __init__(self, policy: AttributionPolicy = AttributionPolicy()):
        self.policy = policy

    @staticmethod
    def _series_valid(xs: Sequence[Sample]) -> bool:
        if not xs:
            return False
        prev = -math.inf
        for s in xs:
            if not (math.isfinite(s.timestamp) and math.isfinite(s.score) and math.isfinite(s.confidence)):
                return False
            if s.timestamp <= prev or not (0 <= s.score <= 1) or not (0 <= s.confidence <= 1):
                return False
            prev = s.timestamp
        return True

    @staticmethod
    def _delta(pre: Sequence[Sample], post: Sequence[Sample]) -> float:
        return post[-1].score - pre[-1].score

    @staticmethod
    def _min_conf(*series: Sequence[Sample]) -> float:
        vals = [s.confidence for xs in series for s in xs]
        return min(vals) if vals else 0.0

    @staticmethod
    def _hash(obs: AttributionObservation, result_payload: dict) -> str:
        def samples(xs):
            return [{"timestamp": s.timestamp, "score": s.score, "confidence": s.confidence} for s in xs]
        payload = {
            "component": obs.component,
            "action_fingerprint": obs.action_fingerprint,
            "intervention_ts": obs.intervention_ts,
            "treated_pre": samples(obs.treated_pre), "treated_post": samples(obs.treated_post),
            "control_component": obs.control_component,
            "control_pre": samples(obs.control_pre), "control_post": samples(obs.control_post),
            "mutation_events": list(obs.mutation_events),
            "protected_scope_events": list(obs.protected_scope_events),
            "proof_valid": obs.proof_valid,
            "result": result_payload,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def evaluate(self, obs: AttributionObservation) -> AttributionResult:
        try:
            return self._evaluate(obs)
        except Exception as exc:
            return AttributionResult(contaminated=True, reasons=(f"estimator_exception:{type(exc).__name__}",))

    def _evaluate(self, obs: AttributionObservation) -> AttributionResult:
        p = self.policy
        reasons = []
        contaminated = False
        treated_ok = self._series_valid(obs.treated_pre) and self._series_valid(obs.treated_post)
        if not treated_ok or len(obs.treated_pre) < p.min_samples or len(obs.treated_post) < p.min_samples:
            contaminated = True; reasons.append("invalid_or_insufficient_treated_samples")
        elif obs.treated_pre[-1].timestamp >= obs.intervention_ts or obs.treated_post[0].timestamp <= obs.intervention_ts:
            contaminated = True; reasons.append("treated_window_incompatible")
        if not obs.proof_valid:
            contaminated = True; reasons.append("proof_integrity_failed")
        if obs.mutation_events:
            contaminated = True; reasons.append("overlapping_mutation")
        if obs.protected_scope_events:
            contaminated = True; reasons.append("protected_scope_overlap")

        observed = self._delta(obs.treated_pre, obs.treated_post) if treated_ok else 0.0
        method = "insufficient"; counter = 0.0; conf = 0.0

        if obs.control_component:
            control_ok = self._series_valid(obs.control_pre) and self._series_valid(obs.control_post)
            if not control_ok or len(obs.control_pre) < p.min_samples or len(obs.control_post) < p.min_samples:
                contaminated = True; reasons.append("invalid_or_insufficient_control_samples")
            elif obs.control_pre[-1].timestamp >= obs.intervention_ts or obs.control_post[0].timestamp <= obs.intervention_ts:
                contaminated = True; reasons.append("control_window_incompatible")
            else:
                method = "explicit_control"
                counter = self._delta(obs.control_pre, obs.control_post)
                conf = min(self._min_conf(obs.treated_pre, obs.treated_post, obs.control_pre, obs.control_post), p.explicit_control_confidence_ceiling)
        elif treated_ok and len(obs.treated_pre) >= p.min_samples:
            # Conservative local projection: project the last observed pre-step slope one post-step.
            step = obs.treated_pre[-1].score - obs.treated_pre[-2].score
            historical_steps = [obs.treated_pre[i].score - obs.treated_pre[i-1].score for i in range(1, len(obs.treated_pre))]
            if max(historical_steps) - min(historical_steps) <= p.stability_tolerance:
                method = "local_pretrend"
                counter = step
                conf = min(self._min_conf(obs.treated_pre, obs.treated_post), p.local_trend_confidence_ceiling)
            else:
                reasons.append("unstable_pretrend")

        if conf < p.min_confidence:
            reasons.append("attribution_confidence_below_floor")
        attributable = observed - counter
        eligible = (not contaminated and method != "insufficient" and conf >= p.min_confidence and attributable > p.min_attributable_delta)
        if attributable <= p.min_attributable_delta:
            reasons.append("attributable_delta_below_floor")
        payload = {
            "observed_delta": observed, "counterfactual_delta": counter,
            "attributable_delta": attributable, "attribution_confidence": conf,
            "evidence_method": method, "contaminated": contaminated,
            "reasons": reasons, "positive_learning_eligible": eligible,
        }
        evidence_hash = self._hash(obs, payload) if method != "insufficient" or contaminated else ""
        return AttributionResult(observed, counter, attributable, conf, method, contaminated, tuple(reasons), evidence_hash, eligible)
