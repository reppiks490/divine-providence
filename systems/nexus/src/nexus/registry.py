from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib, json

@dataclass(frozen=True)
class FactorSpec:
    name: str
    version: str
    components: tuple[str,...]
    method: str
    parameters: tuple[tuple[str,object], ...]=()
    description: str=""
    dependencies: tuple[tuple[str,str], ...]=()

    @property
    def spec_hash(self) -> str:
        raw=json.dumps(asdict(self),sort_keys=True,separators=(",",":"),default=str).encode()
        return hashlib.sha256(raw).hexdigest()

class FactorRegistry:
    def __init__(self): self._specs={}
    def register(self,spec:FactorSpec):
        key=(spec.name,spec.version)
        if key in self._specs and self._specs[key].spec_hash != spec.spec_hash:
            raise ValueError(f"immutable factor version conflict: {key}")
        self._specs[key]=spec
        self.validate_dag()
        return spec.spec_hash
    def get(self,name:str,version:str): return self._specs[(name,version)]
    def all(self): return tuple(self._specs[k] for k in sorted(self._specs))
    def validate_dag(self):
        graph={k:tuple(dep for dep in s.dependencies if dep in self._specs) for k,s in self._specs.items()}
        visiting=set(); done=set()
        def visit(n):
            if n in visiting: raise ValueError(f"factor dependency cycle at {n}")
            if n in done: return
            visiting.add(n)
            for d in graph.get(n,()): visit(d)
            visiting.remove(n); done.add(n)
        for n in graph: visit(n)
        return True
    def dependency_order(self):
        self.validate_dag(); out=[]; seen=set()
        def visit(n):
            if n in seen:return
            for d in self._specs[n].dependencies:
                if d in self._specs: visit(d)
            seen.add(n); out.append(n)
        for n in sorted(self._specs): visit(n)
        return tuple(out)
