#!/usr/bin/env python3
"""Join authorized private intelligence with public event analysis without raw-data egress."""
try:
    from .email_intelligence import normalize_message, classify_message
    from .portfolio_shock_overlay import build_overlay
    from .private_context_fusion import fuse_public_event_with_private_context
except ImportError:
    from email_intelligence import normalize_message, classify_message
    from portfolio_shock_overlay import build_overlay
    from private_context_fusion import fuse_public_event_with_private_context


def analyze_private_event_context(email, holdings, shocks, public_event):
    normalized=normalize_message(email)
    classification=classify_message(email)
    normalized['classification']=classification
    portfolio=build_overlay(holdings, shocks)
    private_context={
        'portfolio_id':'authorized_portfolio_context',
        'overlay_score':portfolio['portfolio_shock_score'],
        'evidence_ids':[normalized.get('message_id')] if normalized.get('message_id') else [],
    }
    fusion=fuse_public_event_with_private_context(public_event, private_context)
    return {
        'email':normalized,
        'portfolio':portfolio,
        'fusion':fusion,
        'outbound_public_payload':None,
        'privacy_boundary':'private_raw_data_stays_private',
    }
