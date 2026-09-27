import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from discovery_receipt import build_receipt


def test_receipt_tracks_exposed_and_withheld_without_payloads():
    candidates = [
        {'id':'a','score':0.99,'capabilities':['market.quote'],'raw_args':{'secret':'x'}},
        {'id':'b','score':0.90,'capabilities':['market.quote'],'output':'sensitive'},
        {'id':'c','score':0.80,'capabilities':['market.quote']},
    ]
    r = build_receipt('market quote provider', candidates, limit=2, status='complete', stop_reason='limit')
    assert [x['id'] for x in r['exposed']] == ['a','b']
    assert r['withheld_count'] == 1
    assert r['top_withheld'][0]['id'] == 'c'
    blob = str(r)
    assert 'secret' not in blob
    assert 'sensitive' not in blob
