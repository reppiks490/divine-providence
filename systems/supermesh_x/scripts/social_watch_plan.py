#!/usr/bin/env python3
"""Build public-only social/public-statement acquisition plans with fallbacks."""


def build_watch_plan(entity, capabilities):
    lanes=[]
    if capabilities.get('social.public.direct'):
        lanes.append({'mode':'direct_public_social','capability':'social.public.direct','priority':1})
    if capabilities.get('research.search'):
        lanes.append({'mode':'search','capability':'research.search','priority':2})
    if capabilities.get('research.crawl'):
        lanes.append({'mode':'crawl','capability':'research.crawl','priority':3})
    if capabilities.get('media.youtube'):
        lanes.append({'mode':'video','capability':'media.youtube','priority':4})
    if not lanes:
        lanes.append({'mode':'unavailable','capability':None,'priority':99})
    return {
        'entity_id':entity.get('id'),
        'channels':list(entity.get('public_channels',[])),
        'public_only':True,
        'lanes':lanes,
        'dedupe_key':'content_hash+published_time+canonical_source',
        'required_times':['published_time','retrieved_time'],
    }
