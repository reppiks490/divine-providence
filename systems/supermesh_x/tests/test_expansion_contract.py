from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
required=[
 'references/source-expansion.md','references/query-planner.md','references/evidence-fusion.md',
 'references/temporal-data.md','references/plugin-discovery.md','config/capability-map.json',
 'scripts/source_planner.py','workflows/omniscout.md','workflows/cross-provider-finance.md'
]
missing=[p for p in required if not (ROOT/p).exists()]
if missing:
    print('FAIL missing expansion:', ', '.join(missing))
    sys.exit(1)
print('PASS expansion structure')
