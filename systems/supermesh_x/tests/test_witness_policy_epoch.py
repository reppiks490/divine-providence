import json
import pytest

from scripts.witnessed_transparency import Witness, WitnessError, RFC9162WitnessedCheckpointLedger
from scripts.witness_policy_epoch import (
    WitnessPolicyEpoch, DurableWitnessPolicyRoot, EpochWitnessRegistry,
    policy_rotation_signature,
)


def make_policy(epoch, pairs, threshold, revoked=()):
    return WitnessPolicyEpoch(epoch=epoch,
        keys={w.witness_id: w.public_key_bytes() for w in pairs},
        threshold=threshold, revoked_key_ids=set(revoked))


def test_rotation_requires_exact_next_epoch_and_dual_threshold(tmp_path):
    a,b,c = Witness.generate('a'), Witness.generate('b'), Witness.generate('c')
    p1 = make_policy(1, [a,b], 2)
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path/'policy.json', p1)
    p2 = make_policy(2, [b,c], 2)
    st = root.make_rotation_statement(p2)
    receipts = [policy_rotation_signature(w, st) for w in (a,b,c)]
    rec = root.rotate(p2, receipts)
    assert root.policy.epoch == 2
    assert rec['old_signers'] == ['a','b']
    assert rec['new_signers'] == ['b','c']

    p4 = make_policy(4, [b,c], 2)
    with pytest.raises(WitnessError, match='exactly one epoch'):
        root.rotate(p4, [])


def test_rotation_fails_if_either_side_lacks_threshold(tmp_path):
    a,b,c = Witness.generate('a'), Witness.generate('b'), Witness.generate('c')
    p1 = make_policy(1, [a,b], 2)
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path/'policy.json', p1)
    p2 = make_policy(2, [b,c], 2)
    st = root.make_rotation_statement(p2)
    with pytest.raises(WitnessError, match='current-policy'):
        root.rotate(p2, [policy_rotation_signature(b,st), policy_rotation_signature(c,st)])
    with pytest.raises(WitnessError, match='next-policy'):
        root.rotate(p2, [policy_rotation_signature(a,st), policy_rotation_signature(b,st)])


def test_revocation_and_duplicate_key_aliases_fail_closed(tmp_path):
    a,b = Witness.generate('a'), Witness.generate('b')
    with pytest.raises(WitnessError, match='duplicate public key'):
        WitnessPolicyEpoch(1, {'a':a.public_key_bytes(),'alias':a.public_key_bytes()}, 1)
    p = make_policy(1,[a,b],1,revoked={'a'})
    root = DurableWitnessPolicyRoot.bootstrap(tmp_path/'policy.json',p)
    reg = EpochWitnessRegistry(root)
    statement={'hello':'world','policy_epoch':1,'policy_digest':p.digest()}
    with pytest.raises(WitnessError, match='revoked'):
        reg.verify('a', statement, a.sign(statement))
    assert reg.verify('b', statement, b.sign(statement))


def test_policy_metadata_cannot_encode_execution_authority():
    a=Witness.generate('a')
    with pytest.raises(WitnessError, match='authority'):
        WitnessPolicyEpoch(1, {'a':a.public_key_bytes()}, 1, metadata={'broker.orders':True})


def test_epoch_registry_binds_checkpoint_signatures_and_survives_rotation(tmp_path):
    a,b,c = Witness.generate('a'), Witness.generate('b'), Witness.generate('c')
    p1=make_policy(1,[a,b],2)
    root=DurableWitnessPolicyRoot.bootstrap(tmp_path/'policy.json',p1)
    reg=EpochWitnessRegistry(root)
    ledger=RFC9162WitnessedCheckpointLedger(reg,'log-A')
    c1=ledger.checkpoint([b'x'],[a,b])
    assert c1['policy_epoch']==1 and c1['policy_digest']==p1.digest()

    p2=make_policy(2,[b,c],2)
    st=root.make_rotation_statement(p2)
    root.rotate(p2,[policy_rotation_signature(w,st) for w in (a,b,c)])
    c2=ledger.checkpoint([b'x',b'y'],[b,c])
    assert c2['policy_epoch']==2 and c2['policy_digest']==p2.digest()
    assert reg.verify('b', {k:c1[k] for k in ('schema','log_id','tree_algorithm','tree_size','root','previous_tree_size','previous_root','consistency_digest','policy_epoch','policy_digest')}, c1['receipts'][1]['signature'])


def test_policy_root_load_revalidates_rotation_chain(tmp_path):
    a,b,c=Witness.generate('a'),Witness.generate('b'),Witness.generate('c')
    p1=make_policy(1,[a,b],2); path=tmp_path/'policy.json'
    root=DurableWitnessPolicyRoot.bootstrap(path,p1)
    p2=make_policy(2,[b,c],2); st=root.make_rotation_statement(p2)
    root.rotate(p2,[policy_rotation_signature(w,st) for w in (a,b,c)])
    loaded=DurableWitnessPolicyRoot.load(path)
    assert loaded.policy.digest()==p2.digest()
    doc=json.loads(path.read_text()); doc['payload']['policies']['2']['threshold']=1
    import hashlib
    raw=json.dumps(doc['payload'],sort_keys=True,separators=(',',':')).encode()
    doc['sha256']=hashlib.sha256(raw).hexdigest(); path.write_text(json.dumps(doc))
    with pytest.raises(WitnessError): DurableWitnessPolicyRoot.load(path)
