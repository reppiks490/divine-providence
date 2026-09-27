from __future__ import annotations
import argparse,json
from nexus.sibling_validation import validate_sibling_contracts

def main():
    p=argparse.ArgumentParser();p.add_argument('--aion',required=True);p.add_argument('--argus',required=True);p.add_argument('--athena',required=True);p.add_argument('--daedalus',required=True);p.add_argument('--out')
    a=p.parse_args();r=validate_sibling_contracts(aion_root=a.aion,argus_root=a.argus,athena_root=a.athena,daedalus_root=a.daedalus);payload=r.to_dict();text=json.dumps(payload,indent=2,sort_keys=True)
    if a.out:open(a.out,'w').write(text+'\n')
    print(text);raise SystemExit(0 if r.passed else 1)
if __name__=='__main__':main()
