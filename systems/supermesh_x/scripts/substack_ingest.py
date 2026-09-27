#!/usr/bin/env python3
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


def publication_feed_url(value):
    value=(value or '').strip().rstrip('/')
    if '://' not in value:
        if '.' not in value:
            value=f'{value}.substack.com'
        value='https://'+value
    p=urlparse(value)
    return f'{p.scheme}://{p.netloc}/feed'


def parse_rss(xml_text):
    root=ET.fromstring(xml_text)
    channel=root.find('channel')
    publication=(channel.findtext('title') if channel is not None else None)
    items=[]
    if channel is not None:
        for item in channel.findall('item'):
            items.append({
                'title':item.findtext('title'),
                'canonical_url':item.findtext('link'),
                'published_time':item.findtext('pubDate'),
                'summary':item.findtext('description'),
                'guid':item.findtext('guid'),
                'source_type':'substack_rss'
            })
    return {'publication':publication,'items':items}
