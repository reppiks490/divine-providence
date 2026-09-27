import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from capability_catalog import discover_candidates, normalize_descriptor


def test_normalize_descriptor_defaults_and_caps():
    row=normalize_descriptor({
        'name':'alpha','capabilities':['research.search','research.fetch'],
        'runtime_targets':['chatgpt','claude'],'transports':['mcp_http'],
        'auth_modes':['oauth2'],'trust_class':'enterprise'
    })
    assert row['name']=='alpha'
    assert row['capabilities']==['research.fetch','research.search']
    assert row['dynamic'] is False
    assert row['trust_class']=='enterprise'


def test_discovery_requires_caps_and_runtime_compatibility():
    catalog=[
        {'name':'alpha','capabilities':['research.search','research.fetch'],'runtime_targets':['chatgpt'],'transports':['native_tool']},
        {'name':'beta','capabilities':['research.search'],'runtime_targets':['chatgpt','claude'],'transports':['mcp_http']},
        {'name':'gamma','capabilities':['research.search','research.fetch'],'runtime_targets':['claude'],'transports':['mcp_http']},
    ]
    rows=discover_candidates(['research.search','research.fetch'],catalog,runtime='chatgpt')
    assert [r['name'] for r in rows]==['alpha']
