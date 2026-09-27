from nexus.adapters import market_state_packet, for_argus, for_athena


def test_no_production_authority_and_argus_proxy_firewall():
    p=market_state_packet(decision_ns=1,factors={'x':1.0},topology={},quality={'q':1.0},lineage=[])
    assert p['production_authorized'] is False
    a=for_argus(p)
    assert a['evidence_tier']=='CANDLE_PROXY'
    assert a['microstructure_truth'] is False
    assert for_athena(p)['advisory_only'] is True
