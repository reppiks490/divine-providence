from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .contracts import HypothesisStatus, ThesisAssessment, finite01
from .thesis import ThesisHealthSnapshot


class ResearchAction(str,Enum):
    COLLECT_EVIDENCE="COLLECT_EVIDENCE"
    RETEST="RETEST"
    EXTERNAL_PROMOTION_REVIEW="EXTERNAL_PROMOTION_REVIEW"
    REJECTION_REVIEW="REJECTION_REVIEW"
    RETIREMENT_REVIEW="RETIREMENT_REVIEW"
    MONITOR="MONITOR"


@dataclass(frozen=True,slots=True)
class ResearchDecisionPolicy:
    min_coverage:float=.80
    promotion_health:float=.65
    rejection_contradiction:float=.70
    retirement_health:float=.25
    def __post_init__(self):
        for n in ("min_coverage","promotion_health","rejection_contradiction","retirement_health"):
            finite01(n,getattr(self,n))


@dataclass(frozen=True,slots=True)
class ResearchRecommendation:
    hypothesis_id:str
    status:str
    action:str
    urgency:float
    reasons:tuple[str,...]
    requires_external_authority:bool
    def __post_init__(self):
        if not self.hypothesis_id or self.status not in {x.value for x in HypothesisStatus}: raise ValueError("invalid recommendation identity")
        if self.action not in {x.value for x in ResearchAction}: raise ValueError("invalid recommendation action")
        finite01("urgency",self.urgency)


def recommend(
    hypothesis_id:str,
    status:HypothesisStatus,
    assessment:ThesisAssessment|None,
    health:ThesisHealthSnapshot|None,
    *,
    policy:ResearchDecisionPolicy|None=None,
)->ResearchRecommendation:
    p=policy or ResearchDecisionPolicy(); reasons=[]
    if status is HypothesisStatus.RETIRED:
        return ResearchRecommendation(hypothesis_id,status.value,ResearchAction.MONITOR.value,0.0,("RETIRED",),False)
    if assessment is None:
        return ResearchRecommendation(hypothesis_id,status.value,ResearchAction.COLLECT_EVIDENCE.value,.90,("NO_ASSESSMENT",),False)
    if assessment.evidence_coverage<p.min_coverage:
        reasons.append("EVIDENCE_COVERAGE_LOW")
    if health is not None and health.retest_required:
        reasons.extend(health.reasons)
    if reasons:
        urgency=max(.55,1.0-assessment.evidence_coverage)
        if health is not None: urgency=max(urgency,1.0-health.effective_health)
        return ResearchRecommendation(hypothesis_id,status.value,ResearchAction.RETEST.value if health and health.retest_required else ResearchAction.COLLECT_EVIDENCE.value,min(1.0,urgency),tuple(dict.fromkeys(reasons)),False)
    if assessment.contradiction_score>=p.rejection_contradiction and assessment.evidence_coverage>=p.min_coverage:
        return ResearchRecommendation(hypothesis_id,status.value,ResearchAction.REJECTION_REVIEW.value,assessment.contradiction_score,("CONTRADICTION_HIGH",),True)
    if status is HypothesisStatus.APPROVED_FEATURE and health is not None and health.effective_health<=p.retirement_health:
        return ResearchRecommendation(hypothesis_id,status.value,ResearchAction.RETIREMENT_REVIEW.value,1.0-health.effective_health,("APPROVED_FEATURE_HEALTH_COLLAPSED",),True)
    if status in {HypothesisStatus.TESTING,HypothesisStatus.VALIDATED,HypothesisStatus.STRESS_TESTED,HypothesisStatus.SHADOW} and assessment.thesis_health>=p.promotion_health and assessment.evidence_coverage>=p.min_coverage:
        return ResearchRecommendation(hypothesis_id,status.value,ResearchAction.EXTERNAL_PROMOTION_REVIEW.value,assessment.thesis_health,("RESEARCH_GATE_READY","DAEDALUS_ATHENA_AUTHORITY_REQUIRED"),True)
    return ResearchRecommendation(hypothesis_id,status.value,ResearchAction.MONITOR.value,max(.05,1.0-assessment.thesis_health),("NO_POLICY_ACTION",),False)
