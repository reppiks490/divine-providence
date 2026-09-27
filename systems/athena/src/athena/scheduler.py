from __future__ import annotations

from .contracts import ResearchRequest


def research_priority(r: ResearchRequest) -> float:
    cost = max(float(r.estimated_compute_cost), 1e-9)
    return (max(0.0, r.expected_information_gain) * max(0.0, r.strategic_relevance) * max(0.0, r.evidence_deficit)) / cost


def rank_requests(requests: list[ResearchRequest]) -> list[ResearchRequest]:
    return sorted(requests, key=research_priority, reverse=True)
