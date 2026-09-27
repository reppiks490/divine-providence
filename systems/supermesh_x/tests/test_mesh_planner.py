import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mesh_planner', ROOT/'scripts/mesh_planner.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_plan_prefers_ready_provider_over_higher_priority_preflight_provider():
    states={
      'twelve-data': {'state':'preflight_required','health':1.0},
      'tickerlayer': {'state':'ready','health':0.8},
    }
    plan=mod.plan_capability('market.quote', states=states)
    assert plan['selected'][0]['provider']=='tickerlayer'

def test_plan_keeps_non_routable_provider_as_blocked_candidate():
    states={'blockscout': {'state':'preflight_required','health':1.0}}
    plan=mod.plan_capability('chain.contract', states=states)
    assert not plan['selected']
    assert plan['blocked'][0]['provider']=='blockscout'
    assert plan['blocked'][0]['state']=='preflight_required'

def test_plan_marks_unknown_availability_as_unverified_not_ready():
    plan=mod.plan_capability('market.quote', states={})
    assert not plan['selected']
    assert plan['blocked']
