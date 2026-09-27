import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_named_seed_profiles_and_dynamic_roles():
    data = json.loads((ROOT/'config/market-movers.json').read_text())
    names = {x['name'] for x in data['entities']}
    assert {'Donald Trump','Elon Musk','Kevin Warsh','Scott Bessent','Jensen Huang','Jamie Dimon'} <= names
    assert data['dynamic_role_buckets']['central_bank_leadership']['resolve_current_holder_at_runtime'] is True
    assert data['policy']['political_persuasion'] is False
