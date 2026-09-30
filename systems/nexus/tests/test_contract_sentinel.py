from pathlib import Path
from nexus.contract_sentinel import ContractDriftSnapshot, compare_contract_snapshots


def test_contract_sentinel_distinguishes_formatting_from_semantics(tmp_path: Path):
    p=tmp_path/'c.py'; p.write_text('def f(x:int)->int:\n    return x+1\n')
    a=ContractDriftSnapshot.capture({('AION','contracts'):p})
    assert a.verify()
    p.write_text('# comment\n\ndef f(x:int)->int:\n    return x + 1\n')
    b=ContractDriftSnapshot.capture({('AION','contracts'):p})
    r=compare_contract_snapshots(a,b)
    assert r.raw_drift is True and r.semantic_drift is False
    assert r.items[0].status=='nonsemantic_change'
    p.write_text('def f(x:int)->int:\n    return x+2\n')
    c=ContractDriftSnapshot.capture({('AION','contracts'):p})
    r2=compare_contract_snapshots(b,c)
    assert r2.semantic_drift is True and r2.items[0].status=='semantic_change'


def test_contract_sentinel_snapshot_roundtrip_and_add_remove(tmp_path: Path):
    a=tmp_path/'a.py'; b=tmp_path/'b.py'; a.write_text('X=1\n'); b.write_text('Y=2\n')
    s1=ContractDriftSnapshot.capture({('ARGUS','contracts'):a})
    out=tmp_path/'snapshot.json'; s1.save(out)
    assert ContractDriftSnapshot.load(out)==s1
    s2=ContractDriftSnapshot.capture({('ATHENA','contracts'):b})
    r=compare_contract_snapshots(s1,s2)
    assert r.semantic_drift is True
    assert {x.status for x in r.items}=={'added','removed'}


def test_contract_sentinel_ignores_interpreter_specific_ast_for_identical_bytes(tmp_path: Path):
    # A baseline captured under another Python version carries a different
    # ast.dump fingerprint for byte-identical source; that must not be drift.
    import hashlib, json
    p=tmp_path/'c.py'; p.write_text('def f(x:int)->int:\n    return x+1\n')
    current=ContractDriftSnapshot.capture({('AION','contracts'):p})
    body=current.to_dict(); body['files'][0]['ast_sha256']='f'*64
    body.pop('snapshot_hash', None); body.pop('verified', None)
    core={'schema':body['schema'],'files':body['files']}
    body['snapshot_hash']=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    out=tmp_path/'baseline.json'; out.write_text(json.dumps(body))
    baseline=ContractDriftSnapshot.load(out)
    assert baseline.verify()
    r=compare_contract_snapshots(baseline,current)
    assert r.raw_drift is False and r.semantic_drift is False
    assert r.items[0].status=='unchanged'


def test_contract_sentinel_relative_snapshot_is_location_independent(tmp_path: Path):
    ids = []
    for root in (tmp_path/'machine_a', tmp_path/'elsewhere'/'machine_b'):
        (root/'aion').mkdir(parents=True); p = root/'aion'/'contracts.py'; p.write_text('X=1\n')
        s = ContractDriftSnapshot.capture({('AION','contracts'): p}, relative_to=root)
        assert s.verify() and s.files[0].path == 'aion/contracts.py'
        ids.append(s.snapshot_hash)
    assert ids[0] == ids[1]
    absolute = ContractDriftSnapshot.capture({('AION','contracts'): tmp_path/'machine_a'/'aion'/'contracts.py'})
    assert absolute.snapshot_hash != ids[0]


def test_contract_sentinel_rejects_empty_or_wrong_schema_baseline(tmp_path: Path):
    import dataclasses
    import pytest
    with pytest.raises(ValueError,match='at least one boundary'):
        ContractDriftSnapshot.capture({})
    p=tmp_path/'c.py';p.write_text('X=1\n')
    good=ContractDriftSnapshot.capture({('AION','contracts'):p})
    bad=dataclasses.replace(good,schema='wrong')
    assert not bad.verify()
    with pytest.raises(ValueError,match='hash/schema'):
        compare_contract_snapshots(bad,good)
