from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from .lineage import DerivationRecord
from .registry import FactorRegistry


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value,str) or len(value)!=64:
        return False
    try:
        int(value,16)
    except ValueError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class FactorGenealogyNode:
    name: str
    version: str
    components: tuple[str, ...]
    method: str
    dependencies: tuple[tuple[str, str], ...]
    spec_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "components": list(self.components),
            "method": self.method,
            "dependencies": [list(x) for x in self.dependencies],
            "spec_hash": self.spec_hash,
        }


@dataclass(frozen=True, slots=True)
class FactorGenealogySnapshot:
    schema: str
    factors: tuple[FactorGenealogyNode, ...]
    dependency_edges: tuple[tuple[str, str, str, str], ...]
    derivation_hashes: tuple[str, ...]
    genealogy_hash: str

    @staticmethod
    def _payload(schema: str, factors: tuple[FactorGenealogyNode, ...], dependency_edges: tuple[tuple[str,str,str,str],...], derivation_hashes: tuple[str,...]) -> dict[str, Any]:
        return {
            "schema": schema,
            "factors": [x.to_dict() for x in factors],
            "dependency_edges": [list(x) for x in dependency_edges],
            "derivation_hashes": list(derivation_hashes),
        }

    @classmethod
    def create(cls, registry: FactorRegistry, derivations: Iterable[DerivationRecord] = ()) -> "FactorGenealogySnapshot":
        registry.validate_complete()
        derivations = tuple(derivations)
        if any(not d.verify() for d in derivations):
            raise ValueError("invalid derivation record in genealogy")
        factors = tuple(sorted((
            FactorGenealogyNode(s.name, s.version, tuple(s.components), s.method, tuple(s.dependencies), s.spec_hash)
            for s in registry.all()
        ), key=lambda x: (x.name, x.version)))
        edges = tuple(sorted(
            (dep_name, dep_version, s.name, s.version)
            for s in registry.all()
            for dep_name, dep_version in s.dependencies
        ))
        dh = tuple(sorted(d.derivation_hash for d in derivations))
        if len(set(dh)) != len(dh):
            raise ValueError("duplicate derivation record in genealogy")
        schema = "nexus.factor-genealogy.v1"
        return cls(schema, factors, edges, dh, _digest(cls._payload(schema, factors, edges, dh)))

    def verify(self) -> bool:
        if self.schema != "nexus.factor-genealogy.v1" or not _is_sha256(self.genealogy_hash):
            return False
        if tuple(sorted(self.derivation_hashes)) != self.derivation_hashes:
            return False
        if len(set(self.derivation_hashes)) != len(self.derivation_hashes):
            return False
        if any(not _is_sha256(x) for x in self.derivation_hashes):
            return False
        keys={(x.name,x.version) for x in self.factors}
        if len(keys)!=len(self.factors):
            return False
        if any(not _is_sha256(x.spec_hash) for x in self.factors):
            return False
        expected_edges={
            (dn,dv,node.name,node.version)
            for node in self.factors
            for dn,dv in node.dependencies
        }
        if tuple(sorted(expected_edges)) != self.dependency_edges:
            return False
        if any((a,b) not in keys or (c,d) not in keys for a,b,c,d in self.dependency_edges):
            return False
        return self.genealogy_hash == _digest(
            self._payload(self.schema,self.factors,self.dependency_edges,self.derivation_hashes)
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(self.schema, self.factors, self.dependency_edges, self.derivation_hashes), "genealogy_hash": self.genealogy_hash}


@dataclass(frozen=True, slots=True)
class ResearchRunManifest:
    schema: str
    run_id: str
    decision_start_ns: int
    decision_end_ns: int
    corpus_manifest_hash: str
    reviewed_registry_hash: str
    genealogy_hash: str
    code_version: str
    input_artifacts: tuple[tuple[str, str], ...]
    output_artifacts: tuple[tuple[str, str], ...]
    parameters_hash: str
    derivation_hashes: tuple[str, ...]
    production_authorized: bool
    manifest_hash: str

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        decision_start_ns: int,
        decision_end_ns: int,
        corpus_manifest_hash: str,
        reviewed_registry_hash: str,
        genealogy: FactorGenealogySnapshot,
        code_version: str,
        input_artifacts: Mapping[str, str],
        output_artifacts: Mapping[str, str],
        parameters: Mapping[str, Any] | None = None,
        derivations: Iterable[DerivationRecord] = (),
    ) -> "ResearchRunManifest":
        if not isinstance(run_id,str) or not run_id.strip():
            raise ValueError("run_id is required")
        if type(decision_start_ns) is not int or type(decision_end_ns) is not int:
            raise TypeError("decision interval must use integer nanoseconds")
        if decision_start_ns < 0 or decision_end_ns < decision_start_ns:
            raise ValueError("invalid decision interval")
        if not isinstance(code_version,str) or not code_version.strip():
            raise ValueError("code_version is required")
        for name,value in (
            ("corpus_manifest_hash",corpus_manifest_hash),
            ("reviewed_registry_hash",reviewed_registry_hash),
        ):
            if not _is_sha256(value):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
        if not genealogy.verify():
            raise ValueError("genealogy hash verification failed")
        derivations = tuple(derivations)
        if any(not d.verify() for d in derivations):
            raise ValueError("invalid derivation record in research run")
        def artifacts(value:Mapping[str,str],label:str)->tuple[tuple[str,str],...]:
            rows=[]
            for key,digest in value.items():
                key=str(key).strip()
                if not key:
                    raise ValueError(f"{label} artifact names must be non-empty")
                if not _is_sha256(digest):
                    raise ValueError(f"{label} artifact {key!r} must have SHA-256 digest")
                rows.append((key,str(digest)))
            if len({k for k,_ in rows}) != len(rows):
                raise ValueError(f"{label} artifact names must be unique")
            return tuple(sorted(rows))
        inputs=artifacts(input_artifacts,"input")
        outputs=artifacts(output_artifacts,"output")
        try:
            params_hash = _digest(parameters or {})
        except (TypeError,ValueError) as exc:
            raise ValueError("parameters must be finite canonical JSON data") from exc
        derivation_hashes = tuple(sorted(d.derivation_hash for d in derivations))
        if len(set(derivation_hashes)) != len(derivation_hashes):
            raise ValueError("duplicate derivation record in research run")
        if derivation_hashes != genealogy.derivation_hashes:
            raise ValueError("research-run derivations must exactly match genealogy derivations")
        if any(not decision_start_ns <= d.decision_ns <= decision_end_ns for d in derivations):
            raise ValueError("derivation decision_ns lies outside research-run interval")
        payload = {
            "schema": "nexus.research-run.v1",
            "run_id": str(run_id),
            "decision_start_ns": int(decision_start_ns),
            "decision_end_ns": int(decision_end_ns),
            "corpus_manifest_hash": str(corpus_manifest_hash),
            "reviewed_registry_hash": str(reviewed_registry_hash),
            "genealogy_hash": genealogy.genealogy_hash,
            "code_version": str(code_version),
            "input_artifacts": inputs,
            "output_artifacts": outputs,
            "parameters_hash": params_hash,
            "derivation_hashes": derivation_hashes,
            "production_authorized": False,
        }
        return cls(**payload, manifest_hash=_digest(payload))

    def verify(self) -> bool:
        if (
            self.schema != "nexus.research-run.v1"
            or not self.run_id
            or type(self.decision_start_ns) is not int
            or type(self.decision_end_ns) is not int
            or self.decision_start_ns < 0
            or self.decision_end_ns < self.decision_start_ns
            or not self.code_version
            or self.production_authorized is not False
        ):
            return False
        for digest in (
            self.corpus_manifest_hash,self.reviewed_registry_hash,self.genealogy_hash,
            self.parameters_hash,self.manifest_hash,*self.derivation_hashes,
            *(v for _,v in self.input_artifacts),*(v for _,v in self.output_artifacts),
        ):
            if not _is_sha256(digest):
                return False
        if tuple(sorted(self.input_artifacts)) != self.input_artifacts:
            return False
        if tuple(sorted(self.output_artifacts)) != self.output_artifacts:
            return False
        if tuple(sorted(self.derivation_hashes)) != self.derivation_hashes:
            return False
        if len(set(self.derivation_hashes)) != len(self.derivation_hashes):
            return False
        payload = {
            "schema": self.schema,
            "run_id": self.run_id,
            "decision_start_ns": self.decision_start_ns,
            "decision_end_ns": self.decision_end_ns,
            "corpus_manifest_hash": self.corpus_manifest_hash,
            "reviewed_registry_hash": self.reviewed_registry_hash,
            "genealogy_hash": self.genealogy_hash,
            "code_version": self.code_version,
            "input_artifacts": self.input_artifacts,
            "output_artifacts": self.output_artifacts,
            "parameters_hash": self.parameters_hash,
            "derivation_hashes": self.derivation_hashes,
            "production_authorized": self.production_authorized,
        }
        return self.manifest_hash == _digest(payload)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["input_artifacts"] = [list(x) for x in self.input_artifacts]
        d["output_artifacts"] = [list(x) for x in self.output_artifacts]
        d["derivation_hashes"] = list(self.derivation_hashes)
        return d

    def aion_source_spec(self) -> dict[str, Any]:
        return {
            "source_id": f"NEXUS:RUN:{self.manifest_hash[:20]}",
            "representation_id": "nexus:research-run:v1",
            "symbol": "NEXUS",
            "capabilities": ["context"],
            "max_evidence_tier": 1,
            "source_sha256": self.manifest_hash,
            "sequence_policy": "monotone",
            "origin": "nexus_derived",
            "license_reference": "internal_derivation",
            "evidence_reference": f"run:{self.run_id}",
        }

    def aion_observation(self, *, ingested_ns: int | None = None, sequence: int = 0) -> dict[str, Any]:
        if ingested_ns is not None and (type(ingested_ns) is not int or ingested_ns < 0):
            raise ValueError("ingested_ns must be a non-negative integer or None")
        if type(sequence) is not int or sequence < 0:
            raise ValueError("sequence must be a non-negative integer")
        ingestion = max(self.decision_end_ns, ingested_ns if ingested_ns is not None else self.decision_end_ns)
        return {
            "source_id": f"NEXUS:RUN:{self.manifest_hash[:20]}",
            "source_event_id": f"run:{self.manifest_hash[:24]}",
            "revision": 1,
            "kind": "context",
            "event_ns": self.decision_end_ns,
            "available_ns": ingestion,
            "ingested_ns": ingestion,
            "evidence_tier": 1,
            "payload": self.to_dict(),
            "plane": "research",
            "published_ns": None,
            "sequence": sequence,
            "quality_flags": ["nexus_research_run"],
            "availability_basis": "observed_receipt",
        }
