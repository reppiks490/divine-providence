"""Data contracts shared by collection, memory and trusted publication."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sys

REPOSITORY = "reppiks490/divine-providence"
BRANCH = "research-history"
MAX_JSON = 5_000_000
MAX_EXPERIMENTS = 4096
MAX_EVENTS = 250
AUTHORITY = {"execution_authorized": False, "production_authorized": False,
             "protected_holdout_touched": False}
PROTOCOL = {
    "version": "icarus.institution.development.v2",
    "stage": "historical_development_paper_proxy",
    "source_rows": [1200, 60000], "whole_files_only": True,
    "model_families": ["logistic", "random_forest", "extra_trees", "hist_gradient_boosting"],
    "validation": "five spread purged development folds; rolling training capped at 2000; protected tail reserved",
    "fold_placement": "spread", "max_train_size": 2000,
    "agenda": "ORACLE marginal provenance diversity with explicit metadata cost priors",
    "agenda_information_priors": {"five_estimated_folds": 1.0, "two_to_four": .75, "insufficient": .05},
    "agenda_fold_estimation": "rows minus conservative 55-row warmup; default DAEDALUS split geometry; advisory only",
    "target_horizon_bars": 5, "feature_lag_bars": 1,
    "permutation_iterations": 199, "bootstrap_iterations": 199,
    "cost_multipliers": [1, 2, 5], "temporal_segments": 3,
    "ablation": "remove return/momentum family from logistic; fixed before results",
    "cross_market": "exact shared unique timestamps; past-only lags 0..3; development prefixes only",
    "budget_per_run": 2, "timeout_seconds_per_source": 360,
    "max_interrupted_attempts": 3,
    "interpretation": "Exploratory development evidence; no confirmed edge or execution fills",
}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def seal(value):
    value = {k: v for k, v in value.items() if k != "content_hash"}
    return {**value, "content_hash": digest(value)}


def read_json(raw):
    if len(raw) > MAX_JSON:
        raise ValueError("JSON exceeds bounded data contract")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("Non-finite JSON")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def validate(value, schema):
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise ValueError("Invalid institution schema")
    if value.get("content_hash") != digest({k: v for k, v in value.items() if k != "content_hash"}):
        raise ValueError("Institution content hash mismatch")
    if any(value.get(k) is not v for k, v in AUTHORITY.items()):
        raise ValueError("Institution authority mismatch")
    # Authority cannot be elevated inside a nested experiment or hypothesis.
    def visit(item):
        if isinstance(item, dict):
            for k, v in item.items():
                if k in AUTHORITY and v is not False:
                    raise ValueError("Nested authority escalation")
                visit(v)
        elif isinstance(item, list):
            for v in item:
                visit(v)
    visit(value)
    if schema == "icarus.institution.memory.v1":
        if set(value) != {"schema", "experiments", "events", "connections", "updated_at", "last_run", "content_hash", *AUTHORITY}:
            raise ValueError("Unexpected memory fields")
        if not isinstance(value["experiments"], dict) or len(value["experiments"]) > MAX_EXPERIMENTS:
            raise ValueError("Invalid memory experiment inventory")
        if not isinstance(value["events"], dict) or len(value["events"]) > MAX_EVENTS:
            raise ValueError("Invalid event memory")
        if not isinstance(value["connections"], dict) or len(value["connections"]) > 2048:
            raise ValueError("Invalid cross-market memory")
        for key, record in value["experiments"].items():
            if not re.fullmatch(r"[0-9a-f]{64}", key) or record.get("id") != key:
                raise ValueError("Invalid experiment context identity")
            if record.get("outcome") not in {"rejected", "watch", "interrupted", "source_rejected"}:
                raise ValueError("Invalid remembered outcome")
            if type(record.get("attempts")) is not int or not 1 <= record["attempts"] <= 3:
                raise ValueError("Invalid remembered attempt count")
    return value


def empty_memory():
    return seal({"schema": "icarus.institution.memory.v1", **AUTHORITY,
                 "experiments": {}, "events": {}, "connections": {}, "updated_at": now(), "last_run": None})


def context(root: Path):
    files = sorted((root / "systems/daedalus/src/daedalus").glob("*.py"))
    files += sorted((root / "systems/oracle/src/oracle").glob("*.py"))
    # Presentation/publication edits must not restart scientific experiments.
    files += [root / "scripts/institution" / name for name in ("common.py", "driver.py", "sources.py", "agenda.py")]
    source = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    versions = {name: importlib.metadata.version(name) for name in
                ("numpy", "pandas", "scipy", "scikit-learn", "joblib")}
    value = {"protocol": PROTOCOL, "code": source, "dependencies": versions,
             "python": f"{sys.version_info.major}.{sys.version_info.minor}"}
    return {**value, "context_hash": digest(value)}


def experiment_id(source_hash, context_hash):
    return digest({"source_hash": source_hash, "context_hash": context_hash})


def write_json(path, value):
    raw = canonical(value)
    if len(raw) > MAX_JSON:
        raise ValueError("Output exceeds bounded data contract")
    Path(path).write_bytes(raw + b"\n")
