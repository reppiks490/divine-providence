from __future__ import annotations

from typing import Mapping, Any

from ..contracts import AdversarialReport, ExperimentSpec


def run_adversarial(
    spec: ExperimentSpec,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> AdversarialReport:
    del baseline  # baseline is reserved for richer comparative checks in later versions.
    failed: list[str] = []
    details: list[tuple[str, str]] = []

    checks = set(spec.checks)
    if "leakage" in checks:
        ok = not bool(candidate.get("uses_future", False))
        details.append(("leakage", "pass" if ok else "candidate uses future information"))
        if not ok:
            failed.append("leakage")
    if "ablation" in checks:
        ok = bool(candidate.get("ablation_stable", False))
        details.append(("ablation", "pass" if ok else "candidate fails ablation stability"))
        if not ok:
            failed.append("ablation")
    if "perturbation" in checks:
        ok = bool(candidate.get("perturbation_stable", False))
        details.append(("perturbation", "pass" if ok else "candidate fails perturbation stability"))
        if not ok:
            failed.append("perturbation")
    if "missingness" in checks:
        ok = bool(candidate.get("missingness_safe", False))
        details.append(("missingness", "pass" if ok else "candidate fails missingness safety"))
        if not ok:
            failed.append("missingness")
    if "reproducibility" in checks:
        hashes = tuple(candidate.get("replay_hashes", ()))
        ok = len(hashes) >= 2 and len(set(hashes)) == 1
        details.append(("reproducibility", "pass" if ok else "replay hashes are not identical"))
        if not ok:
            failed.append("reproducibility")

    return AdversarialReport(
        experiment_id=spec.artifact_id,
        passed=not failed,
        failed_checks=tuple(failed),
        details=tuple(details),
    )
