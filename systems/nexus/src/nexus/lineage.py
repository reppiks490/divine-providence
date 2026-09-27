from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Mapping


@dataclass(frozen=True, slots=True)
class DerivationRecord:
    product_id: str
    product_version: str
    decision_ns: int
    spec_hash: str
    input_hashes: tuple[tuple[str, str], ...]
    code_version: str
    parameters_hash: str
    derivation_hash: str

    @staticmethod
    def _payload(
        *, product_id: str, product_version: str, decision_ns: int, spec_hash: str,
        input_hashes: tuple[tuple[str, str], ...], code_version: str,
        parameters_hash: str,
    ) -> dict:
        return {
            "product_id":product_id,
            "product_version":product_version,
            "decision_ns":int(decision_ns),
            "spec_hash":spec_hash,
            "input_hashes":[list(x) for x in input_hashes],
            "code_version":code_version,
            "parameters_hash":parameters_hash,
        }

    @classmethod
    def create(
        cls,
        *,
        product_id: str,
        product_version: str,
        decision_ns: int,
        spec_hash: str,
        input_hashes: Mapping[str, str],
        code_version: str,
        parameters: Mapping | None = None,
    ) -> "DerivationRecord":
        inputs=tuple(sorted((str(k),str(v)) for k,v in input_hashes.items()))
        params=json.dumps(parameters or {},sort_keys=True,separators=(",",":"),default=str).encode()
        ph=hashlib.sha256(params).hexdigest()
        payload=cls._payload(product_id=product_id,product_version=product_version,decision_ns=decision_ns,
            spec_hash=spec_hash,input_hashes=inputs,code_version=code_version,parameters_hash=ph)
        dh=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return cls(product_id,product_version,int(decision_ns),spec_hash,inputs,code_version,ph,dh)

    def verify(self) -> bool:
        payload=self._payload(product_id=self.product_id,product_version=self.product_version,
            decision_ns=self.decision_ns,spec_hash=self.spec_hash,input_hashes=self.input_hashes,
            code_version=self.code_version,parameters_hash=self.parameters_hash)
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()==self.derivation_hash

    def to_dict(self)->dict:
        d=asdict(self);d["input_hashes"]=[list(x) for x in self.input_hashes];return d
