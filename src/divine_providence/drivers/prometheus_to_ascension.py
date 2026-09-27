"""PROMETHEUS attestation contract <-> ASCENSION Sibling Manifest Conformance Kit.

Read-only cross-check that every field ASCENSION's declared PROMETHEUS v0.5
profile requires exists on PROMETHEUS's runtime attestation/receipt types, and
that the mandatory receipt checks agree. It does not sign, verify cryptography
or open the Transfer gate: ``authenticated`` stays false by design.
"""
import dataclasses
import importlib

import sibling_manifest_conformance_v0_1 as kit

from ._common import emit

profile = kit.prometheus_v0_5_declared_profile()
out = {"connection": "prometheus->ascension", "profile_id": profile["profile_id"], "authenticated": False,
       "transfer": "BLOCKED: needs sibling-signed runtime export + Adapter v0.4 trust policy (see systems/ascension/PROMETHEUS_v0.5_GAP_MAP.md)"}
try:
    att = importlib.import_module("prometheus_loop.attestation")
except ModuleNotFoundError:
    emit({**out, "ok": False, "error": "prometheus_loop.attestation missing (attestation-lineage branch not integrated)"})
    raise SystemExit(0)


def field_names(cls_name: str) -> set[str]:
    return {f.name for f in dataclasses.fields(getattr(att, cls_name))}


required = (profile["external_attestation_required_fields"], profile["verification_receipt_required_fields"],
            profile["mandatory_receipt_checks"])
missing_att = sorted(set(required[0]) - field_names("ExternalExecutionAttestation"))
missing_rec = sorted(set(required[1]) - field_names("AttestationVerificationReceipt"))
# PROMETHEUS's own mandatory receipt checks (the set its receipts are validated against).
prom_checks = getattr(att, "_REQUIRED_CHECKS", None)
checks_ok = prom_checks is not None and set(prom_checks) == set(required[2])
emit({**out, "ok": all(required) and not missing_att and not missing_rec and checks_ok,
      "missing_attestation_fields": missing_att, "missing_receipt_fields": missing_rec,
      "ascension_mandatory_receipt_checks": profile["mandatory_receipt_checks"],
      "prometheus_required_checks": sorted(prom_checks) if prom_checks is not None else None,
      "handoff_required_layers": kit.build_handoff_checklist("PROMETHEUS")["required_layers"]})
