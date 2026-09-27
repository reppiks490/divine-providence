#!/usr/bin/env python3
"""Canonicalize and cluster syndicated/reposted public market events."""
from datetime import datetime, timezone
import hashlib
import re


def _parse(ts):
    s=str(ts).strip().replace('Z','+00:00')
    dt=datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _norm_text(text):
    text=str(text).lower()
    text=re.sub(r'https?://\S+','',text)
    text=re.sub(r'[^a-z0-9%$]+',' ',text)
    return ' '.join(text.split())


def canonical_event_key(event, bucket_seconds=120):
    if bucket_seconds <= 0:
        raise ValueError('bucket_seconds must be positive')
    ts=_parse(event.get('published_time') or event.get('event_time'))
    bucket=int(ts.timestamp())//int(bucket_seconds)
    entity=' '.join(str(event.get('entity','unknown')).lower().split())
    text=_norm_text(event.get('text',''))
    raw=f'{entity}|{text}|{bucket}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def cluster_events(events, bucket_seconds=120):
    groups={}
    for event in events:
        key=canonical_event_key(event,bucket_seconds=bucket_seconds)
        groups.setdefault(key,[]).append(event)
    out=[]
    for key,rows in groups.items():
        rows=sorted(rows,key=lambda r:str(r.get('published_time') or r.get('event_time') or ''))
        out.append({
            'cluster_id':key,
            'event_ids':[r.get('id') for r in rows],
            'independent_source_families':len({r.get('source_family','unknown') for r in rows}),
            'first_seen':rows[0].get('published_time') or rows[0].get('event_time'),
            'last_seen':rows[-1].get('published_time') or rows[-1].get('event_time'),
            'representative':dict(rows[0]),
        })
    out.sort(key=lambda r:(r.get('first_seen') or '',r['cluster_id']))
    return out
