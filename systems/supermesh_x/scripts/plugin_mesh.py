#!/usr/bin/env python3
import json
from pathlib import Path


def load_universe(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def resolve_capability(universe, capability, runtime_states=None):
    runtime_states = runtime_states or {}
    candidates=[]
    missing=[]
    for p in universe.get('providers',[]):
        if capability not in p.get('capabilities',[]):
            continue
        state=runtime_states.get(p['id'],'unverified')
        row={'provider':p['id'],'state':state,'priority':p.get('priority',50),'mode':p.get('mode','external')}
        if state in {'ready','available','connected'}:
            candidates.append(row)
        else:
            missing.append(row)
    candidates.sort(key=lambda x:(-x['priority'],x['provider']))
    missing.sort(key=lambda x:(-x['priority'],x['provider']))
    return {'capability':capability,'selected':candidates,'missing':missing}
