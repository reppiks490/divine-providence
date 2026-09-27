import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_mesh_planner_cli_emits_json_plan(tmp_path):
    state=tmp_path/'state.json'
    state.write_text(json.dumps({'providers':{
      'twelve-data': {'state':'ready','health':0.9},
      'tickerlayer': {'state':'ready','health':0.8}
    }}))
    p=subprocess.run([sys.executable, str(ROOT/'scripts/mesh_planner.py'), 'market.quote', '--state-file', str(state)], capture_output=True, text=True)
    assert p.returncode==0
    data=json.loads(p.stdout)
    assert data['selected'][0]['provider']=='twelve-data'
