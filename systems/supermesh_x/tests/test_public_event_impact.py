import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from public_event_impact import classify_event, measure_impact, attribution_assessment


def test_classify_trump_tariff_event():
    event = {"text": "President Trump announced a 25% tariff on imported autos", "actor": "Donald Trump"}
    out = classify_event(event)
    assert out["category"] == "trade_tariff"
    assert out["market_channels"] == ["equities", "fx", "rates", "volatility", "commodities"]


def test_measure_impact_uses_pre_event_baseline_and_multi_horizon_returns():
    prices = {
        "NQ": {"pre": 20000.0, "5m": 19800.0, "30m": 19700.0, "1h": 19600.0},
        "VIX": {"pre": 15.0, "5m": 16.5, "30m": 17.0, "1h": 17.2},
    }
    out = measure_impact(prices)
    assert round(out["NQ"]["returns_pct"]["5m"], 4) == -1.0
    assert round(out["VIX"]["returns_pct"]["5m"], 4) == 10.0
    assert out["NQ"]["direction"] == "down"
    assert out["VIX"]["direction"] == "up"


def test_attribution_penalizes_confounders_and_never_claims_causality():
    clean = attribution_assessment(
        timing_score=0.95,
        source_score=0.95,
        move_zscore=3.0,
        cross_asset_score=0.9,
        confounder_score=0.1,
        novelty_score=0.9,
    )
    noisy = attribution_assessment(
        timing_score=0.95,
        source_score=0.95,
        move_zscore=3.0,
        cross_asset_score=0.9,
        confounder_score=0.9,
        novelty_score=0.9,
    )
    assert clean["score"] > noisy["score"]
    assert clean["causal_claim"] is False
    assert "association" in clean["interpretation"].lower()
