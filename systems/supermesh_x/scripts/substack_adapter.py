#!/usr/bin/env python3
from urllib.parse import urlparse


def feed_url(publication_url):
    u=(publication_url or '').strip().rstrip('/')
    if not u.startswith(('http://','https://')):
        u='https://'+u
    parsed=urlparse(u)
    return f'{parsed.scheme}://{parsed.netloc}/feed'


def ingestion_plan(api_authorized=False, rss_available=True, private_email_authorized=False):
    lanes=[]
    if api_authorized:
        lanes.append('developer_api')
    if rss_available:
        lanes.append('rss')
    lanes.append('public_web')
    lanes.append('search_index')
    if private_email_authorized:
        lanes.append('authorized_inbox')
    return lanes


def normalize_entry(entry):
    return {
        'title':entry.get('title'),
        'author':entry.get('author'),
        'published_time':entry.get('published_time') or entry.get('published'),
        'url':entry.get('url') or entry.get('link'),
        'summary':entry.get('summary'),
        'source_class':'substack_publication',
    }
