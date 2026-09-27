import dataclasses, pytest
from mutation_receipt import MutationLifecycleRecorder

def _receipt():
    r=MutationLifecycleRecorder(intervention_id="iv-1",action_fingerprint="fp",component="svc",
                                lease_owner="intervention:iv-1",lease_scopes=("component:svc",))
    r.record("created",timestamp=1); r.record("lease_acquired",timestamp=2)
    r.record("mutation_started",timestamp=3); r.record("mutation_completed",timestamp=4,details={"success":True})
    r.record("lease_released",timestamp=5); return r.finalize()

def test_chain_verifies_and_binds_exact_intervention():
    x=_receipt(); assert x.verify_integrity(); assert x.intervention_id=="iv-1"
def test_transition_tampering_breaks_integrity():
    x=_receipt(); bad=dataclasses.replace(x.transitions[2],details={"forged":True})
    assert not dataclasses.replace(x,transitions=x.transitions[:2]+(bad,)+x.transitions[3:]).verify_integrity()
def test_intervention_substitution_breaks_integrity():
    assert not dataclasses.replace(_receipt(),intervention_id="other").verify_integrity()
def test_chronology_fail_closed():
    r=MutationLifecycleRecorder(intervention_id="iv",action_fingerprint="fp",component="svc"); r.record("created",timestamp=2)
    with pytest.raises(ValueError): r.record("mutation_started",timestamp=1)
def test_finalized_append_closed():
    r=MutationLifecycleRecorder(intervention_id="iv",action_fingerprint="fp",component="svc"); r.record("created",timestamp=1); r.finalize()
    with pytest.raises(RuntimeError): r.record("mutation_started",timestamp=2)
def test_no_mutation_authority_surface():
    assert {"execute","mutate","promote","rollback","acquire","release"}.isdisjoint(set(dir(_receipt())))
