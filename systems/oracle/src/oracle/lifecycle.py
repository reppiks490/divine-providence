from __future__ import annotations
from .contracts import HypothesisStatus, LifecycleTransition, PromotionEvidence

_ALLOWED={
 HypothesisStatus.DISCOVERED:{HypothesisStatus.QUEUED,HypothesisStatus.REJECTED},
 HypothesisStatus.QUEUED:{HypothesisStatus.TESTING,HypothesisStatus.REJECTED},
 HypothesisStatus.TESTING:{HypothesisStatus.VALIDATED,HypothesisStatus.REJECTED},
 HypothesisStatus.VALIDATED:{HypothesisStatus.STRESS_TESTED,HypothesisStatus.REJECTED},
 HypothesisStatus.STRESS_TESTED:{HypothesisStatus.SHADOW,HypothesisStatus.REJECTED},
 HypothesisStatus.SHADOW:{HypothesisStatus.APPROVED_FEATURE,HypothesisStatus.REJECTED,HypothesisStatus.RETIRED},
 HypothesisStatus.APPROVED_FEATURE:{HypothesisStatus.RETIRED},
 HypothesisStatus.REJECTED:{HypothesisStatus.RETIRED},
 HypothesisStatus.RETIRED:set(),
}

def validate_transition(from_status:str,to_status:str)->None:
    a,b=HypothesisStatus(from_status),HypothesisStatus(to_status)
    if b not in _ALLOWED[a]: raise ValueError(f"illegal lifecycle transition {a.value}->{b.value}")

def transition(hypothesis_id:str,from_status:str,to_status:str,occurred_ns:int,reason:str,evidence_ids:tuple[str,...]=())->LifecycleTransition:
    validate_transition(from_status,to_status)
    return LifecycleTransition(hypothesis_id,from_status,to_status,occurred_ns,reason,evidence_ids)

def feature_gate(e:PromotionEvidence, *, max_athena_ood:float=.65)->tuple[bool,tuple[str,...]]:
    failures=[]
    if not e.daedalus_promoted: failures.append("DAEDALUS_NOT_PROMOTED")
    if not e.holdout_clean: failures.append("HOLDOUT_NOT_CLEAN")
    if not e.stress_passed: failures.append("STRESS_NOT_PASSED")
    if not e.shadow_ready: failures.append("SHADOW_NOT_READY")
    if e.athena_abstain: failures.append("ATHENA_ABSTAIN")
    if e.athena_ood_score>max_athena_ood: failures.append("ATHENA_OOD_HIGH")
    if e.unresolved_critical_quality_flags: failures.append("CRITICAL_DATA_QUALITY")
    return not failures,tuple(failures)

def promotion_stages(current_status:str,e:PromotionEvidence,*,max_athena_ood:float=.65)->tuple[tuple[HypothesisStatus,...],tuple[str,...]]:
    """Return only lifecycle stages justified by external promotion evidence.

    ORACLE does not manufacture promotion authority; it translates DAEDALUS/ATHENA
    and quality evidence into legal research-state transitions.
    """
    current=HypothesisStatus(current_status)
    reasons=[]
    stages=[]
    if current is HypothesisStatus.TESTING:
        if e.daedalus_promoted and e.holdout_clean:
            stages.append(HypothesisStatus.VALIDATED); current=HypothesisStatus.VALIDATED
        else:
            if not e.daedalus_promoted: reasons.append("DAEDALUS_NOT_PROMOTED")
            if not e.holdout_clean: reasons.append("HOLDOUT_NOT_CLEAN")
            return tuple(stages),tuple(reasons)
    if current is HypothesisStatus.VALIDATED:
        if e.stress_passed and not e.unresolved_critical_quality_flags:
            stages.append(HypothesisStatus.STRESS_TESTED); current=HypothesisStatus.STRESS_TESTED
        else:
            if not e.stress_passed: reasons.append("STRESS_NOT_PASSED")
            if e.unresolved_critical_quality_flags: reasons.append("CRITICAL_DATA_QUALITY")
            return tuple(stages),tuple(reasons)
    if current is HypothesisStatus.STRESS_TESTED:
        if e.shadow_ready and not e.athena_abstain and e.athena_ood_score<=max_athena_ood:
            stages.append(HypothesisStatus.SHADOW); current=HypothesisStatus.SHADOW
        else:
            if not e.shadow_ready: reasons.append("SHADOW_NOT_READY")
            if e.athena_abstain: reasons.append("ATHENA_ABSTAIN")
            if e.athena_ood_score>max_athena_ood: reasons.append("ATHENA_OOD_HIGH")
            return tuple(stages),tuple(reasons)
    if current is HypothesisStatus.SHADOW:
        ok,failures=feature_gate(e,max_athena_ood=max_athena_ood)
        if ok: stages.append(HypothesisStatus.APPROVED_FEATURE)
        else: reasons.extend(failures)
    return tuple(stages),tuple(dict.fromkeys(reasons))
