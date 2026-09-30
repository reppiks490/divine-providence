from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from typing import Mapping


def _is_sha256(value: str) -> bool:
    if not isinstance(value,str) or len(value)!=64:
        return False
    try:
        int(value,16)
    except ValueError:
        return False
    return True


def _canonical_json(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        allow_nan=False,
    ).encode()


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
        if not isinstance(product_id,str) or not product_id.strip():
            raise ValueError("product_id is required")
        if not isinstance(product_version,str) or not product_version.strip():
            raise ValueError("product_version is required")
        if type(decision_ns) is not int or decision_ns < 0:
            raise ValueError("decision_ns must be a non-negative integer")
        if not _is_sha256(spec_hash):
            raise ValueError("spec_hash must be a SHA-256 hex digest")
        if not isinstance(code_version,str) or not code_version.strip():
            raise ValueError("code_version is required")
        if not isinstance(input_hashes,Mapping):
            raise TypeError("input_hashes must be a mapping")

        normalized=[]
        for key,value in input_hashes.items():
            key=str(key).strip()
            value=str(value)
            if not key:
                raise ValueError("input hash names must be non-empty")
            if not _is_sha256(value):
                raise ValueError(f"input hash for {key!r} must be a SHA-256 hex digest")
            normalized.append((key,value))
        inputs=tuple(sorted(normalized))
        if len({k for k,_ in inputs}) != len(inputs):
            raise ValueError("input hash names must be unique")

        try:
            params=_canonical_json(parameters or {})
        except (TypeError,ValueError) as exc:
            raise ValueError("parameters must be finite canonical JSON data") from exc
        ph=hashlib.sha256(params).hexdigest()
        payload=cls._payload(
            product_id=product_id.strip(),
            product_version=product_version.strip(),
            decision_ns=decision_ns,
            spec_hash=spec_hash,
            input_hashes=inputs,
            code_version=code_version.strip(),
            parameters_hash=ph,
        )
        dh=hashlib.sha256(_canonical_json(payload)).hexdigest()
        return cls(
            product_id.strip(),product_version.strip(),decision_ns,spec_hash,
            inputs,code_version.strip(),ph,dh
        )

    def verify(self) -> bool:
        if (
            not self.product_id
            or not self.product_version
            or type(self.decision_ns) is not int
            or self.decision_ns < 0
            or not _is_sha256(self.spec_hash)
            or not self.code_version
            or not _is_sha256(self.parameters_hash)
            or not _is_sha256(self.derivation_hash)
            or tuple(sorted(self.input_hashes)) != self.input_hashes
            or len({k for k,_ in self.input_hashes}) != len(self.input_hashes)
            or any(not k or not _is_sha256(v) for k,v in self.input_hashes)
        ):
            return False
        payload=self._payload(
            product_id=self.product_id,
            product_version=self.product_version,
            decision_ns=self.decision_ns,
            spec_hash=self.spec_hash,
            input_hashes=self.input_hashes,
            code_version=self.code_version,
            parameters_hash=self.parameters_hash,
        )
        return hashlib.sha256(_canonical_json(payload)).hexdigest()==self.derivation_hash

    def to_dict(self)->dict:
        d=asdict(self)
        d["input_hashes"]=[list(x) for x in self.input_hashes]
        return d
