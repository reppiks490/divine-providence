#!/usr/bin/env python3
"""Conservative association scoring for public events and market reactions."""


def _c(v):
    return max(0.0,min(1.0,float(v)))


def score_attribution(features):
    sources=min(max(int(features.get('independent_sources',0)),0),4)/4.0
    components={
        'temporal_proximity':(_c(features.get('temporal_proximity',0)),0.18),
        'asset_relevance':(_c(features.get('asset_relevance',0)),0.18),
        'surprise':(_c(features.get('surprise',0)),0.12),
        'reaction_magnitude':(_c(features.get('reaction_magnitude',0)),0.14),
        'volume_confirmation':(_c(features.get('volume_confirmation',0)),0.07),
        'volatility_confirmation':(_c(features.get('volatility_confirmation',0)),0.06),
        'independent_sources':(sources,0.08),
        'cross_asset_confirmation':(_c(features.get('cross_asset_confirmation',0)),0.07),
        'counterfactual_fit':(_c(features.get('counterfactual_fit',0)),0.10),
    }
    positive=sum(v*w for v,w in components.values())
    penalty=0.28*_c(features.get('confounder_strength',0))+0.22*_c(features.get('anticipation_strength',0))
    score=max(0.0,min(1.0,positive-penalty))
    if score >= 0.82:
        tier='strongly_supported_association'
    elif score >= 0.65:
        tier='supported_association'
    elif score >= 0.42:
        tier='plausible_association'
    else:
        tier='inconclusive'
    return {
        'score':round(score,6),
        'tier':tier,
        'causal_claim_allowed':False,
        'policy':'Report association strength; do not state unqualified causation from this score alone.'
    }
