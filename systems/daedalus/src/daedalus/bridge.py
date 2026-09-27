from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from collections import Counter


SCHEMA_VERSION = "icarus-candidate-v1"
NEXUS_HANDOFF_SCHEMA = "nexus.daedalus-validation-handoff.v1"

KNOWN_NEXUS_ROUTES = frozenset({
    "BLOCKING_DEPENDENCY",
    "DAEDALUS_DEVELOPMENT_ONLY",
    "BLOCKED_PENDING_CALENDAR_SESSION_SEMANTICS",
    "BLOCKED_PENDING_REPRESENTATION_IDENTITY",
    "RESOLVED_RECURRING_SESSION_CLOSURE",
    "RESOLVED_REPRESENTATION_COPY_LINEAGE",
    "SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC",
})


@dataclass(frozen=True)
class NexusDevelopmentTask:
    candidate_id: str
    family: str
    priority: str
    score: float
    scope: tuple[str, ...]
    source_evidence: tuple[dict[str, Any], ...]
    clean_confirmation_rule: dict[str, Any] | None
    allow_protected_holdout: bool = False
    confirmatory_evidence_required: bool = True
    production_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scope"] = list(self.scope)
        d["source_evidence"] = list(self.source_evidence)
        return d


def export_candidate(path: Path, candidate: dict[str, Any]) -> Path:
    """Export a read-only research candidate manifest. This function never writes into Icarus itself."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA_VERSION,
        "status": "RESEARCH_CANDIDATE_ONLY",
        "production_authorized": False,
        "candidate": candidate,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def _require_false(payload: dict[str, Any], key: str, *, where: str) -> None:
    if payload.get(key) is not False:
        raise ValueError(f"{where}.{key} must be explicitly false")


def load_nexus_validation_handoff(path: Path) -> dict[str, Any]:
    """Load a NEXUS handoff only if its holdout/production firewall is intact.

    NEXUS currently performs candidate discovery over the complete accessible source
    history. DAEDALUS must therefore treat those same rows as development evidence only;
    carving a protected tail *after* the NEXUS scan would not restore independence.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("NEXUS handoff root must be an object")
    if payload.get("schema") != NEXUS_HANDOFF_SCHEMA:
        raise ValueError(f"unsupported NEXUS handoff schema: {payload.get('schema')!r}")
    _require_false(payload, "production_authorized", where="handoff")
    _require_false(payload, "protected_holdout_spent", where="handoff")

    policy = payload.get("discovery_evidence_policy")
    if not isinstance(policy, dict):
        raise ValueError("NEXUS handoff is missing discovery_evidence_policy")
    if policy.get("full_accessible_history_scanned_before_candidate_selection") is not True:
        raise ValueError("NEXUS handoff must explicitly disclose full-history candidate discovery")
    if policy.get("current_history_selection_contaminated") is not True:
        raise ValueError("NEXUS handoff must mark current history as selection-contaminated")
    if policy.get("pristine_protected_holdout_available_inside_same_scanned_files") is not False:
        raise ValueError("NEXUS handoff may not claim a pristine holdout inside already-scanned source files")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("NEXUS handoff candidates must be a list")
    observed_routes: Counter[str] = Counter()
    for i, row in enumerate(candidates):
        if not isinstance(row, dict):
            raise ValueError(f"handoff.candidates[{i}] must be an object")
        _require_false(row, "production_authorized", where=f"handoff.candidates[{i}]")
        route = row.get("route")
        if not isinstance(route, dict):
            raise ValueError(f"handoff.candidates[{i}].route must be an object")
        if route.get("protected_holdout_eligible_on_current_history") is not False:
            raise ValueError(f"handoff.candidates[{i}] illegally marks current history as protected-holdout eligible")
        if route.get("confirmatory_validation_allowed_on_current_history") is not False:
            raise ValueError(f"handoff.candidates[{i}] illegally allows confirmatory validation on discovery history")
        route_name = str(route.get("route") or "")
        if route_name not in KNOWN_NEXUS_ROUTES:
            raise ValueError(f"handoff.candidates[{i}] uses unknown route: {route_name!r}")
        observed_routes[route_name] += 1

        if route_name == "SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC":
            if route.get("data_loss_asserted") is not False:
                raise ValueError(f"handoff.candidates[{i}] may not convert an open-session diagnostic into a data-loss assertion")
        if route_name == "RESOLVED_RECURRING_SESSION_CLOSURE":
            if route.get("data_loss_asserted") is not False:
                raise ValueError(f"handoff.candidates[{i}] may not label recurring-session closure as data loss")
        if route_name == "RESOLVED_REPRESENTATION_COPY_LINEAGE":
            if route.get("fusion_as_independent_views_allowed") is not False:
                raise ValueError(f"handoff.candidates[{i}] copy lineage may not be fused as independent views")

        if route_name == "DAEDALUS_DEVELOPMENT_ONLY":
            if route.get("confirmatory_requires_new_evidence") is not True:
                raise ValueError(f"handoff.candidates[{i}] must require unseen evidence for confirmation")
            rule = row.get("clean_confirmation_rule")
            if not isinstance(rule, dict):
                raise ValueError(f"handoff.candidates[{i}] is missing clean_confirmation_rule")
            if rule.get("current_source_history_is_pristine") is not False:
                raise ValueError(f"handoff.candidates[{i}] clean rule may not relabel scanned history as pristine")
            if rule.get("rule") != "UNSEEN_EVIDENCE_ONLY":
                raise ValueError(f"handoff.candidates[{i}] uses unsupported clean confirmation rule")

    declared_routes = payload.get("route_counts")
    if not isinstance(declared_routes, dict):
        raise ValueError("NEXUS handoff route_counts must be an object")
    normalized_declared = {str(k): int(v) for k, v in declared_routes.items()}
    if normalized_declared != dict(sorted(observed_routes.items())):
        raise ValueError("NEXUS handoff route_counts do not match candidate-row routes")
    return payload


def nexus_development_tasks(path: Path) -> tuple[NexusDevelopmentTask, ...]:
    """Return development-only tasks from a validated NEXUS handoff.

    This does not spend a DAEDALUS protected holdout and does not call `research_file`
    with holdout permission. It is a routing/import contract only.
    """
    payload = load_nexus_validation_handoff(path)
    tasks: list[NexusDevelopmentTask] = []
    for row in payload["candidates"]:
        route = row["route"]
        if route.get("route") != "DAEDALUS_DEVELOPMENT_ONLY":
            continue
        candidate = row.get("candidate")
        if not isinstance(candidate, dict):
            raise ValueError("DAEDALUS development handoff row is missing candidate payload")
        tasks.append(NexusDevelopmentTask(
            candidate_id=str(candidate.get("candidate_id") or ""),
            family=str(candidate.get("family") or ""),
            priority=str(candidate.get("priority") or ""),
            score=float(candidate.get("score") or 0.0),
            scope=tuple(str(x) for x in candidate.get("scope", [])),
            source_evidence=tuple(dict(x) for x in row.get("source_evidence", []) if isinstance(x, dict)),
            clean_confirmation_rule=dict(row["clean_confirmation_rule"]) if isinstance(row.get("clean_confirmation_rule"), dict) else None,
            allow_protected_holdout=False,
            confirmatory_evidence_required=True,
            production_authorized=False,
        ))
    return tuple(tasks)


def summarize_nexus_handoff(path: Path) -> dict[str, Any]:
    payload = load_nexus_validation_handoff(path)
    tasks = nexus_development_tasks(path)
    route_counts = dict(payload.get("route_counts", {}))
    return {
        "schema": payload["schema"],
        "source_iteration": payload.get("source_iteration"),
        "corpus_manifest_hash": payload.get("corpus_manifest_hash"),
        "candidate_count": len(payload.get("candidates", [])),
        "route_counts": route_counts,
        "development_task_count": len(tasks),
        "blocking_dependency_count": int(route_counts.get("BLOCKING_DEPENDENCY", 0)),
        "blocked_session_semantics_count": int(route_counts.get("BLOCKED_PENDING_CALENDAR_SESSION_SEMANTICS", 0)),
        "blocked_representation_identity_count": int(route_counts.get("BLOCKED_PENDING_REPRESENTATION_IDENTITY", 0)),
        "resolved_session_closure_count": int(route_counts.get("RESOLVED_RECURRING_SESSION_CLOSURE", 0)),
        "resolved_representation_copy_lineage_count": int(route_counts.get("RESOLVED_REPRESENTATION_COPY_LINEAGE", 0)),
        "open_session_diagnostic_count": int(route_counts.get("SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC", 0)),
        "protected_holdout_eligible_task_count": sum(bool(t.allow_protected_holdout) for t in tasks),
        "protected_holdout_spent": False,
        "production_authorized": False,
    }
