import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from mrtr_guard import validate_input_required, build_resume_envelope, validate_task_descriptor


def test_input_required_requires_opaque_state_and_bounded_requests():
    bad = validate_input_required({'resultType':'input_required','inputRequests':{}})
    assert bad['allowed'] is False
    assert bad['reason'] == 'missing_request_state'
    ok = validate_input_required({'resultType':'input_required','requestState':'opaque-1','inputRequests':{'q1':{'method':'elicitation/create'}}})
    assert ok['allowed'] is True


def test_input_required_rejects_deprecated_sampling_and_roots_on_modern_protocol():
    for method in ('sampling/createMessage','roots/list'):
        r = validate_input_required({'resultType':'input_required','requestState':'s','inputRequests':{'x':{'method':method}}}, protocol_version='2026-07-28')
        assert r['allowed'] is False
        assert r['reason'] == 'deprecated_modern_input_request'


def test_resume_echoes_state_and_only_known_responses():
    prior = {'resultType':'input_required','requestState':'opaque-9','inputRequests':{'a':{'method':'elicitation/create'}}}
    env = build_resume_envelope(prior, {'a':{'action':'accept','content':{'choice':'yes'}}, 'evil':{'x':1}})
    assert env['requestState'] == 'opaque-9'
    assert set(env['inputResponses']) == {'a'}


def test_round_limit_fails_closed():
    r = validate_input_required({'resultType':'input_required','requestState':'s','inputRequests':{'a':{'method':'elicitation/create'}}}, round_number=11, max_rounds=10)
    assert r['allowed'] is False
    assert r['reason'] == 'mrtr_round_limit_exceeded'


def test_task_descriptor_requires_unguessable_id_and_no_enumeration_contract():
    short = validate_task_descriptor({'taskId':'1234','status':'working'})
    assert short['allowed'] is False
    ok = validate_task_descriptor({'taskId':'a7d4c9028f5e4b1bbd72e99ac0325d12','status':'working'})
    assert ok['allowed'] is True
    assert ok['enumeration_allowed'] is False
