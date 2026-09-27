from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..attestation import PluginAttestationPolicy
from ..contracts import RejectedHypothesis, ResearchProvenanceManifest
from ..ids import canonical_json, content_id


class ResearchMemory:
    """Append-only local research memory for PROMETHEUS artifacts."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._by_id: dict[str, dict[str, Any]] = {}
        self._negative_by_experiment: dict[str, RejectedHypothesis] = {}
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        for line_number, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            record = json.loads(raw)
            payload_json = canonical_json(record["payload"])
            expected = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
            if record.get("content_sha256") != expected:
                raise ValueError(f"research memory hash mismatch at line {line_number}")
            artifact_id = record["artifact_id"]
            previous = self._by_id.get(artifact_id)
            if previous is not None and previous != record:
                raise ValueError(f"conflicting duplicate artifact id {artifact_id}")
            self._index_record(record)

    def _index_record(self, record: dict[str, Any]) -> None:
        self._by_id[record["artifact_id"]] = record
        if record["artifact_type"] == "RejectedHypothesis":
            payload = record["payload"]
            artifact = RejectedHypothesis(
                experiment_id=payload["experiment_id"],
                reason=payload["reason"],
                evidence_ids=tuple(payload["evidence_ids"]),
            )
            self._negative_by_experiment[artifact.experiment_id] = artifact

    def append(self, artifact: Any) -> bool:
        artifact_id = getattr(artifact, "artifact_id", None)
        if not artifact_id:
            raise TypeError("artifact must expose artifact_id")
        if artifact_id in self._by_id:
            return False
        payload = json.loads(canonical_json(artifact))
        payload_json = canonical_json(payload)
        record = {
            "artifact_id": artifact_id,
            "artifact_type": type(artifact).__name__,
            "payload": payload,
            "content_sha256": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(record) + "\n")
        self._index_record(record)
        return True

    def find_by_id(self, artifact_id: str) -> dict[str, Any]:
        return self._by_id[artifact_id]


    def reconstruct_provenance_manifest(self, artifact_id: str) -> ResearchProvenanceManifest:
        record = self.find_by_id(artifact_id)
        if record["artifact_type"] != "ResearchProvenanceManifest":
            raise ValueError(f"wrong artifact type for provenance manifest {artifact_id}")
        payload = record["payload"]
        if content_id("research-provenance", payload) != artifact_id:
            raise ValueError(f"provenance manifest content id mismatch for {artifact_id}")
        return ResearchProvenanceManifest(
            loop_run_id=payload["loop_run_id"],
            experiment_id=payload["experiment_id"],
            candidate_id=payload["candidate_id"],
            selected_plugin_descriptor_ids=tuple(payload["selected_plugin_descriptor_ids"]),
            plugin_evidence_ids=tuple(payload["plugin_evidence_ids"]),
            plugin_contribution_ids=tuple(payload["plugin_contribution_ids"]),
            observation_ids=tuple(payload["observation_ids"]),
            source_contract_ids=tuple(payload.get("source_contract_ids", ())),
            parent_manifest_ids=tuple(payload.get("parent_manifest_ids", ())),
            external_attestation_ids=tuple(payload.get("external_attestation_ids", ())),
            attestation_verification_ids=tuple(payload.get("attestation_verification_ids", ())),
            plugin_attestation_policy=PluginAttestationPolicy(payload.get("plugin_attestation_policy", "OPTIONAL")),
        )

    def has_negative(self, experiment_id: str) -> bool:
        return experiment_id in self._negative_by_experiment

    def negative_for(self, experiment_id: str) -> RejectedHypothesis:
        return self._negative_by_experiment[experiment_id]
