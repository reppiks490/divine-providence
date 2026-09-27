import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from social_watch_plan import build_watch_plan


def test_watch_plan_prefers_direct_public_source_then_fallbacks():
    plan=build_watch_plan(
      {'id':'elon_musk','public_channels':['x','official_company','video']},
      {'social.public.direct':False,'research.search':True,'research.crawl':True,'media.youtube':True}
    )
    assert plan['public_only'] is True
    assert plan['lanes'][0]['mode'] in {'search','crawl','video'}
    assert any(x['mode']=='search' for x in plan['lanes'])


def test_watch_plan_never_requests_private_location_or_nonpublic_data():
    plan=build_watch_plan({'id':'donald_trump','public_channels':['public_social']},{'research.search':True})
    assert all('private' not in str(x).lower() for x in plan['lanes'])
