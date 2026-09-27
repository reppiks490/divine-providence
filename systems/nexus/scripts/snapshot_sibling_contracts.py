from __future__ import annotations
import argparse, json
from pathlib import Path
from nexus.contract_sentinel import ContractDriftSnapshot, compare_contract_snapshots


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--aion',required=True); p.add_argument('--argus',required=True)
    p.add_argument('--athena',required=True); p.add_argument('--daedalus',required=True)
    p.add_argument('--out',required=True); p.add_argument('--baseline')
    p.add_argument('--relative-to',help='record paths relative to this root (path-independent baseline)')
    a=p.parse_args()
    boundaries={
        ('AION','contracts'):Path(a.aion)/'aion'/'contracts.py',
        ('AION','store'):Path(a.aion)/'aion'/'store.py',
        ('ARGUS','contracts'):Path(a.argus)/'src'/'argus'/'contracts.py',
        ('ATHENA','contracts'):Path(a.athena)/'src'/'athena'/'contracts.py',
        ('DAEDALUS','bridge'):Path(a.daedalus)/'src'/'daedalus'/'bridge.py',
    }
    snap=ContractDriftSnapshot.capture(boundaries,relative_to=a.relative_to); snap.save(a.out)
    result={'snapshot':snap.to_dict()}
    exit_code=0
    if a.baseline:
        report=compare_contract_snapshots(ContractDriftSnapshot.load(a.baseline),snap)
        result['drift']=report.to_dict(); exit_code=2 if report.semantic_drift else 0
    print(json.dumps(result,sort_keys=True,indent=2))
    raise SystemExit(exit_code)

if __name__=='__main__': main()
