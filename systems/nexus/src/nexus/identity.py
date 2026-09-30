from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json
from pathlib import Path

@dataclass(frozen=True)
class InstrumentSpec:
    instrument_id:str
    canonical_symbol:str
    asset_class:str
    venue:str|None=None
    contract_kind:str="spot"  # spot|future|continuous_future|equity|index|synthetic|other
    aliases:tuple[str,...]=()
    execution_role:str="context"  # context|execution_candidate|non_executable
    underlying:str|None=None
    metadata:tuple[tuple[str,str],...]=()

    def __post_init__(self) -> None:
        for name,value in (
            ("instrument_id",self.instrument_id),
            ("canonical_symbol",self.canonical_symbol),
            ("asset_class",self.asset_class),
        ):
            if not isinstance(value,str) or not value.strip() or value != value.strip():
                raise ValueError(f"{name} must be a non-empty trimmed string")
        if self.contract_kind not in {
            "spot","future","continuous_future","equity","index","synthetic","other"
        }:
            raise ValueError("unsupported contract_kind")
        if self.execution_role not in {"context","execution_candidate","non_executable"}:
            raise ValueError("unsupported execution_role")
        aliases=[str(x).strip().upper() for x in self.aliases]
        if any(not x for x in aliases) or len(set(aliases)) != len(aliases):
            raise ValueError("instrument aliases must be non-empty and unique")
        keys=[str(k) for k,_ in self.metadata]
        if any(not k.strip() for k in keys) or len(set(keys)) != len(keys):
            raise ValueError("instrument metadata keys must be non-empty and unique")

    @property
    def spec_hash(self)->str:
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

class InstrumentRegistry:
    """Immutable version-by-identity registry; alias resolution never rewrites raw stream identity."""
    def __init__(self): self._specs={}; self._aliases={}
    def register(self,spec:InstrumentSpec)->str:
        if not spec.instrument_id or not spec.canonical_symbol:
            raise ValueError("instrument_id and canonical_symbol are required")
        if spec.instrument_id in self._specs and self._specs[spec.instrument_id].spec_hash!=spec.spec_hash:
            raise ValueError(f"immutable instrument conflict: {spec.instrument_id}")
        aliases=tuple((alias,alias.strip().upper()) for alias in (spec.canonical_symbol,*spec.aliases))
        for alias,k in aliases:
            owner=self._aliases.get(k)
            if owner is not None and owner!=spec.instrument_id:
                raise ValueError(f"ambiguous alias {alias}: {owner} vs {spec.instrument_id}")
        # Mutate only after every conflict check passes.
        self._specs[spec.instrument_id]=spec
        for _,k in aliases:
            self._aliases[k]=spec.instrument_id
        return spec.spec_hash
    def resolve(self,alias:str)->InstrumentSpec:
        if not isinstance(alias,str) or not alias.strip():
            raise KeyError(alias)
        return self._specs[self._aliases[alias.strip().upper()]]
    def get(self,instrument_id:str)->InstrumentSpec: return self._specs[instrument_id]
    def all(self): return tuple(self._specs[k] for k in sorted(self._specs))
    def dump(self,path:str|Path):
        payload={"instruments":[asdict(x) for x in self.all()]}
        Path(path).write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
