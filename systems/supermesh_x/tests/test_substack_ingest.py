import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from substack_ingest import publication_feed_url, parse_rss


def test_publication_feed_url():
    assert publication_feed_url('example') == 'https://example.substack.com/feed'
    assert publication_feed_url('https://example.substack.com') == 'https://example.substack.com/feed'


def test_parse_rss_normalizes_items():
    xml = '''<rss><channel><title>Demo</title><item><title>Macro Note</title><link>https://demo.substack.com/p/macro</link><pubDate>Thu, 24 Sep 2026 12:00:00 GMT</pubDate><description>Rates and oil</description><guid>abc</guid></item></channel></rss>'''
    out = parse_rss(xml)
    assert out['publication'] == 'Demo'
    assert out['items'][0]['title'] == 'Macro Note'
    assert out['items'][0]['canonical_url'].endswith('/p/macro')
    assert out['items'][0]['source_type'] == 'substack_rss'
