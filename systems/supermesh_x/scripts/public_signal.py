#!/usr/bin/env python3
"""Normalize public-figure signals for market-impact analysis."""
import hashlib


def normalize_signal(raw):
    signal_type = raw.get('signal_type') or ('social_post' if raw.get('platform') else 'public_statement')
    if signal_type == 'private_location' or raw.get('public_only') is False:
        raise ValueError('Only public, lawfully accessible signals are supported')
    published = raw.get('published_time') or raw.get('event_time')
    if not published:
        raise ValueError('published_time or event_time is required')
    text = raw.get('text','')
    source = raw.get('source','')
    digest = hashlib.sha256((source+'\n'+text+'\n'+published).encode('utf-8')).hexdigest()
    return {
        'entity': raw.get('entity','unknown'),
        'signal_type': signal_type,
        'platform': raw.get('platform','public_source'),
        'event_time': published,
        'published_time': published,
        'retrieved_time': raw.get('retrieved_time'),
        'text': text,
        'topics': list(raw.get('topics',[])),
        'asset_mentions': list(raw.get('asset_mentions',[])),
        'content_hash': digest,
        'public_only': True,
        'provenance': {
            'source': source,
            'provider': raw.get('provider'),
            'source_class': raw.get('source_class','public_web'),
        },
    }
