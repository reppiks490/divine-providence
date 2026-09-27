from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
required=[
 'SKILL.md','manifest.yaml','README.md','CHATGPT.md','CODEX.md','CLAUDE.md',
 'references/architecture.md','references/provider-registry.md','references/research-mesh.md',
 'references/finance-quant.md','references/crypto-onchain.md','references/coding-orchestration.md',
 'references/learning-media.md','references/nvidia-compute.md','references/verification-governance.md',
 'schemas/capability-contract.schema.json','schemas/evidence-record.schema.json',
 'config/providers.example.yaml','scripts/validate_package.py','scripts/capability_router.py'
]
missing=[p for p in required if not (ROOT/p).exists()]
if missing:
    print('FAIL missing:', ', '.join(missing))
    sys.exit(1)
print('PASS package structure')
