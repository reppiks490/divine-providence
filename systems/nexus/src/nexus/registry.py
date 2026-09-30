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

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.version.strip() or not self.method.strip():
            raise ValueError("factor name, version and method are required")
        if not self.components or any(not str(x).strip() for x in self.components):
            raise ValueError("factor components must be non-empty")
        if len(set(self.components)) != len(self.components):
            raise ValueError("factor components must be unique")
        pnames=[str(k) for k,_ in self.parameters]
        if any(not k.strip() for k in pnames) or len(set(pnames)) != len(pnames):
            raise ValueError("factor parameter names must be non-empty and unique")
        if any(
            not isinstance(dep,tuple) or len(dep)!=2
            or not str(dep[0]).strip() or not str(dep[1]).strip()
            for dep in self.dependencies
        ):
            raise ValueError("factor dependencies must be non-empty (name, version) pairs")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("factor dependencies must be unique")
        try:
            json.dumps(asdict(self),sort_keys=True,separators=(",",":"),default=str,allow_nan=False)
        except (TypeError,ValueError) as exc:
            raise ValueError("factor specification must be finite canonical JSON data") from exc

    @property
    def spec_hash(self) -> str:
        raw=json.dumps(asdict(self),sort_keys=True,separators=(",",":"),default=str,allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

class FactorRegistry:
    def __init__(self): self._specs={}
    def register(self,spec:FactorSpec):
        key=(spec.name,spec.version)
        old=self._specs.get(key)
        if old is not None and old.spec_hash != spec.spec_hash:
            raise ValueError(f"immutable factor version conflict: {key}")
        self._specs[key]=spec
        try:
            self.validate_dag()
        except Exception:
            if old is None:
                self._specs.pop(key,None)
            else:
                self._specs[key]=old
            raise
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
    def missing_dependencies(self):
        return tuple(sorted({
            dep
            for spec in self._specs.values()
            for dep in spec.dependencies
            if dep not in self._specs
        }))
    def validate_complete(self):
        missing=self.missing_dependencies()
        if missing:
            raise ValueError(f"missing factor dependencies: {missing}")
        return self.validate_dag()
    def dependency_order(self):
        self.validate_complete(); out=[]; seen=set()
        def visit(n):
            if n in seen:return
            for d in self._specs[n].dependencies:
                if d in self._specs: visit(d)
            seen.add(n); out.append(n)
        for n in sorted(self._specs): visit(n)
        return tuple(out)
