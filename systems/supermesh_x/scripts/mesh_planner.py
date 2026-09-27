#!/usr/bin/env python3
"""Capability planning that combines registry priority with runtime provider state."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from provider_state import rank_candidates


def _providers_for(capability):
    registry = json.loads((ROOT / 'config' / 'providers.json').read_text())['providers']
    rows = []
    for provider in registry:
        if capability in provider.get('capabilities', []):
            rows.append(provider)
    rows.sort(key=lambda p: p.get('priority', 0), reverse=True)
    return rows


def plan_capability(capability, states, limit=3):
    providers = _providers_for(capability)
    names = [p['name'] for p in providers]
    normalized = {}
    for name in names:
        if name in states:
            normalized[name] = states[name]
        else:
            normalized[name] = {'state': 'unverified', 'health': 0.0}

    ranked = rank_candidates(names, normalized)
    priority = {p['name']: p.get('priority', 0) for p in providers}
    for row in ranked:
        row['registry_priority'] = priority[row['provider']]
        row['combined_score'] = round(row['score'] * 0.75 + (priority[row['provider']] / 100.0) * 0.25, 6)
    ranked.sort(key=lambda row: (row['routable'], row['combined_score']), reverse=True)

    selected = [r for r in ranked if r['routable']][:limit]
    blocked = [r for r in ranked if not r['routable']]
    return {
        'capability': capability,
        'selected': selected,
        'blocked': blocked,
        'policy': 'runtime-readiness-first with registry-priority tie-break',
    }


def _load_states(path):
    if not path:
        return {}
    payload=json.loads(Path(path).read_text())
    return payload.get('providers', payload)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('capability')
    ap.add_argument('--state-file')
    ap.add_argument('--limit',type=int,default=3)
    args=ap.parse_args()
    print(json.dumps(plan_capability(args.capability,_load_states(args.state_file),args.limit),indent=2))


if __name__=='__main__':
    main()
