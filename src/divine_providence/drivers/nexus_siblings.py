"""NEXUS -> AION / ARGUS / ATHENA / DAEDALUS exact sibling-contract validation.

Runs NEXUS's own ``validate_sibling_contracts`` against the monorepo sibling
trees: AION EventStore append/as-of/hash-chain, ARGUS CANDLE_PROXY firewall,
ATHENA advisory-only provenance, DAEDALUS research-candidate bridge.
"""
from nexus.sibling_validation import validate_sibling_contracts

from ._common import emit, sibling_roots

r = sibling_roots()
res = validate_sibling_contracts(aion_root=r["aion"], argus_root=r["argus"], athena_root=r["athena"], daedalus_root=r["daedalus"])
emit({"connection": "nexus->siblings", "ok": res.passed, "result": res.to_dict()})
