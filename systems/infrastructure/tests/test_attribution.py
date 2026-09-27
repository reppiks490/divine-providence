from attribution import Sample, AttributionObservation, AttributionPolicy, CounterfactualAttributor


def s(t, score, c=.9): return Sample(t, score, c)
def obs(**kw):
    base=dict(component='svc', action_fingerprint='a', intervention_ts=10,
              treated_pre=(s(1,.4),s(2,.4)), treated_post=(s(11,.6),s(12,.6)))
    base.update(kw); return AttributionObservation(**base)

def test_equal_control_recovery_gets_no_positive_credit():
    r=CounterfactualAttributor().evaluate(obs(control_component='ctrl', control_pre=(s(1,.4),s(2,.4)), control_post=(s(11,.6),s(12,.6))))
    assert r.attributable_delta == 0 and not r.positive_learning_eligible

def test_treated_improvement_exceeds_stable_control():
    r=CounterfactualAttributor().evaluate(obs(control_component='ctrl', control_pre=(s(1,.4),s(2,.4)), control_post=(s(11,.41),s(12,.41))))
    assert r.evidence_method=='explicit_control' and r.positive_learning_eligible and r.evidence_hash

def test_overlapping_mutation_contaminates():
    r=CounterfactualAttributor().evaluate(obs(mutation_events=('m1',)))
    assert r.contaminated and not r.positive_learning_eligible

def test_protected_scope_overlap_contaminates():
    r=CounterfactualAttributor().evaluate(obs(protected_scope_events=('fd:a',)))
    assert r.contaminated

def test_stable_pretrend_fallback_can_be_eligible():
    r=CounterfactualAttributor().evaluate(obs(treated_pre=(s(1,.38),s(2,.39),s(3,.40))))
    assert r.evidence_method=='local_pretrend' and r.positive_learning_eligible

def test_unstable_pretrend_is_insufficient():
    r=CounterfactualAttributor().evaluate(obs(treated_pre=(s(1,.2),s(2,.5),s(3,.4))))
    assert r.evidence_method=='insufficient' and not r.positive_learning_eligible

def test_low_confidence_denies_positive_credit():
    r=CounterfactualAttributor().evaluate(obs(treated_pre=(s(1,.4,.2),s(2,.4,.2))))
    assert not r.positive_learning_eligible

def test_nonmonotonic_timestamp_contaminates():
    r=CounterfactualAttributor().evaluate(obs(treated_pre=(s(2,.4),s(1,.4))))
    assert r.contaminated

def test_bad_proof_contaminates():
    r=CounterfactualAttributor().evaluate(obs(proof_valid=False))
    assert r.contaminated

def test_negative_attribution_is_not_positive_eligible():
    r=CounterfactualAttributor().evaluate(obs(control_component='ctrl', control_pre=(s(1,.4),s(2,.4)), control_post=(s(11,.8),s(12,.8))))
    assert r.attributable_delta < 0 and not r.positive_learning_eligible

def test_canonical_hash_is_stable():
    a=CounterfactualAttributor(); o=obs(control_component='ctrl', control_pre=(s(1,.4),s(2,.4)), control_post=(s(11,.41),s(12,.41)))
    assert a.evaluate(o).evidence_hash == a.evaluate(o).evidence_hash

def test_exception_fails_closed():
    class Boom(CounterfactualAttributor):
        def _evaluate(self, obs): raise RuntimeError('boom')
    r=Boom().evaluate(obs()); assert r.contaminated and not r.positive_learning_eligible

def test_v6_causal_success_without_v7_attribution_gets_no_credit():
    from infrastructure_loop import ActionResult, OutcomeMemory, ProposedAction, ActionClass
    a=ProposedAction('svc',ActionClass.TUNE,'tune',{},.1,.1,.9,.9,'x').finalize(); m=OutcomeMemory()
    m.update(ActionResult(a,True,.4,.8,1,causal_eligible=True,evidence_hash='proof'))
    assert m.prior(a)==(0.0,0.0)

def test_attributed_success_gets_credit():
    from infrastructure_loop import ActionResult, OutcomeMemory, ProposedAction, ActionClass
    a=ProposedAction('svc',ActionClass.TUNE,'tune',{},.1,.1,.9,.9,'x').finalize(); m=OutcomeMemory()
    m.update(ActionResult(a,True,.4,.8,1,causal_eligible=True,evidence_hash='proof',attribution_eligible=True,attribution_hash='attr'))
    assert m.prior(a)[0] > 0
