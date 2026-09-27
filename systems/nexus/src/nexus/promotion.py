from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Callable

import pandas as pd

from .causality import CausalityAudit, audit_prefix_invariance


@dataclass(frozen=True, slots=True)
class TransformSpec:
    name: str
    version: str
    category: str
    code_hash: str
    description: str = ""

    @property
    def spec_hash(self) -> str:
        raw=json.dumps(asdict(self),sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CausalityCertificate:
    transform_name: str
    transform_version: str
    spec_hash: str
    sample_hash: str
    comparisons: int
    checked_cutpoints: tuple[int, ...]
    certificate_hash: str

    def verify(self) -> bool:
        payload={
            "transform_name":self.transform_name,
            "transform_version":self.transform_version,
            "spec_hash":self.spec_hash,
            "sample_hash":self.sample_hash,
            "comparisons":self.comparisons,
            "checked_cutpoints":list(self.checked_cutpoints),
        }
        expected=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return expected==self.certificate_hash


class CausalTransformRegistry:
    """Immutable transform registry with mandatory prefix-invariance certificates.

    A transform can exist in the registry without being certified, but `promotable`
    remains false until the exact registered version passes a causality audit. This is
    a research/engineering gate only; it does not authorize production execution.
    """

    def __init__(self) -> None:
        self._specs: dict[tuple[str,str], TransformSpec] = {}
        self._certs: dict[tuple[str,str], CausalityCertificate] = {}

    def register(self, spec: TransformSpec) -> str:
        key=(spec.name,spec.version)
        old=self._specs.get(key)
        if old is not None and old.spec_hash != spec.spec_hash:
            raise ValueError(f"immutable transform version conflict: {key}")
        self._specs[key]=spec
        return spec.spec_hash

    @staticmethod
    def _sample_hash(data: pd.DataFrame) -> str:
        # pandas' stable row hashing includes index and exact column order; hash that
        # byte stream plus dtypes/column names so the certificate binds to the sample.
        row_hash=pd.util.hash_pandas_object(data,index=True).to_numpy(dtype="uint64",copy=False).tobytes()
        meta=json.dumps({"columns":[str(c) for c in data.columns],"dtypes":[str(x) for x in data.dtypes]},sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(meta+b"|"+row_hash).hexdigest()

    def certify(
        self,
        name: str,
        version: str,
        build: Callable[[pd.DataFrame], pd.DataFrame],
        sample: pd.DataFrame,
        *,
        cutpoints=None,
        atol: float = 1e-10,
        rtol: float = 1e-8,
    ) -> tuple[CausalityCertificate, CausalityAudit]:
        key=(name,version)
        if key not in self._specs:
            raise KeyError(key)
        audit=audit_prefix_invariance(build,sample,cutpoints=cutpoints,atol=atol,rtol=rtol)
        if not audit.passed:
            raise ValueError(f"causality certification failed with {len(audit.violations)} violation(s)")
        spec=self._specs[key];sample_hash=self._sample_hash(sample)
        payload={
            "transform_name":name,
            "transform_version":version,
            "spec_hash":spec.spec_hash,
            "sample_hash":sample_hash,
            "comparisons":audit.comparisons,
            "checked_cutpoints":list(audit.checked_cutpoints),
        }
        ch=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        cert=CausalityCertificate(name,version,spec.spec_hash,sample_hash,audit.comparisons,audit.checked_cutpoints,ch)
        self._certs[key]=cert
        return cert,audit

    def certificate(self,name:str,version:str)->CausalityCertificate|None:
        return self._certs.get((name,version))

    def promotable(self,name:str,version:str)->bool:
        c=self._certs.get((name,version));return bool(c and c.verify())

    def manifest(self)->dict:
        rows=[]
        for key in sorted(self._specs):
            spec=self._specs[key];cert=self._certs.get(key)
            rows.append({"spec":asdict(spec),"spec_hash":spec.spec_hash,"causality_certificate":asdict(cert) if cert else None,"promotable":bool(cert and cert.verify()),"production_authorized":False})
        return {"schema":"nexus.causal-transform-registry.v1","transforms":rows,"production_authorized":False}
