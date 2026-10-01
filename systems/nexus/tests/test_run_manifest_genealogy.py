from nexus.lineage import DerivationRecord
from nexus.registry import FactorRegistry, FactorSpec
from nexus.run_manifest import FactorGenealogySnapshot, ResearchRunManifest


def _built():
    r=FactorRegistry()
    r.register(FactorSpec('base','1',('A','B'),'equal'))
    r.register(FactorSpec('meta','1',('base',),'ensemble',dependencies=(('base','1'),)))
    d=DerivationRecord.create(product_id='meta',product_version='1',decision_ns=20,spec_hash=r.get('meta','1').spec_hash,input_hashes={'A':'a'*64},code_version='abc',parameters={'w':1})
    g=FactorGenealogySnapshot.create(r,[d])
    m=ResearchRunManifest.create(run_id='r1',decision_start_ns=10,decision_end_ns=20,corpus_manifest_hash='c'*64,reviewed_registry_hash='e'*64,genealogy=g,code_version='abc',input_artifacts={'catalog':'1'*64},output_artifacts={'factor':'2'*64},parameters={'x':2},derivations=[d])
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
    assert o['kind']=='context' and o['event_ns']==20 and o['available_ns']==25 and o['ingested_ns']==25
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


def test_genealogy_rejects_dangling_dependency():
    import pytest
    r=FactorRegistry()
    r.register(FactorSpec('meta','1',('missing',),'ensemble',dependencies=(('missing','1'),)))
    with pytest.raises(ValueError,match='missing factor dependencies'):
        FactorGenealogySnapshot.create(r)


def test_registry_cycle_failure_is_atomic():
    import pytest
    r=FactorRegistry()
    r.register(FactorSpec('a','1',('B',),'equal',dependencies=(('b','1'),)))
    with pytest.raises(ValueError,match='cycle'):
        r.register(FactorSpec('b','1',('A',),'equal',dependencies=(('a','1'),)))
    assert ('b','1') in r.missing_dependencies()
    # Failed registration did not leave b installed.
    try:
        r.get('b','1')
    except KeyError:
        pass
    else:
        raise AssertionError('cycle failure must roll back registry mutation')


def test_genealogy_and_run_reject_tampered_derivation():
    import dataclasses
    import pytest
    r,d,g,m=_built()
    bad=dataclasses.replace(d,derivation_hash='0'*64)
    with pytest.raises(ValueError,match='invalid derivation'):
        FactorGenealogySnapshot.create(r,[bad])
    with pytest.raises(ValueError,match='invalid derivation'):
        ResearchRunManifest.create(
            run_id='bad',decision_start_ns=10,decision_end_ns=20,
            corpus_manifest_hash='c'*64,reviewed_registry_hash='e'*64,
            genealogy=g,code_version='abc',input_artifacts={},output_artifacts={},
            derivations=[bad],
        )


def test_derivation_identity_rejects_invalid_hashes_time_and_nan_parameters():
    import pytest
    kwargs=dict(
        product_id='x',product_version='1',decision_ns=1,
        spec_hash='a'*64,input_hashes={'A':'b'*64},code_version='v1',
    )
    with pytest.raises(ValueError,match='decision_ns'):
        DerivationRecord.create(**{**kwargs,'decision_ns':-1})
    with pytest.raises(ValueError,match='spec_hash'):
        DerivationRecord.create(**{**kwargs,'spec_hash':'not-a-hash'})
    with pytest.raises(ValueError,match='input hash'):
        DerivationRecord.create(**{**kwargs,'input_hashes':{'A':'bad'}})
    with pytest.raises(ValueError,match='canonical JSON'):
        DerivationRecord.create(**kwargs,parameters={'x':float('nan')})
    with pytest.raises(ValueError,match='product_id'):
        DerivationRecord.create(**{**kwargs,'product_id':' '})


def test_run_manifest_rejects_derivations_not_bound_to_genealogy():
    import pytest
    r=FactorRegistry()
    r.register(FactorSpec('base','1',('A',),'equal'))
    d=DerivationRecord.create(
        product_id='base',product_version='1',decision_ns=20,
        spec_hash=r.get('base','1').spec_hash,input_hashes={'A':'a'*64},
        code_version='v1',
    )
    empty=FactorGenealogySnapshot.create(r,[])
    with pytest.raises(ValueError,match='exactly match'):
        ResearchRunManifest.create(
            run_id='x',decision_start_ns=10,decision_end_ns=20,
            corpus_manifest_hash='c'*64,reviewed_registry_hash='e'*64,
            genealogy=empty,code_version='v1',
            input_artifacts={},output_artifacts={},derivations=[d],
        )


def test_run_manifest_rejects_invalid_hashes_and_observation_sequence():
    import pytest
    _,_,_,m=_built()
    with pytest.raises(ValueError,match='reviewed_registry_hash'):
        ResearchRunManifest.create(
            run_id='bad',decision_start_ns=10,decision_end_ns=20,
            corpus_manifest_hash='c'*64,reviewed_registry_hash='not-a-hash',
            genealogy=FactorGenealogySnapshot.create(FactorRegistry()),
            code_version='v1',input_artifacts={},output_artifacts={},
        )
    with pytest.raises(ValueError,match='sequence'):
        m.aion_observation(sequence=-1)
    with pytest.raises(ValueError,match='ingested_ns'):
        m.aion_observation(ingested_ns=-1)


def test_rehashed_genealogy_and_run_cannot_hide_semantic_malformed_state():
    import dataclasses,hashlib,json
    _,_,g,m=_built()

    # Bypass the hardened constructor deliberately to emulate a forged
    # deserialized object whose outer hash was recomputed after semantic tampering.
    original=g.factors[0]
    bad_node=object.__new__(type(original))
    for name,value in (
        ('name',original.name),
        ('version',original.version),
        ('components',('A','A')),
        ('method',original.method),
        ('dependencies',original.dependencies),
        ('spec_hash',original.spec_hash),
    ):
        object.__setattr__(bad_node,name,value)
    factors=(bad_node,*g.factors[1:])
    payload=FactorGenealogySnapshot._payload(
        g.schema,factors,g.dependency_edges,g.derivation_hashes
    )
    forged=FactorGenealogySnapshot(
        g.schema,factors,g.dependency_edges,g.derivation_hashes,
        hashlib.sha256(
            json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        ).hexdigest(),
    )
    assert not forged.verify()

    bad_run=dataclasses.replace(
        m,
        run_id=' r1 ',
        input_artifacts=(('catalog','1'*64),('catalog','1'*64)),
    )
    payload={
        "schema":bad_run.schema,"run_id":bad_run.run_id,
        "decision_start_ns":bad_run.decision_start_ns,
        "decision_end_ns":bad_run.decision_end_ns,
        "corpus_manifest_hash":bad_run.corpus_manifest_hash,
        "reviewed_registry_hash":bad_run.reviewed_registry_hash,
        "genealogy_hash":bad_run.genealogy_hash,
        "code_version":bad_run.code_version,
        "input_artifacts":bad_run.input_artifacts,
        "output_artifacts":bad_run.output_artifacts,
        "parameters_hash":bad_run.parameters_hash,
        "derivation_hashes":bad_run.derivation_hashes,
        "production_authorized":False,
    }
    bad_run=dataclasses.replace(
        bad_run,
        manifest_hash=hashlib.sha256(
            json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        ).hexdigest(),
    )
    assert not bad_run.verify()


def test_run_manifest_requires_trimmed_run_and_code_identity():
    import pytest
    r=FactorRegistry()
    g=FactorGenealogySnapshot.create(r)
    common=dict(
        decision_start_ns=0,decision_end_ns=1,
        corpus_manifest_hash='c'*64,reviewed_registry_hash='e'*64,
        genealogy=g,input_artifacts={},output_artifacts={},
    )
    with pytest.raises(ValueError,match='run_id'):
        ResearchRunManifest.create(run_id=' x ',code_version='v1',**common)
    with pytest.raises(ValueError,match='code_version'):
        ResearchRunManifest.create(run_id='x',code_version=' v1 ',**common)
