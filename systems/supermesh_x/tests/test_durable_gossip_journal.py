import json
import pytest
from scripts.witnessed_transparency import Witness, WitnessError, RFC9162WitnessedCheckpointLedger
from scripts.witness_policy_epoch import WitnessPolicyEpoch, DurableWitnessPolicyRoot, EpochWitnessRegistry, policy_rotation_signature
from scripts.durable_gossip_journal import DurableGossipJournal


def setup(tmp_path):
    a,b,c=Witness.generate('a'),Witness.generate('b'),Witness.generate('c')
    p1=WitnessPolicyEpoch(1,{w.witness_id:w.public_key_bytes() for w in (a,b)},2)
    root=DurableWitnessPolicyRoot.bootstrap(tmp_path/'policy.json',p1)
    reg=EpochWitnessRegistry(root); ledger=RFC9162WitnessedCheckpointLedger(reg,'log-A')
    journal=DurableGossipJournal(tmp_path/'gossip.jsonl',reg)
    return a,b,c,root,reg,ledger,journal


def test_journal_replays_across_policy_rotation(tmp_path):
    a,b,c,root,reg,ledger,j=setup(tmp_path)
    c1=ledger.checkpoint([b'a'],[a,b]); j.append(c1)
    p2=WitnessPolicyEpoch(2,{w.witness_id:w.public_key_bytes() for w in (b,c)},2)
    st=root.make_rotation_statement(p2); root.rotate(p2,[policy_rotation_signature(w,st) for w in (a,b,c)])
    c2=ledger.checkpoint([b'a',b'b'],[b,c]); j.append(c2)
    restored=DurableGossipJournal.load(tmp_path/'gossip.jsonl',reg)
    assert restored.latest('log-A')['tree_size']==2
    assert restored.latest('log-A')['policy_epoch']==2


def test_journal_rejects_stale_policy_for_new_append(tmp_path):
    a,b,c,root,reg,ledger,j=setup(tmp_path)
    old=ledger.checkpoint([b'a'],[a,b]); j.append(old)
    p2=WitnessPolicyEpoch(2,{w.witness_id:w.public_key_bytes() for w in (b,c)},2)
    st=root.make_rotation_statement(p2); root.rotate(p2,[policy_rotation_signature(w,st) for w in (a,b,c)])
    with pytest.raises(WitnessError,match='stale policy epoch'):
        j.append(old)


def test_journal_persists_before_observation_and_rolls_back_on_io_failure(tmp_path,monkeypatch):
    a,b,c,root,reg,ledger,j=setup(tmp_path)
    cp=ledger.checkpoint([b'a'],[a,b])
    monkeypatch.setattr(j,'_append_envelope',lambda envelope: (_ for _ in ()).throw(OSError('disk down')))
    with pytest.raises(WitnessError,match='journal persistence failed'): j.append(cp)
    assert j.latest('log-A') is None


def test_journal_hash_chain_or_signature_tamper_fails_replay(tmp_path):
    a,b,c,root,reg,ledger,j=setup(tmp_path)
    cp=ledger.checkpoint([b'a'],[a,b]); j.append(cp)
    path=tmp_path/'gossip.jsonl'; row=json.loads(path.read_text().strip())
    row['receipt']['root']='ff'*32
    import hashlib
    body={k:row[k] for k in ('schema','sequence','previous_digest','receipt')}
    row['entry_digest']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    path.write_text(json.dumps(row)+'\n')
    with pytest.raises(WitnessError): DurableGossipJournal.load(path,reg)
