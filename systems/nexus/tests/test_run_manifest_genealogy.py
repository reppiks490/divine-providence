from nexus.lineage import DerivationRecord
from nexus.registry import FactorRegistry, FactorSpec
from nexus.run_manifest import FactorGenealogySnapshot, ResearchRunManifest


def _built():
    r=FactorRegistry()
    r.register(FactorSpec('base','1',('A','B'),'equal'))
    r.register(FactorSpec('meta','1',('base',),'ensemble',dependencies=(('base','1'),)))
    d=DerivationRecord.create(product_id='meta',product_version='1',decision_ns=20,spec_hash=r.get('meta','1').spec_hash,input_hashes={'A':'a'*64},code_version='abc',parameters={'w':1})
    g=FactorGenealogySnapshot.create(r,[d])
    m=ResearchRunManifest.create(run_id='r1',decision_start_ns=10,decision_end_ns=20,corpus_manifest_hash='c'*64,reviewed_registry_hash='r'*64,genealogy=g,code_version='abc',input_artifacts={'catalog':'1'*64},output_artifacts={'factor':'2'*64},parameters={'x':2},derivations=[d])
    return r,d,g,m


def test_genealogy_and_run_manifest_are_deterministic_and_verified():
    _,d,g,m=_built()
    assert g.verify() and m.verify()
    assert len(g.genealogy_hash)==64 and len(m.manifest_hash)==64
    assert m.production_authorized is False
    _,d2,g2,m2=_built()
    assert d.derivation_hash==d2.derivation_hash
    assert g.genealogy_hash==g2.genealogy_hash
    assert m.manifest_hash==m2.manifest_hash


def test_run_manifest_exports_aion_context_shapes_without_production_authority():
    _,_,_,m=_built()
    s=m.aion_source_spec(); o=m.aion_observation(ingested_ns=25)
    assert s['capabilities']==['context'] and s['source_sha256']==m.manifest_hash
    assert o['kind']=='context' and o['event_ns']==20 and o['available_ns']==20 and o['ingested_ns']==25
    assert o['payload']['production_authorized'] is False


def test_genealogy_nodes_are_deeply_immutable_shapes():
    import dataclasses
    _,_,g,_=_built()
    assert isinstance(g.factors,tuple) and isinstance(g.factors[0].components,tuple)
    try:
        g.factors[0].name='changed'
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError('genealogy node must be frozen')
