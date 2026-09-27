#!/usr/bin/env python3
"""Construct an auditable point-in-time event replay bundle."""
from datetime import datetime, timezone
import copy
import hashlib
import json


def _parse(ts):
    s=str(ts).strip().replace('Z','+00:00')
    dt=datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _canon(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def build_replay_bundle(event, evidence, market, cutoff):
    cutoff_dt=_parse(cutoff)
    event_time=_parse(event.get('event_time') or event.get('published_time'))
    if event_time > cutoff_dt:
        raise ValueError('event occurs after replay cutoff')
    kept_e=[]
    for row in evidence:
        ts=row.get('available_time') or row.get('published_time') or row.get('retrieved_time')
        if ts and _parse(ts) <= cutoff_dt:
            kept_e.append(copy.deepcopy(row))
    kept_m=[]
    for row in market:
        ts=row.get('observed_time') or row.get('available_time')
        if ts and _parse(ts) <= cutoff_dt:
            kept_m.append(copy.deepcopy(row))
    payload={
        'event':copy.deepcopy(event),
        'evidence':kept_e,
        'market':kept_m,
        'cutoff':cutoff,
        'point_in_time':True,
    }
    payload['bundle_hash']=hashlib.sha256(_canon(payload).encode('utf-8')).hexdigest()
    return payload
