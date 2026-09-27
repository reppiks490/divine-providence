#!/usr/bin/env python3
"""Generate a source-diversification plan from a SuperMesh-X domain.

The planner is intentionally deterministic and provider-agnostic. A runtime adapter can
bind the returned capability classes to actual installed tools.
"""
import argparse, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAP=json.loads((ROOT/'config/capability-map.json').read_text())

ESCALATION={
  'research': [
    ['primary_official','structured_provider'],
    ['public_web','reputable_news'],
    ['scholarly','code_repository','community']
  ],
  'finance': [
    ['structured_provider'],
    ['primary_official','regulatory'],
    ['reputable_news']
  ],
  'crypto': [
    ['structured_provider'],
    ['primary_official','code_repository'],
    ['public_web']
  ],
  'coding': [
    ['code_repository','user_authorized_private'],
    ['primary_official']
  ],
  'learning': [
    ['primary_official','user_authorized_private'],
    ['scholarly','public_web']
  ]
}

def plan(domain, depth='standard'):
    if domain not in MAP:
        raise SystemExit(f'unknown domain: {domain}')
    levels=ESCALATION[domain]
    take={'minimal':1,'standard':2,'deep':len(levels)}[depth]
    return {
      'domain': domain,
      'depth': depth,
      'capabilities': MAP[domain]['capabilities'],
      'source_waves': [
        {'wave':i+1,'source_classes':classes}
        for i,classes in enumerate(levels[:take])
      ],
      'stop_rule':'stop when remaining sources are duplicative or low expected information gain'
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('domain', choices=sorted(MAP))
    ap.add_argument('--depth', choices=['minimal','standard','deep'], default='standard')
    args=ap.parse_args()
    print(json.dumps(plan(args.domain,args.depth), indent=2))

if __name__=='__main__': main()
