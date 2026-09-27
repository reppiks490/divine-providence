from scripts.private_intelligence_hub import analyze_private_event_context


def test_hub_combines_email_classification_and_portfolio_overlay_without_exporting_private_payloads():
    out = analyze_private_event_context(
        email={'id':'m1','subject':'TradingView Alert: NQ','body':'condition triggered','timestamp':'2026-09-24T20:00:00Z'},
        holdings=[{'symbol':'QQQ','weight':0.5}],
        shocks={'QQQ':{'shock_score':-1.2,'channel':'equities'}},
        public_event={'event_id':'e1','topic':'rates','confidence':0.8,'evidence_ids':['pub1']},
    )
    assert out['email']['classification']['market_alert'] is True
    assert out['portfolio']['portfolio_shock_score'] == -0.6
    assert out['fusion']['private_context_exportable'] is False
    assert out['outbound_public_payload'] is None
