from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .attestation import AttestationVerificationReceipt, ExternalExecutionAttestation, PluginAttestationPolicy
from .contracts import CandidateImprovement, LoopKind
from .fixtures import sample_candidate_profile, sample_observations, sample_plugins
from .ids import content_id
from .memory.store import ResearchMemory
from .orchestration.loop import HostPluginResult, PrometheusLoop, RunInput
from .plugins import PluginDecisionStatus, PluginExecutionEvidence


def _completed(plugin_id: str, token: str) -> HostPluginResult:
    return HostPluginResult(
        plugin_id=plugin_id,
        success=True,
        input_fingerprint=f"fixture-input:{plugin_id}",
        output_fingerprint=f"fixture-output:{token}",
    )


def _fixture_loop_id(policy: PluginAttestationPolicy) -> str:
    observations = sample_observations()
    inventory = sample_plugins()
    profile = sample_candidate_profile()
    return content_id(
        "loop",
        {
            "run_kind": LoopKind.FORGE.value,
            "objective": "research architecture validation with source-backed analysis",
            "observations": [item.artifact_id for item in observations],
            "plugins": [item.descriptor_id for item in inventory],
            "candidate_fingerprint": content_id("candidate-profile", profile),
            "source_contract_ids": (),
            "parent_manifest_ids": (),
            "plugin_attestation_policy": policy.value,
        },
    )


def _attested_completed(plugin_id: str, token: str, loop_run_id: str) -> HostPluginResult:
    inventory = sample_plugins()
    descriptor = next(item for item in inventory if item.plugin_id == plugin_id)
    base = _completed(plugin_id, token)
    evidence = PluginExecutionEvidence(
        loop_run_id=loop_run_id,
        plugin_id=plugin_id,
        plugin_descriptor_id=descriptor.descriptor_id,
        status=PluginDecisionStatus.COMPLETED,
        input_fingerprint=base.input_fingerprint,
        output_fingerprint=base.output_fingerprint,
    )
    attestation = ExternalExecutionAttestation(
        plugin_evidence_id=evidence.artifact_id,
        subject_sha256=evidence.artifact_id.split(":", 1)[1],
        predicate_type="https://example.invalid/plugin-execution/v1",
        envelope_ref=f"fixture://attestation/{plugin_id}",
        envelope_sha256=("a" if plugin_id == "deep-research" else "b") * 64,
        verification_material_sha256=("c" if plugin_id == "deep-research" else "d") * 64,
        signer_identity=f"fixture-host://{plugin_id}",
        attestation_format="application/vnd.in-toto+json",
    )
    receipt = AttestationVerificationReceipt(
        attestation_id=attestation.artifact_id,
        verifier_id="fixture-verifier://v1",
        trusted_root_id="fixture-root://v1",
        verification_policy_id="fixture-policy://v1",
        checks=(
            ("signature", True),
            ("subject_digest", True),
            ("signer_identity", True),
            ("trusted_root", True),
        ),
        external_verification_ref=f"fixture://verification/{plugin_id}",
    )
    return HostPluginResult(
        plugin_id=plugin_id,
        success=True,
        input_fingerprint=base.input_fingerprint,
        output_fingerprint=base.output_fingerprint,
        external_attestation=attestation,
        attestation_verification=receipt,
    )


def _demo(memory_path: Path, *, policy: PluginAttestationPolicy = PluginAttestationPolicy.OPTIONAL) -> dict:
    loop = PrometheusLoop(ResearchMemory(memory_path))
    loop_run_id = _fixture_loop_id(policy)
    if policy is PluginAttestationPolicy.REQUIRE_VERIFIED:
        plugin_results = (
            _attested_completed("deep-research", "deep-research-demo", loop_run_id),
            _attested_completed("exa", "exa-demo", loop_run_id),
        )
    else:
        plugin_results = (
            _completed("deep-research", "deep-research-demo"),
            _completed("exa", "exa-demo"),
        )
    result = loop.run(
        RunInput(
            run_kind=LoopKind.FORGE,
            objective="research architecture validation with source-backed analysis",
            observations=sample_observations(),
            plugin_inventory=sample_plugins(),
            plugin_results=plugin_results,
            candidate_profile=sample_candidate_profile(),
            baseline_metrics=(("score", 0.50), ("drawdown", 0.20)),
            candidate_metrics=(("score", 0.62), ("drawdown", 0.18)),
            plugin_attestation_policy=policy,
        )
    )
    plugin_status: dict[str, str] = {}
    uses = {use.plugin_id: use for use in result.plugin_audit.uses}
    for decision in result.plugin_audit.decisions:
        use = uses.get(decision.plugin_id)
        plugin_status[decision.plugin_id] = (use.status if use else decision.status).value

    result_status = result.result.status.value if isinstance(result.result, CandidateImprovement) else "REJECTED"
    return {
        "loop_run_id": result.loop_run_id,
        "status": result.status.value,
        "plugin_audit": plugin_status,
        "disagreement_ids": [case.artifact_id for case in result.disagreements],
        "route": {
            "artifact_id": result.route.artifact_id,
            "action": result.route.action.value,
            "priority_band": result.route.priority_band.value,
            "reason_code": result.route.reason_code,
        },
        "hypothesis_id": result.hypothesis.artifact_id if result.hypothesis is not None else None,
        "experiment_id": result.experiment.artifact_id if result.experiment is not None else None,
        "reused_negative": result.reused_negative,
        "plugin_attestation_policy": policy.value,
        "external_attestation_ids": list(result.external_attestation_ids),
        "attestation_verification_ids": list(result.attestation_verification_ids),
        "attestation_coverage_gaps": list(result.attestation_coverage_gaps),
        "provenance_manifest_id": result.provenance_manifest_id,
        "provenance_lineage_report_id": result.provenance_lineage_report_id,
        "promotion_packet_id": result.promotion_packet.artifact_id if result.promotion_packet else None,
        "cryptographic_verification_performed_by_prometheus": False,
        "production_authorized": bool(result.promotion_packet and result.promotion_packet.production_authorized),
        "result": {
            "artifact_id": result.result.artifact_id,
            "status": result_status,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prometheus-loop")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="run the deterministic local v0.5 OPTIONAL-attestation fixture")
    demo.add_argument("--memory", type=Path, required=True, help="path for append-only local research memory")
    strict = subparsers.add_parser("demo-strict-attested", help="run deterministic strict externally-attested fixture")
    strict.add_argument("--memory", type=Path, required=True, help="path for append-only local research memory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        print(json.dumps(_demo(args.memory), sort_keys=True))
        return 0
    if args.command == "demo-strict-attested":
        print(json.dumps(_demo(args.memory, policy=PluginAttestationPolicy.REQUIRE_VERIFIED), sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
