from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from .lineage import DerivationRecord
from .registry import FactorRegistry


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str).encode()).hexdigest()


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
        schema = "nexus.factor-genealogy.v1"
        return cls(schema, factors, edges, dh, _digest(cls._payload(schema, factors, edges, dh)))

    def verify(self) -> bool:
        return self.genealogy_hash == _digest(self._payload(self.schema, self.factors, self.dependency_edges, self.derivation_hashes))

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
        if decision_start_ns < 0 or decision_end_ns < decision_start_ns:
            raise ValueError("invalid decision interval")
        if not genealogy.verify():
            raise ValueError("genealogy hash verification failed")
        derivations = tuple(derivations)
        if any(not d.verify() for d in derivations):
            raise ValueError("invalid derivation record in research run")
        inputs = tuple(sorted((str(k), str(v)) for k, v in input_artifacts.items()))
        outputs = tuple(sorted((str(k), str(v)) for k, v in output_artifacts.items()))
        params_hash = _digest(parameters or {})
        derivation_hashes = tuple(sorted(d.derivation_hash for d in derivations))
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
        return self.production_authorized is False and self.manifest_hash == _digest(payload)

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
        ingestion = max(self.decision_end_ns, int(ingested_ns if ingested_ns is not None else self.decision_end_ns))
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
            "sequence": int(sequence),
            "quality_flags": ["nexus_research_run"],
            "availability_basis": "observed_receipt",
        }
