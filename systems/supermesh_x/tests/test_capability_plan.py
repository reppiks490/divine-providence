import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from capability_plan import compile_plan, validate_step, plan_digest


def _candidate(name, score, fingerprint='fp1'):
    return {
        'provider': name,
        'adaptive_score': score,
        'schema_fingerprint': fingerprint,
        'runtime_state': 'ready',
    }


def test_compile_read_plan_selects_primary_and_fallbacks():
    plan = compile_plan(
        request_id='r1',
        capability='market.quote',
        candidates=[_candidate('alpha', 0.92), _candidate('beta', 0.81)],
        source_class='public_web',
    )
    assert plan['capability'] == 'market.quote'
    assert plan['authority']['mode'] == 'read'
    assert plan['authority']['requires_explicit_authorization'] is False
    assert plan['steps'][0]['provider'] == 'alpha'
    assert plan['steps'][0]['fallbacks'] == ['beta']
    assert plan['steps'][0]['schema_fingerprint'] == 'fp1'


def test_broker_orders_are_never_auto_authorized():
    plan = compile_plan(
        request_id='r2',
        capability='broker.orders',
        candidates=[_candidate('ibkr', 0.99)],
        source_class='user_authorized_private',
    )
    assert plan['authority']['mode'] == 'transactional_write'
    assert plan['authority']['requires_explicit_authorization'] is True
    assert plan['auto_execute'] is False


def test_private_raw_data_cannot_flow_to_public_provider():
    step = {
        'provider': 'public-search',
        'provider_visibility': 'public',
        'input_class': 'user_authorized_private',
        'input_fields': ['email_body', 'account_number'],
        'allowed_derived_fields': [],
    }
    out = validate_step(step)
    assert out['allowed'] is False
    assert out['reason'] == 'private_to_public_blocked'


def test_allowlisted_derived_private_features_can_flow_publicly():
    step = {
        'provider': 'market-data',
        'provider_visibility': 'public',
        'input_class': 'derived_private_feature',
        'input_fields': ['portfolio_beta_bucket'],
        'allowed_derived_fields': ['portfolio_beta_bucket'],
    }
    out = validate_step(step)
    assert out['allowed'] is True


def test_schema_drift_forces_rediscovery_before_execution():
    plan = compile_plan(
        request_id='r3',
        capability='market.quote',
        candidates=[_candidate('alpha', 0.9, 'oldfp')],
        source_class='public_web',
        observed_schema_fingerprints={'alpha': 'newfp'},
    )
    assert plan['steps'][0]['preflight'] == 'rediscover'
    assert plan['steps'][0]['executable'] is False


def test_plan_digest_is_deterministic_and_excludes_runtime_secrets():
    plan = compile_plan(
        request_id='r4',
        capability='market.quote',
        candidates=[_candidate('alpha', 0.9)],
        source_class='public_web',
        runtime_secrets={'api_key': 'SECRET'},
    )
    first = plan_digest(plan)
    second = plan_digest(plan)
    assert first == second
    assert 'SECRET' not in str(plan)
    assert len(first) == 64
