#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def _registry():
    return json.loads((ROOT/'config'/'integration-registry.json').read_text(encoding='utf-8'))


def select_integrations(capability, runtime_states=None):
    runtime_states=runtime_states or {}
    selected=[]; deferred=[]
    for item in _registry()['integrations']:
        if capability not in item.get('capabilities',[]):
            continue
        state=runtime_states.get(item['id'],'unverified')
        row=dict(item); row['state']=state
        if state in {'ready','connected','available'}:
            selected.append(row)
        else:
            deferred.append(row)
    selected.sort(key=lambda x:(-x.get('priority',0),x['id']))
    deferred.sort(key=lambda x:(-x.get('priority',0),x['id']))
    return {'capability':capability,'selected':selected,'deferred':deferred}
