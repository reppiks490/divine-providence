from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class TournamentEvidence:
    candidate_id: str
    trades: int
    positive_folds: int
    total_folds: int
    mean_net: float
    ci_low: float
    ci_high: float
    adjusted_p: float
    causality_pass: bool = True
    event_time_pass: bool = True
    ood_abstention_pass: bool = True
    holdout_untouched: bool = True
    hard_veto: bool = False
    specialist_scope: str | None = None

def decide_candidate(e: TournamentEvidence) -> dict:
    if e.hard_veto or not e.causality_pass or not e.event_time_pass or not e.holdout_untouched:
        return {"candidate_id":e.candidate_id,"decision":"QUARANTINE","reasons":["hard_integrity_veto"],"evidence":asdict(e)}
    reasons=[]
    if e.trades < 30: reasons.append("insufficient_trade_count")
    if e.total_folds < 3: reasons.append("insufficient_fold_count")
    fold_ratio=e.positive_folds/e.total_folds if e.total_folds else 0.0
    if fold_ratio < 0.75: reasons.append("insufficient_fold_stability")
    if e.mean_net <= 0: reasons.append("nonpositive_mean")
    if e.ci_low <= 0: reasons.append("confidence_interval_crosses_zero")
    if e.adjusted_p >= 0.05: reasons.append("multiple_testing_not_significant")
    if not e.ood_abstention_pass: reasons.append("ood_fallback_failure")
    if not reasons:
        return {"candidate_id":e.candidate_id,"decision":"PROMOTE_SHADOW","reasons":[],"evidence":asdict(e)}
    specialist_ok=(e.specialist_scope is not None and e.trades>=50 and fold_ratio>=0.75 and e.mean_net>0 and e.ci_low>0 and e.adjusted_p<0.05)
    if specialist_ok:
        return {"candidate_id":e.candidate_id,"decision":"RETAIN_SPECIALIST","reasons":[],"evidence":asdict(e)}
    return {"candidate_id":e.candidate_id,"decision":"QUARANTINE","reasons":reasons,"evidence":asdict(e)}
