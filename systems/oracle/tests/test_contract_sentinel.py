import sys
from pathlib import Path
from oracle.contract_sentinel import contract_fingerprint
BASE=Path(__file__).resolve().parents[2]
for p in [BASE/'ARGUS-MICROSTRUCTURE-OS_HANDOFF'/'argus-microstructure-os'/'src',BASE/'ATHENA-SUPERVISORY-FABRIC_HANDOFF'/'athena-supervisory-fabric'/'src',BASE/'ICARUS-AION-MARKET-MEMORY-v0.1'/'icarus-aion']:
    sys.path.insert(0,str(p))

def test_contract_fingerprint_is_stable():
    from aion.contracts import Observation,SourceSpec
    from athena.contracts import ResearchRequest,Provenance
    from argus.contracts import MicrostructureFeature
    m={'AION.Observation':Observation,'AION.SourceSpec':SourceSpec,'ATHENA.ResearchRequest':ResearchRequest,'ATHENA.Provenance':Provenance,'ARGUS.MicrostructureFeature':MicrostructureFeature}
    a=contract_fingerprint(m); b=contract_fingerprint(m)
    assert a==b and len(a)==64
