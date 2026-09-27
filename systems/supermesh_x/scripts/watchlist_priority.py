#!/usr/bin/env python3
"""Prioritize public market-mover monitoring by market relevance only."""


def _c(v):
    return max(0.0,min(1.0,float(v)))


def score_mover(asset_relevance, topic_relevance, recency, historical_impact, source_coverage):
    score=(
        0.30*_c(asset_relevance)+
        0.20*_c(topic_relevance)+
        0.20*_c(recency)+
        0.20*_c(historical_impact)+
        0.10*_c(source_coverage)
    )
    return {'score':round(score,6),'policy':'market_relevance_only'}
