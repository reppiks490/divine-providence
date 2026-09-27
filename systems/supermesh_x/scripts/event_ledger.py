#!/usr/bin/env python3
"""Append-only hash-chain ledger for replayable public market events."""
import copy
import hashlib
import json


def _canon(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def build_ledger_entry(event, previous=None):
    event=copy.deepcopy(event)
    event_time=event.get('event_time') or event.get('published_time')
    if not event_time:
        raise ValueError('event_time or published_time required')
    published=event.get('published_time') or event_time
    retrieved=event.get('retrieved_time') or published
    prior_hash=(previous or {}).get('record_hash')
    payload={
        'event':event,
        'clock':{
            'event_time':event_time,
            'published_time':published,
            'retrieved_time':retrieved,
        },
        'previous_hash':prior_hash,
    }
    digest=hashlib.sha256(_canon(payload).encode('utf-8')).hexdigest()
    payload['record_hash']=digest
    return payload


def verify_ledger(entries):
    previous=None
    for i,entry in enumerate(entries):
        expected=build_ledger_entry(entry['event'], previous=previous)
        if expected['clock'] != entry.get('clock') or expected['previous_hash'] != entry.get('previous_hash') or expected['record_hash'] != entry.get('record_hash'):
            return {'valid':False,'broken_index':i}
        previous=entry
    return {'valid':True,'broken_index':None,'entries':len(entries)}
