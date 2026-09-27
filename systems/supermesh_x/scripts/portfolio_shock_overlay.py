"""Map observed market shocks onto portfolio holdings for descriptive exposure analysis."""

from __future__ import annotations

from typing import Any, Dict, Iterable


def build_overlay(holdings: Iterable[Dict[str, Any]], shocks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    gross_exposed_weight = 0.0
    score = 0.0
    exposures = []
    for holding in holdings:
        symbol = holding.get("symbol")
        weight = float(holding.get("weight", 0.0) or 0.0)
        shock = shocks.get(symbol)
        if shock is None:
            continue
        gross_exposed_weight += abs(weight)
        contribution = weight * float(shock.get("shock_score", 0.0) or 0.0)
        score += contribution
        exposures.append({
            "symbol": symbol,
            "weight": weight,
            "shock_score": shock.get("shock_score", 0.0),
            "contribution": contribution,
            "channel": shock.get("channel"),
        })
    return {
        "gross_exposed_weight": round(gross_exposed_weight, 10),
        "portfolio_shock_score": round(score, 10),
        "exposures": exposures,
        "trade_instruction": None,
        "causal_claim": False,
    }
