import dataclasses, time
from pathlib import Path
from durable_journal import DurableProofJournal
from proof_journal import ProofJournalTransaction, ProofJournalReplayVerifier
from proof_envelope import EvidenceBinding, ProofEnvelopeBuilder, STAGE_ORDER
from mutation_receipt import MutationLifecycleRecorder


def make_tx(now=100.0, iid='iv-17'):
    action='fp-17'
    bindings=[EvidenceBinding.create(kind=k,action_identity=action,payload={'stage':k}) for k in STAGE_ORDER]
    env=ProofEnvelopeBuilder().build(bindings,now=now,ttl_seconds=1000)
    rec=MutationLifecycleRecorder(intervention_id=iid,action_fingerprint=action,component='svc')
    rec.record('created',timestamp=now); rec.record('mutation_completed',timestamp=now+1)
    mr=rec.finalize()
    result={'intervention_id':iid,'proof_envelope_hash':env.envelope_hash,'mutation_receipt_hash':mr.receipt_hash,
            'action':{'fingerprint':action}}
    return ProofJournalTransaction.create(intervention_id=iid,action_identity=action,result=result,proof_envelope=env,
                                          mutation_receipt=mr,created_at=now+2)

def test_roundtrip_mapping_requires_reverification():
    tx=make_tx(); rebuilt=ProofJournalTransaction.from_mapping(dataclasses.asdict(tx))
    assert ProofJournalReplayVerifier().verify(rebuilt,now=103).valid

def test_durable_frame_roundtrip_replay(tmp_path):
    tx=make_tx(); j=DurableProofJournal(tmp_path/'proof.bin'); j.append(dataclasses.asdict(tx))
    report=j.recover(); assert report.clean and len(report.records)==1
    rebuilt=ProofJournalTransaction.from_mapping(report.records[0].payload)
    assert ProofJournalReplayVerifier().verify(rebuilt,now=103).valid

def test_tampered_durable_payload_cannot_regain_proof(tmp_path):
    tx=make_tx(); payload=dataclasses.asdict(tx); payload['result']['intervention_id']='evil'
    j=DurableProofJournal(tmp_path/'proof.bin'); j.append(payload)
    rebuilt=ProofJournalTransaction.from_mapping(j.recover().records[0].payload)
    assert not ProofJournalReplayVerifier().verify(rebuilt,now=103).valid

def test_loop_recovery_accepts_only_replay_valid(tmp_path):
    from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
    path=tmp_path/'proof.bin'; j=DurableProofJournal(path)
    good=make_tx(iid='good'); bad=dataclasses.asdict(make_tx(iid='bad')); bad['transaction_hash']='0'*64
    j.append(dataclasses.asdict(good)); j.append(bad)
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(path)))
    report,recovered=loop.recover_durable_proofs(now=103)
    assert len(report.records)==2 and [x.intervention_id for x in recovered]==['good']

def test_truncated_tail_does_not_restore_partial_record(tmp_path):
    path=tmp_path/'proof.bin'; j=DurableProofJournal(path); j.append(dataclasses.asdict(make_tx()))
    with path.open('ab') as f: f.write(b'ISJ16')
    from infrastructure_loop import InfrastructureSupervisoryLoop, LoopConfig
    loop=InfrastructureSupervisoryLoop([],config=LoopConfig(durable_proof_journal_path=str(path)))
    report,recovered=loop.recover_durable_proofs(now=103)
    assert report.tail_status=='truncated' and len(recovered)==1

def test_no_durable_sink_is_fail_open():
    from infrastructure_loop import InfrastructureSupervisoryLoop
    report,recovered=InfrastructureSupervisoryLoop([]).recover_durable_proofs(now=103)
    assert report is None and recovered==()
