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

    @property
    def spec_hash(self)->str:
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

class InstrumentRegistry:
    """Immutable version-by-identity registry; alias resolution never rewrites raw stream identity."""
    def __init__(self): self._specs={}; self._aliases={}
    def register(self,spec:InstrumentSpec)->str:
        if spec.instrument_id in self._specs and self._specs[spec.instrument_id].spec_hash!=spec.spec_hash:
            raise ValueError(f"immutable instrument conflict: {spec.instrument_id}")
        for alias in (spec.canonical_symbol,*spec.aliases):
            k=alias.upper()
            owner=self._aliases.get(k)
            if owner is not None and owner!=spec.instrument_id:
                raise ValueError(f"ambiguous alias {alias}: {owner} vs {spec.instrument_id}")
            self._aliases[k]=spec.instrument_id
        self._specs[spec.instrument_id]=spec; return spec.spec_hash
    def resolve(self,alias:str)->InstrumentSpec:
        return self._specs[self._aliases[alias.upper()]]
    def get(self,instrument_id:str)->InstrumentSpec: return self._specs[instrument_id]
    def all(self): return tuple(self._specs[k] for k in sorted(self._specs))
    def dump(self,path:str|Path):
        payload={"instruments":[asdict(x) for x in self.all()]}
        Path(path).write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")
