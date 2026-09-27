#!/usr/bin/env python3
"""Small dependency-free capability router for SuperMesh-X.

This does not call providers. It ranks providers from a machine-readable registry so
runtime adapters can bind actual tools safely.
"""
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "providers.json"

def load_registry():
    return json.loads(REGISTRY.read_text())['providers']

def route(capability, available=None, limit=5):
    available = set(available or [])
    rows=[]
    for p in load_registry():
        if capability in p.get('capabilities', []):
            if available and p['name'] not in available:
                continue
            rows.append((p.get('priority', 0), p['name'], bool(p.get('optional'))))
    rows.sort(reverse=True)
    return [{"provider":n,"score":s,"optional":o} for s,n,o in rows[:limit]]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('capability')
    ap.add_argument('--available', nargs='*', default=[])
    ap.add_argument('--limit', type=int, default=5)
    args=ap.parse_args()
    print(json.dumps(route(args.capability,args.available,args.limit), indent=2))

if __name__=='__main__':
    main()
