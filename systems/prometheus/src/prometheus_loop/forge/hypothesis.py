from __future__ import annotations

from ..contracts import DisagreementCase, ResearchHypothesis


_FAMILIES = {
    "DIRECTIONAL": (
        "EVIDENCE_OR_SPECIALIZATION_MISMATCH",
        "Sibling directional disagreement is caused by evidence mismatch, specialization boundary, or a regime-transition lag.",
        "After aligning eligible evidence and replaying the same instant, the directional disagreement persists without source-health or specialization explanation.",
    ),
    "CONFIDENCE": (
        "CALIBRATION_OR_EVIDENCE_MISMATCH",
        "Sibling confidence disagreement is caused by calibration drift or unequal eligible evidence.",
        "Confidence remains materially different after identical evidence and calibration controls are applied.",
    ),
    "REGIME": (
        "REGIME_TRANSITION_MISMATCH",
        "Sibling regime disagreement is caused by transition timing or representation sensitivity.",
        "The disagreement persists outside transition windows under matched representations.",
    ),
    "RISK": (
        "RISK_INPUT_MISMATCH",
        "Sibling risk disagreement is caused by different eligible risk inputs or staleness.",
        "The disagreement persists after risk inputs and availability are matched.",
    ),
}


def hypothesis_from_case(case: DisagreementCase) -> ResearchHypothesis:
    family, claim, falsifier = _FAMILIES.get(
        case.disagreement_type,
        (
            "GENERIC_EVIDENCE_MISMATCH",
            f"Disagreement on {case.dimension} is caused by an identifiable evidence or model-boundary difference.",
            f"No eligible evidence or model-boundary difference explains the {case.dimension} disagreement under replay.",
        ),
    )
    return ResearchHypothesis(case_id=case.artifact_id, family=family, claim=claim, falsifier=falsifier)
