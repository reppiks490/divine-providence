#!/usr/bin/env python3
"""Plan cross-asset event studies for public market-moving figures."""
from impact_windows import event_windows


def build_event_study_plan(entity_id, assets, style='intraday'):
    return {
        'entity_id':entity_id,
        'assets':list(assets),
        'style':style,
        'windows':event_windows(style),
        'measurements':[
            'raw_return','abnormal_return','realized_volatility','volume_zscore',
            'spread_or_liquidity_if_available','cross_asset_response'
        ],
        'counterfactual':{
            'enabled':True,
            'preferred_methods':['matched_controls','synthetic_control','factor_adjusted_return'],
            'short_horizon_preferred':True,
        },
        'confounder_checks':[
            'scheduled_macro_release','central_bank_event','earnings_or_company_news',
            'geopolitical_breaking_news','market_open_close_effect','already_moving_pre_event',
            'duplicate_or_syndicated_story','timestamp_uncertainty'
        ],
        'attribution_policy':'association_not_unqualified_causation',
        'outputs':['impact_score','confidence_tier','direction','peak_window','decay_profile','affected_assets','evidence_lineage']
    }
