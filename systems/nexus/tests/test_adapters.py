from nexus.adapters import market_state_packet, for_argus, for_athena


def test_no_production_authority_and_argus_proxy_firewall():
    p=market_state_packet(decision_ns=1,factors={'x':1.0},topology={},quality={'q':1.0},lineage=[])
    assert p['production_authorized'] is False
    a=for_argus(p)
    assert a['evidence_tier']=='CANDLE_PROXY'
    assert a['microstructure_truth'] is False
    assert for_athena(p)['advisory_only'] is True


def test_market_state_and_sibling_adapters_reject_malformed_boundary_values():
    import pytest
    from nexus.adapters import (
        argus_candle_proxy_feature,athena_provenance,
        aion_context_source_spec,aion_derivation_source_spec,
    )
    with pytest.raises(ValueError,match='decision_ns'):
        market_state_packet(
            decision_ns=1.5,factors={},topology={},quality={},lineage=[]
        )
    with pytest.raises(ValueError,match='finite'):
        market_state_packet(
            decision_ns=1,factors={'x':float('nan')},
            topology={},quality={},lineage=[]
        )
    with pytest.raises(ValueError,match='finite JSON'):
        market_state_packet(
            decision_ns=1,factors={},topology={'x':float('inf')},
            quality={},lineage=[]
        )
    with pytest.raises(ValueError,match='finite'):
        argus_candle_proxy_feature(
            name='x',value=float('nan'),event_ns=1,source_id='s',reason='r'
        )
    with pytest.raises(ValueError,match='cannot precede'):
        athena_provenance(
            event_time_ns=10,ingestion_time_ns=9,source_id='s',
            representation_id='r',version='1',lineage_id='l'
        )
    with pytest.raises(ValueError,match='source_sha256'):
        aion_context_source_spec(
            source_id='s',representation_id='r',symbol='X',
            source_sha256='bad',evidence_reference='e'
        )
    with pytest.raises(ValueError,match='spec_hash'):
        aion_derivation_source_spec(
            product_id='p',product_version='1',spec_hash='bad',code_version='v'
        )



def test_nexus_derived_aion_context_uses_derived_at_decision_not_synthetic():
    from nexus.adapters import aion_derivation_observation, aion_source_health_observation
    from nexus.lineage import DerivationRecord
    from nexus.source_health import SourceHealthRegistry

    derivation = DerivationRecord.create(
        product_id="NEXUS:RISK", product_version="1", decision_ns=160,
        spec_hash="a" * 64, input_hashes={"NQ": "b" * 64}, code_version="test",
    )
    derived = aion_derivation_observation(derivation, ingested_ns=175)
    assert derived["kind"] == "context"
    assert derived["event_ns"] == 160 == derived["available_ns"]
    assert derived["ingested_ns"] == 175
    assert derived["availability_basis"] == "derived_at_decision"
    assert "synthetic" not in derived["quality_flags"]

    plane = SourceHealthRegistry().snapshot(160)
    health = aion_source_health_observation(plane, ingested_ns=175)
    assert health["kind"] == "context"
    assert health["event_ns"] == 160 == health["available_ns"]
    assert health["ingested_ns"] == 175
    assert health["availability_basis"] == "derived_at_decision"
    assert "synthetic" not in health["quality_flags"]
