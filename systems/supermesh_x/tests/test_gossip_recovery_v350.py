import json
import pytest
from scripts.witnessed_transparency import Witness, WitnessError, RFC9162WitnessedCheckpointLedger
from scripts.witness_policy_epoch import WitnessPolicyEpoch, DurableWitnessPolicyRoot, EpochWitnessRegistry
from scripts.durable_gossip_journal import DurableGossipJournal


def setup(tmp_path):
    a,b=Witness.generate('a'),Witness.generate('b')
    p=WitnessPolicyEpoch(1,{w.witness_id:w.public_key_bytes() for w in (a,b)},2)
    root=DurableWitnessPolicyRoot.bootstrap(tmp_path/'policy.json',p)
    reg=EpochWitnessRegistry(root); ledger=RFC9162WitnessedCheckpointLedger(reg,'log-A')
    return a,b,reg,ledger


def test_strict_load_rejects_torn_tail_but_recovery_quarantines_it(tmp_path):
    a,b,reg,ledger=setup(tmp_path); path=tmp_path/'gossip.jsonl'
    j=DurableGossipJournal(path,reg); cp=ledger.checkpoint([b'a'],[a,b]); j.append(cp)
    with path.open('ab') as fh: fh.write(b'{"schema":1,"sequence":2')
    with pytest.raises(WitnessError): DurableGossipJournal.load(path,reg)
    recovered=DurableGossipJournal.recover(path,reg,quarantine_dir=tmp_path/'quarantine')
    assert recovered.latest('log-A')['tree_size']==1
    assert recovered.sequence==1
    assert recovered.recovery_report['quarantined_bytes']>0
    assert recovered.recovery_report['quarantine_path']
    assert json.loads(path.read_text().strip())['sequence']==1


def test_recovery_refuses_valid_json_integrity_tamper(tmp_path):
    a,b,reg,ledger=setup(tmp_path); path=tmp_path/'gossip.jsonl'
    j=DurableGossipJournal(path,reg); j.append(ledger.checkpoint([b'a'],[a,b]))
    row=json.loads(path.read_text()); row['entry_digest']='00'*32; path.write_text(json.dumps(row)+'\n')
    with pytest.raises(WitnessError,match='integrity'): DurableGossipJournal.recover(path,reg,quarantine_dir=tmp_path/'q')
