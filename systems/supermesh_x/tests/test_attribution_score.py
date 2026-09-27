import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from attribution_score import score_attribution


def test_high_signal_event_scores_supported_but_not_absolute_causation():
    out=score_attribution({
      'temporal_proximity':0.98,'asset_relevance':0.95,'surprise':0.9,
      'reaction_magnitude':0.85,'volume_confirmation':0.8,'volatility_confirmation':0.75,
      'independent_sources':3,'cross_asset_confirmation':0.8,'confounder_strength':0.05,
      'anticipation_strength':0.0,'counterfactual_fit':0.9
    })
    assert out['score'] > 0.75
    assert out['tier'] in {'supported_association','strongly_supported_association'}
    assert out['causal_claim_allowed'] is False


def test_confounders_and_pre_event_move_reduce_attribution():
    clean=score_attribution({'temporal_proximity':1,'asset_relevance':1,'surprise':1,'reaction_magnitude':1,'independent_sources':3,'counterfactual_fit':1})
    dirty=score_attribution({'temporal_proximity':1,'asset_relevance':1,'surprise':1,'reaction_magnitude':1,'independent_sources':3,'counterfactual_fit':1,'confounder_strength':0.9,'anticipation_strength':0.8})
    assert dirty['score'] < clean['score']
