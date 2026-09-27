#!/usr/bin/env python3
from pathlib import Path
import json, re, sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
for p in ["SKILL.md","manifest.yaml","README.md","config/providers.json","scripts/workspace_isolation.py","scripts/remote_store_adapter.py","references/workspace-isolation-remote-store.md","scripts/runtime_driver.py","references/runtime-driver-enforcement.md","scripts/runtime_launch_attestation.py","references/runtime-launch-attestation.md","scripts/runtime_evidence_journal.py","references/runtime-evidence-journal.md","scripts/signed_runtime_evidence.py","references/signed-runtime-evidence.md","scripts/trust_transparency.py","references/trust-transparency.md"]:
    if not (ROOT/p).exists(): errors.append(f"missing {p}")
text=(ROOT/'SKILL.md').read_text() if (ROOT/'SKILL.md').exists() else ''
if not text.startswith('---\nname: supermesh-x'):
    errors.append('invalid SKILL.md frontmatter/name')
try:
    reg=json.loads((ROOT/'config/providers.json').read_text())
    names=[p['name'] for p in reg['providers']]
    if len(names)!=len(set(names)): errors.append('duplicate provider names')
    if not any('research.search' in p.get('capabilities',[]) for p in reg['providers']): errors.append('no research.search provider')
except Exception as e:
    errors.append(f'providers.json invalid: {e}')
for schema in ['capability-contract.schema.json','evidence-record.schema.json']:
    try: json.loads((ROOT/'schemas'/schema).read_text())
    except Exception as e: errors.append(f'{schema} invalid: {e}')
if errors:
    print('FAIL')
    for e in errors: print('-',e)
    sys.exit(1)
print('PASS SuperMesh-X package validation')
