#!/usr/bin/env python3
"""Rank recursive research frontier items and stop when novelty yield collapses."""


def _clamp(value):
    return max(0.0, min(1.0, float(value)))


def rank_frontier(items):
    rows = []
    for item in items:
        row = dict(item)
        relevance = _clamp(row.get("relevance", 0.0))
        novelty = _clamp(row.get("novelty", 0.0))
        cost = max(0.1, float(row.get("cost", 1.0)))
        diversity = 1.15 if not row.get("family_seen", False) else 0.75
        row["frontier_score"] = round((relevance * novelty * diversity) / cost, 6)
        rows.append(row)
    rows.sort(key=lambda x: x["frontier_score"], reverse=True)
    return rows


def should_continue(novelty_yields, remaining_budget, min_yield=0.05, patience=3):
    if remaining_budget <= 0:
        return False
    if len(novelty_yields) < patience:
        return True
    recent = novelty_yields[-patience:]
    return any(float(v) >= min_yield for v in recent)
