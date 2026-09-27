#!/usr/bin/env python3
"""Classify public events and conservatively measure associated market reactions."""
from attribution_score import score_attribution
from geopolitical_event import classify_geopolitical_event, transmission_map


def classify_event(event):
    text=str(event.get('text','')).lower()
    if any(k in text for k in ['tariff','trade duty','import duty']):
        return {'category':'trade_tariff','market_channels':['equities','fx','rates','volatility','commodities']}
    geo=classify_geopolitical_event(event)
    if geo['themes']:
        mapped=transmission_map(geo)
        return {'category':'geopolitical','market_channels':mapped['channels'],'themes':geo['themes'],'assets':mapped['assets']}
    if any(k in text for k in ['rate cut','rate hike','interest rate','federal reserve','central bank']):
        return {'category':'monetary_policy','market_channels':['equities','fx','rates','volatility']}
    if any(k in text for k in ['regulation','antitrust','export control','chip ban']):
        return {'category':'regulatory_policy','market_channels':['equities','fx','volatility']}
    return {'category':'other_public_event','market_channels':['equities','volatility']}


def measure_impact(prices):
    out={}
    for asset,row in prices.items():
        if 'pre' not in row or float(row['pre']) == 0:
            raise ValueError(f'{asset}: nonzero pre baseline required')
        pre=float(row['pre']); returns={}
        for horizon,value in row.items():
            if horizon=='pre': continue
            returns[horizon]=(float(value)/pre-1.0)*100.0
        last=list(returns.values())[-1] if returns else 0.0
        out[asset]={
            'returns_pct':returns,
            'direction':'up' if last>0 else ('down' if last<0 else 'flat'),
            'baseline':pre,
        }
    return out


def attribution_assessment(timing_score, source_score, move_zscore, cross_asset_score, confounder_score, novelty_score,
                           anticipation_score=0.0, independent_sources=2):
    magnitude=min(1.0, abs(float(move_zscore))/3.0)
    features={
        'temporal_proximity':timing_score,
        'asset_relevance':1.0,
        'surprise':novelty_score,
        'reaction_magnitude':magnitude,
        'volume_confirmation':0.5,
        'volatility_confirmation':0.5,
        'independent_sources':independent_sources,
        'cross_asset_confirmation':cross_asset_score,
        'counterfactual_fit':source_score,
        'confounder_strength':confounder_score,
        'anticipation_strength':anticipation_score,
    }
    scored=score_attribution(features)
    return {
        'score':scored['score'],
        'tier':scored['tier'],
        'causal_claim':False,
        'interpretation':f"{scored['tier'].replace('_',' ')}; report as an association unless stronger causal identification is available",
    }
