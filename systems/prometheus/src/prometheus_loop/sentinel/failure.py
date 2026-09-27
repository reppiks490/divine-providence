from __future__ import annotations

from ..contracts import FailureCase


def contract_drift_failure(
    *,
    expected_hash: str,
    observed_hash: str,
    decision_instant: str,
) -> FailureCase:
    return FailureCase(
        failure_type="CONTRACT_DRIFT",
        source_system="NEXUS",
        expected_contract_hash=expected_hash,
        observed_contract_hash=observed_hash,
        decision_instant=decision_instant,
        details="Observed NEXUS sibling contract snapshot does not match the pinned release identity; input quarantined.",
    )


def causal_instant_failure(
    *,
    contract_hash: str,
    decision_instant: str,
    details: str,
) -> FailureCase:
    return FailureCase(
        failure_type="CAUSAL_INSTANT_MISMATCH",
        source_system="NEXUS",
        expected_contract_hash=contract_hash,
        observed_contract_hash=contract_hash,
        decision_instant=decision_instant,
        details=details,
    )


def bundle_validation_failure(
    *,
    expected_hash: str,
    observed_hash: str,
    decision_instant: str,
    details: str,
) -> FailureCase:
    return FailureCase(
        failure_type="BUNDLE_VALIDATION_FAILURE",
        source_system="NEXUS",
        expected_contract_hash=expected_hash,
        observed_contract_hash=observed_hash,
        decision_instant=decision_instant,
        details=details,
    )
