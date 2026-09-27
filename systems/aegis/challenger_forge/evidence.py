
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class EvidenceRecord:
    evidence_id: str
    title: str
    source_type: str
    peer_reviewed: bool
    review_article: bool = False
    out_of_sample: bool = False
    transaction_costs: bool = False
    trading_delays_or_latency: bool = False
    survivor_bias_control: bool = False
    long_sample: bool = False
    cross_market_or_multi_market: bool = False
    time_series_cv: bool = False
    citation_count: int = 0
    notes: str = ""

def grade_evidence(r: EvidenceRecord) -> dict:
    if r.review_article:
        return {
            "evidence_id": r.evidence_id,
            "grade": "TAXONOMY_REVIEW",
            "score": 0,
            "vetoes": ["review_not_direct_performance_evidence"],
            "record": asdict(r),
        }

    score = 0
    score += 2 if r.peer_reviewed else 0
    score += 3 if r.out_of_sample else 0
    score += 2 if r.transaction_costs else 0
    score += 1 if r.trading_delays_or_latency else 0
    score += 2 if r.survivor_bias_control else 0
    score += 1 if r.long_sample else 0
    score += 1 if r.cross_market_or_multi_market else 0
    score += 1 if r.time_series_cv else 0
    score += 1 if r.citation_count >= 50 else 0

    vetoes = []
    if not r.out_of_sample:
        vetoes.append("no_explicit_out_of_sample")
    if not r.transaction_costs:
        vetoes.append("no_explicit_transaction_cost_model")

    if score >= 10 and not vetoes:
        grade = "A"
    elif score >= 7:
        grade = "B"
    elif score >= 4:
        grade = "C"
    else:
        grade = "D"

    if "no_explicit_out_of_sample" in vetoes and grade in {"A","B"}:
        grade = "C"
    if "no_explicit_transaction_cost_model" in vetoes and grade == "A":
        grade = "B"

    return {
        "evidence_id": r.evidence_id,
        "grade": grade,
        "score": score,
        "vetoes": vetoes,
        "record": asdict(r),
    }
