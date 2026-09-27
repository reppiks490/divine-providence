import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from adaptive_director import direct_capability, replacement_plan

CATALOG = [
    {'name':'alpha','capabilities':['market.quote'],'runtime_targets':['chatgpt'],'transports':['native_tool'],'auth_modes':['none'],'priority':80},
    {'name':'beta','capabilities':['market.quote'],'runtime_targets':['chatgpt'],'transports':['native_tool'],'auth_modes':['none'],'priority':70},
    {'name':'gamma','capabilities':['market.quote'],'runtime_targets':['chatgpt'],'transports':['native_tool'],'auth_modes':['oauth'],'priority':100},
]
RUNTIME = {'name':'chatgpt','supported_transports':['native_tool'],'credential_modes':['none']}


def test_director_uses_feedback_and_breakers():
    states = {'alpha':{'state':'ready','health':0.9}, 'beta':{'state':'ready','health':0.9}, 'gamma':{'state':'ready','health':1.0}}
    feedback = {'alpha':{'market.quote':{'score':0.3}}, 'beta':{'market.quote':{'score':0.95}}}
    breakers = {'alpha':{'consecutive_failures':0}, 'beta':{'consecutive_failures':0}}
    out = direct_capability('market.quote', states, CATALOG, RUNTIME, feedback=feedback, breaker_metrics=breakers, now=100)
    assert out['selected'][0]['provider'] == 'beta'
    assert any(x['provider']=='gamma' and x['block_reason']=='auth_unavailable' for x in out['blocked'])


def test_replacement_plan_promotes_fallback_when_current_breaks():
    plan = replacement_plan(
        current_provider='alpha',
        capability='market.quote',
        surface_change={'breaking':True,'removed':['quote'],'changed':[]},
        states={'alpha':{'state':'degraded','health':0.3},'beta':{'state':'ready','health':0.95}},
        catalog=CATALOG,
        runtime_profile=RUNTIME,
        feedback={'beta':{'market.quote':{'score':0.9}}},
        now=100,
    )
    assert plan['action'] == 'replace'
    assert plan['replacement'] == 'beta'
