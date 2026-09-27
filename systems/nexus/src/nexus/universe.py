from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import StreamManifest
from .integrity import IntegrityPolicy, assess_manifest
from .quality import quality_score


@dataclass(frozen=True, slots=True)
class UniverseDecision:
    stream_id: str
    symbol: str
    selected: bool
    reason: str
    score: float


def build_factor_universe(
    manifests: Iterable[StreamManifest],
    *,
    policy: IntegrityPolicy | None = None,
    max_streams_per_symbol: int | None = None,
) -> tuple[tuple[str, ...], tuple[UniverseDecision, ...]]:
    """Select a lineage-safe factor universe without duplicate/copy inflation."""
    policy=policy or IntegrityPolicy(); decisions=[]; candidates=[]; seen_raw=set();seen_logical=set()
    for m in manifests:
        a=assess_manifest(m,policy);sid=m.identity.stream_id;sym=m.identity.symbol;q=quality_score(m)
        if not a.admitted:
            decisions.append(UniverseDecision(sid,sym,False,"integrity_gate",q));continue
        rh=m.identity.raw_sha256;lh=m.metadata.get("logical_sha256")
        if rh in seen_raw:
            decisions.append(UniverseDecision(sid,sym,False,"exact_byte_duplicate",q));continue
        if lh and lh in seen_logical:
            decisions.append(UniverseDecision(sid,sym,False,"logical_duplicate",q));continue
        seen_raw.add(rh)
        if lh:seen_logical.add(lh)
        candidates.append(m)
    by_symbol={}
    for m in candidates:by_symbol.setdefault(m.identity.symbol,[]).append(m)
    selected=[]
    for sym,group in sorted(by_symbol.items()):
        group=sorted(group,key=lambda m:(-quality_score(m),m.identity.stream_id))
        keep=len(group) if max_streams_per_symbol is None else max(0,int(max_streams_per_symbol))
        for i,m in enumerate(group):
            ok=i<keep;reason="selected" if ok else "symbol_representation_cap"
            decisions.append(UniverseDecision(m.identity.stream_id,sym,ok,reason,quality_score(m)))
            if ok:selected.append(m.identity.stream_id)
    return tuple(sorted(selected)),tuple(sorted(decisions,key=lambda d:d.stream_id))
