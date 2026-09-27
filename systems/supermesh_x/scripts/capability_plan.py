#!/usr/bin/env python3
"""Compile adaptive provider selections into auditable execution contracts."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy


PRIVATE_CLASSES = {"user_authorized_private"}
DERIVED_PRIVATE_CLASS = "derived_private_feature"


def _score(candidate):
    for key in ("adaptive_score", "combined_score", "state_score", "score"):
        if key in candidate:
            try:
                return float(candidate[key])
            except (TypeError, ValueError):
                pass
    return 0.0


def _authority_for(capability):
    cap = str(capability)
    if cap == "broker.orders" or cap.startswith("broker.order"):
        return {
            "mode": "transactional_write",
            "requires_explicit_authorization": True,
        }
    if cap.startswith(("communications.email.send", "communications.email.forward", "code.deploy", "repo.write")):
        return {
            "mode": "external_write",
            "requires_explicit_authorization": True,
        }
    return {
        "mode": "read",
        "requires_explicit_authorization": False,
    }


def validate_step(step):
    """Validate one planned provider hop against privacy constraints."""
    row = dict(step or {})
    visibility = row.get("provider_visibility", "public")
    input_class = row.get("input_class", "public_web")
    fields = set(row.get("input_fields") or [])
    allowed_derived = set(row.get("allowed_derived_fields") or [])

    if visibility == "public" and input_class in PRIVATE_CLASSES:
        return {"allowed": False, "reason": "private_to_public_blocked"}

    if visibility == "public" and input_class == DERIVED_PRIVATE_CLASS:
        if not fields.issubset(allowed_derived):
            return {"allowed": False, "reason": "derived_private_field_not_allowlisted"}

    return {"allowed": True, "reason": "allowed"}


def compile_plan(
    request_id,
    capability,
    candidates,
    source_class="public_web",
    observed_schema_fingerprints=None,
    allowed_derived_fields=None,
    input_fields=None,
    runtime_secrets=None,
):
    """Compile ranked candidates into a deterministic, permission-aware plan.

    Runtime secrets are intentionally accepted but never persisted in the plan.
    """
    del runtime_secrets
    ordered = sorted((deepcopy(x) for x in (candidates or [])), key=_score, reverse=True)
    authority = _authority_for(capability)
    observed = observed_schema_fingerprints or {}
    allowlist = list(allowed_derived_fields or [])
    in_fields = list(input_fields or [])

    steps = []
    if ordered:
        primary = ordered[0]
        provider = primary.get("provider") or primary.get("name")
        expected_fp = primary.get("schema_fingerprint")
        current_fp = observed.get(provider, expected_fp)
        schema_ok = expected_fp is None or current_fp == expected_fp
        step = {
            "index": 0,
            "capability": str(capability),
            "provider": provider,
            "fallbacks": [
                x.get("provider") or x.get("name")
                for x in ordered[1:]
                if (x.get("provider") or x.get("name"))
            ],
            "provider_visibility": primary.get("provider_visibility", "public"),
            "input_class": source_class,
            "input_fields": in_fields,
            "allowed_derived_fields": allowlist,
            "schema_fingerprint": expected_fp,
            "observed_schema_fingerprint": current_fp,
            "preflight": "ready" if schema_ok else "rediscover",
            "executable": bool(schema_ok),
        }
        privacy = validate_step(step)
        if not privacy["allowed"]:
            step["executable"] = False
            step["preflight"] = "privacy_block"
        step["privacy"] = privacy
        steps.append(step)

    auto_execute = bool(steps) and all(step["executable"] for step in steps) and not authority["requires_explicit_authorization"]
    plan = {
        "request_id": str(request_id),
        "capability": str(capability),
        "authority": authority,
        "source_class": source_class,
        "auto_execute": auto_execute,
        "steps": steps,
        "status": "ready" if auto_execute else ("authorization_required" if authority["requires_explicit_authorization"] and steps else "preflight_required"),
    }
    return plan


def plan_digest(plan):
    """Return a stable SHA-256 digest for the persisted plan contract."""
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
