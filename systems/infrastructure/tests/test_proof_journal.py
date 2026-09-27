import dataclasses
from proof_envelope import EvidenceBinding, ProofEnvelopeBuilder, STAGE_ORDER
from mutation_receipt import MutationLifecycleRecorder
from proof_journal import ProofJournalTransaction, ProofJournalReplayVerifier

def fixture():
    action="fp"; intervention="iv"
    bindings=[EvidenceBinding.create(kind=s,action_identity=action,payload={"stage":s}) for s in STAGE_ORDER]
    env=ProofEnvelopeBuilder().build(bindings,now=10,ttl_seconds=90)
    rec=MutationLifecycleRecorder(intervention_id=intervention,action_fingerprint=action,component="svc")
    rec.record("created",timestamp=10); rec.record("mutation_completed",timestamp=11); mr=rec.finalize()
    result={"action":{"fingerprint":action},"intervention_id":intervention,"proof_envelope_hash":env.envelope_hash,"mutation_receipt_hash":mr.receipt_hash}
    tx=ProofJournalTransaction.create(intervention_id=intervention,action_identity=action,result=result,proof_envelope=env,mutation_receipt=mr,created_at=12)
    return tx

def test_complete_transaction_replays(): assert ProofJournalReplayVerifier().verify(fixture(),now=20).valid
def test_result_tamper_detected():
    x=fixture(); assert not ProofJournalReplayVerifier().verify(dataclasses.replace(x,result={**x.result,"intervention_id":"evil"}),now=20).valid
def test_cross_intervention_substitution_detected():
    x=fixture(); mr=dataclasses.replace(x.mutation_receipt,intervention_id="other")
    assert not ProofJournalReplayVerifier().verify(dataclasses.replace(x,mutation_receipt=mr),now=20).valid
def test_envelope_substitution_detected():
    x=fixture(); env=dataclasses.replace(x.proof_envelope,action_identity="other")
    assert not ProofJournalReplayVerifier().verify(dataclasses.replace(x,proof_envelope=env),now=20).valid
def test_transaction_hash_tamper_detected():
    x=fixture(); assert not ProofJournalReplayVerifier().verify(dataclasses.replace(x,transaction_hash="0"*64),now=20).valid
def test_no_authority_surface():
    assert {"execute","mutate","promote","rollback","acquire","release"}.isdisjoint(dir(ProofJournalReplayVerifier()))
