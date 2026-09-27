import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from routing_kernel import route_capability

CATALOG=[
  {'name':'alpha','capabilities':['research.search'],'runtime_targets':['chatgpt'],'transports':['native_tool'],'auth_modes':['none'],'priority':90},
  {'name':'beta','capabilities':['research.search'],'runtime_targets':['chatgpt'],'transports':['mcp_http'],'auth_modes':['oauth2'],'priority':95},
  {'name':'gamma','capabilities':['research.search'],'runtime_targets':['chatgpt'],'transports':['mcp_http'],'auth_modes':['none'],'priority':80},
]
RUNTIME={'supported_transports':['native_tool','mcp_http'],'credential_modes':['none']}


def test_route_blocks_auth_mismatch_and_open_breaker():
    states={
      'alpha': {'state':'ready','health':0.8},
      'beta': {'state':'ready','health':1.0},
      'gamma': {'state':'ready','health':0.9},
    }
    breakers={'gamma': {'consecutive_failures':4,'last_failure_ts':100}}
    plan=route_capability('research.search',states,CATALOG,RUNTIME,breakers,now=110,limit=3)
    assert [r['provider'] for r in plan['selected']]==['alpha']
    reasons={r['provider']:r['block_reason'] for r in plan['blocked']}
    assert reasons['beta']=='auth_unavailable'
    assert reasons['gamma']=='circuit_open'


def test_route_keeps_unverified_provider_blocked():
    plan=route_capability('research.search',{},CATALOG,RUNTIME,{},now=0)
    assert not plan['selected']
    assert {r['provider'] for r in plan['blocked']}=={'alpha','beta','gamma'}
