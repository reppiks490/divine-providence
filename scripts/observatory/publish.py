"""Publish Observatory data without executing or checking out history content.

Only the CLI reads GITHUB_TOKEN. The collector and reporter need no write token.
The injectable transport has signature ``(method, path, body) -> (status, data)``.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import report


BRANCH = "observatory-history"
MARKER = "<!-- icarus-observatory:incident:v1 -->"
ISSUE_TITLE = "ICARUS Observatory: current incident"
RUN_SCHEMA = "icarus.observatory.run.v1"
HISTORY_SCHEMA = "icarus.observatory.history.v1"
MAX_BLOB_BYTES = 2_000_000
MAX_HISTORY_BYTES = 32 * 1024 * 1024
MAX_API_BYTES = 8 * 1024 * 1024
RETENTION = 90
EVIDENCE_FILES = frozenset({"collection.json", "hub.json", "validation_report.json",
                          "hub.stdout.log", "hub.stderr.log", "validation.stdout.log",
                          "validation.stderr.log"})
DATA_FILES = frozenset({"index.json", "latest.json", "last_complete.json", "index.html", "summary.md"})
HASH = re.compile(r"[0-9a-f]{64}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")
RUN_PATH = re.compile(r"runs/([1-9][0-9]*)-([1-9][0-9]*)\.json\Z")
FINDING_ID = re.compile(r"(?:hub/tests|(?:suite|compile|adversarial|connection)/[A-Za-z0-9_.-]{1,128})\Z")
RECEIPT_KEYS = frozenset({"schema", "run_id", "run_attempt", "event", "repository", "ref", "commit", "run_url",
    "started_at", "finished_at", "python", "platform", "validator_exit_code", "hub_exit_code", "inventory",
    "dependencies", "environment_hash", "state", "reasons", "findings", "evidence_hashes",
    "previous_receipt_hash", "execution_authorized", "production_authorized", "live_engine", "receipt_hash"})
FINDING_KEYS = frozenset({"id", "state", "counts", "seconds", "diagnostic", "systems", "run_id", "commit", "finding_hash"})
ENTRY_KEYS = frozenset({"path", "run_id", "run_attempt", "state", "commit", "receipt_hash", "previous_receipt_hash"})


class PublishError(RuntimeError):
    """Invalid publication data or an unsuccessful GitHub API operation."""


def _reject(message):
    raise PublishError(message)


def _positive(value):
    return type(value) is int and value > 0


def _hash(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def _hash_object(value, field):
    unhashed = {key: item for key, item in value.items() if key != field}
    return hashlib.sha256(report.canonical_bytes(unhashed)).hexdigest()


def _json(data, label):
    if len(data) > MAX_BLOB_BYTES:
        _reject(f"{label} exceeds data size limit")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _reject(f"{label} contains duplicate JSON keys")
            result[key] = value
        return result
    try:
        value = json.loads(data, object_pairs_hook=pairs,
                           parse_constant=lambda _: _reject(f"{label} contains non-finite JSON"))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PublishError(f"Invalid JSON in {label}") from exc
    return value


def _strings(value, label, maximum=512):
    if not isinstance(value, list) or len(value) > maximum or any(not isinstance(item, str) or len(item) > 8192 for item in value):
        _reject(f"Invalid {label}")


def _date(value):
    if not isinstance(value, str) or len(value) > 64:
        _reject("Invalid receipt timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PublishError("Invalid receipt timestamp") from exc
    if result.utcoffset() is None or result.utcoffset().total_seconds() != 0:
        _reject("Receipt timestamps must be UTC")
    return result


def validate_receipt(value):
    """Validate the versioned data envelope and its self-contained content hashes."""
    if not isinstance(value, dict) or set(value) != RECEIPT_KEYS or value.get("schema") != RUN_SCHEMA:
        _reject("Invalid receipt schema or fields")
    if not _positive(value["run_id"]) or not _positive(value["run_attempt"]):
        _reject("Invalid receipt run identity")
    if value["event"] not in {"schedule", "push", "workflow_dispatch"} or value["ref"] != "refs/heads/main":
        _reject("Receipt is not an allowlisted main run")
    if not isinstance(value["repository"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value["repository"]):
        _reject("Invalid receipt repository")
    if not isinstance(value["commit"], str) or SHA.fullmatch(value["commit"]) is None:
        _reject("Invalid receipt commit identity")
    if value["run_url"] != f"https://github.com/{value['repository']}/actions/runs/{value['run_id']}":
        _reject("Invalid canonical Actions identity URL")
    if value["execution_authorized"] is not False or value["production_authorized"] is not False or value["live_engine"] != "not_observed":
        _reject("Invalid receipt authority")
    if _date(value["finished_at"]) < _date(value["started_at"]):
        _reject("Receipt finish precedes its start")
    for key in ("python", "platform"):
        if not isinstance(value[key], str) or not value[key] or len(value[key]) > 512:
            _reject(f"Invalid receipt {key}")
    for key in ("validator_exit_code", "hub_exit_code"):
        if value[key] is not None and type(value[key]) is not int:
            _reject(f"Invalid receipt {key}")
    if value["state"] not in {"healthy", "unhealthy", "incomplete"}:
        _reject("Invalid receipt state")
    _strings(value["reasons"], "receipt reasons")
    inventory = value["inventory"]
    if not isinstance(inventory, dict) or set(inventory) != {"systems", "connections", "adversarial", "coverage"}:
        _reject("Invalid receipt inventory")
    for key in ("systems", "adversarial"):
        _strings(inventory[key], f"inventory {key}")
        if len(set(inventory[key])) != len(inventory[key]) or any(NAME.fullmatch(item) is None for item in inventory[key]):
            _reject("Invalid inventory labels")
    if not isinstance(inventory["connections"], dict) or len(inventory["connections"]) > 512 or not isinstance(inventory["coverage"], dict):
        _reject("Invalid connection inventory")
    for system, coverage in inventory["coverage"].items():
        if system not in inventory["systems"] or not isinstance(coverage, dict) or not {"status"}.issubset(coverage) or set(coverage) - {"status", "connections", "reason"}:
            _reject("Invalid system coverage declaration")
        if coverage["status"] not in {"connected", "standalone", "not_observed"} or (coverage["status"] == "not_observed" and value["state"] != "incomplete"):
            _reject("Invalid system coverage status")
        if "connections" in coverage:
            _strings(coverage["connections"], "coverage connections")
            if any(name not in inventory["connections"] for name in coverage["connections"]):
                _reject("Invalid system coverage connection identity")
        if "reason" in coverage and (not isinstance(coverage["reason"], str) or len(coverage["reason"]) > 8192):
            _reject("Invalid system coverage reason")
        if coverage["status"] == "standalone" and not coverage.get("reason"):
            _reject("Standalone system coverage requires an explanation")
    for name, connection in inventory["connections"].items():
        if NAME.fullmatch(name) is None or not isinstance(connection, dict) or set(connection) != {"systems", "contract"}:
            _reject("Invalid connection inventory")
        _strings(connection["systems"], "connection systems")
        if any(item not in inventory["systems"] for item in connection["systems"]) or not isinstance(connection["contract"], str) or len(connection["contract"]) > 8192:
            _reject("Invalid connection inventory members")
    if not isinstance(value["dependencies"], list) or len(value["dependencies"]) > 4096:
        _reject("Invalid dependency metadata")
    for dependency in value["dependencies"]:
        if not isinstance(dependency, dict) or set(dependency) != {"name", "version"} or any(not isinstance(dependency[key], str) or len(dependency[key]) > 512 for key in dependency):
            _reject("Invalid dependency metadata")
    environment_content = {key: value[key] for key in ("python", "platform", "dependencies")}
    if not _hash(value["environment_hash"]) or value["environment_hash"] != hashlib.sha256(report.canonical_bytes(environment_content)).hexdigest():
        _reject("Invalid environment content hash")
    hashes = value["evidence_hashes"]
    if not isinstance(hashes, dict) or any(name not in EVIDENCE_FILES or not _hash(digest) for name, digest in hashes.items()):
        _reject("Invalid evidence content hashes")
    if value["previous_receipt_hash"] is not None and not _hash(value["previous_receipt_hash"]):
        _reject("Invalid prior receipt hash")
    findings = value["findings"]
    if not isinstance(findings, dict) or len(findings) > 2048 or "hub/tests" not in findings:
        _reject("Invalid receipt findings")
    for finding_id, finding in findings.items():
        if FINDING_ID.fullmatch(finding_id) is None or not isinstance(finding, dict) or set(finding) != FINDING_KEYS:
            _reject("Invalid finding schema")
        if finding["id"] != finding_id or type(finding["run_id"]) is not int or finding["run_id"] != value["run_id"] or finding["commit"] != value["commit"]:
            _reject("Invalid finding run identity")
        if finding["state"] not in {"pass", "fail", "not_observed"}:
            _reject("Invalid finding state")
        if not isinstance(finding["diagnostic"], str) or len(finding["diagnostic"]) > 8192:
            _reject("Invalid finding diagnostic")
        _strings(finding["systems"], "finding systems")
        if any(system not in inventory["systems"] for system in finding["systems"]):
            _reject("Invalid finding systems")
        counts = finding["counts"]
        if counts is not None and (not isinstance(counts, dict) or len(counts) > 64 or any(not isinstance(key, str) or not re.fullmatch(r"[a-z_]{1,64}", key) or type(count) is not int or count < 0 for key, count in counts.items())):
            _reject("Invalid finding counts")
        seconds = finding["seconds"]
        if seconds is not None and (type(seconds) not in {int, float} or not math.isfinite(seconds) or seconds < 0):
            _reject("Invalid finding duration")
        if finding["state"] != "not_observed" and finding_id.startswith(("suite/", "hub/")):
            if counts is None or seconds is None:
                _reject("Observed test findings require counts and duration")
        if not _hash(finding["finding_hash"]) or finding["finding_hash"] != _hash_object(finding, "finding_hash"):
            _reject("Finding content hash mismatch")
        if finding["state"] == "pass" and finding_id.startswith(("suite/", "hub/")):
            if counts is None or counts.get("passed", 0) < 1 or any(counts.get(key, 0) for key in ("failed", "errors", "deselected")):
                _reject("Invalid passing test finding")
    expected = {"hub/tests"} | {f"{prefix}/{name}" for prefix in ("suite", "compile") for name in inventory["systems"]}
    expected |= {f"adversarial/{name}" for name in inventory["adversarial"]} | {f"connection/{name}" for name in inventory["connections"]}
    if set(findings) != expected:
        _reject("Receipt findings differ from expected inventory")
    if value["state"] == "healthy" and (value["validator_exit_code"] != 0 or value["hub_exit_code"] != 0 or value["reasons"] or any(finding["state"] != "pass" for finding in findings.values())):
        _reject("Healthy receipt has failing or incomplete evidence")
    if value["state"] == "unhealthy" and not any(finding["state"] == "fail" for finding in findings.values()):
        _reject("Unhealthy receipt has no failing finding")
    if value["state"] != "incomplete":
        if not inventory["systems"] or not inventory["connections"] or not inventory["adversarial"] or set(inventory["coverage"]) != set(inventory["systems"]) or any(finding["state"] == "not_observed" for finding in findings.values()):
            _reject("Complete receipt has incomplete inventory or findings")
        native_failed = any(key != "hub/tests" and finding["state"] == "fail" for key, finding in findings.items())
        if type(value["validator_exit_code"]) is not int or (value["validator_exit_code"] == 0) == native_failed or type(value["hub_exit_code"]) is not int or (value["hub_exit_code"] == 0) != (findings["hub/tests"]["state"] == "pass"):
            _reject("Complete receipt exit codes contradict findings")
    if not _hash(value["receipt_hash"]) or value["receipt_hash"] != _hash_object(value, "receipt_hash"):
        _reject("Receipt content hash mismatch")
    return value


class GitHubClient:
    """Bounded stdlib REST client; no token is retained in artifacts or diagnostics."""

    def __init__(self, token, repository, transport=None):
        if not isinstance(token, str) or not token:
            _reject("GITHUB_TOKEN is required for publication")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository or ""):
            _reject("Invalid GitHub repository")
        self.repository = repository
        self._token = token
        self._transport = transport or self._request

    def _request(self, method, path, body):
        request = Request("https://api.github.com" + path, method=method,
                          data=report.canonical_bytes(body) if body is not None else None,
                          headers={"Authorization": "Bearer " + self._token,
                                   "Accept": "application/vnd.github+json",
                                   "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json",
                                   "User-Agent": "icarus-observatory"})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read(MAX_API_BYTES + 1)
                if len(raw) > MAX_API_BYTES:
                    _reject("GitHub API response exceeds size limit")
                return response.status, json.loads(raw) if raw else None
        except HTTPError as exc:
            # Neither request headers nor untrusted response bodies enter diagnostics.
            return exc.code, None
        except (URLError, TimeoutError, ValueError, UnicodeError, OSError) as exc:
            raise PublishError("GitHub API request failed") from exc

    def call(self, method, path, body=None, allow_missing=False):
        if not path.startswith("/") or ".." in path:
            _reject("Invalid GitHub API path")
        status, data = self._transport(method, f"/repos/{self.repository}" + path, body)
        if allow_missing and status == 404:
            return None
        if status not in {200, 201, 204}:
            _reject(f"GitHub API {method} {path} returned HTTP {status}")
        return data


def _identity(environment):
    required = ("GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_EVENT_NAME")
    if any(not environment.get(key) for key in required):
        _reject("Missing trusted Actions identity metadata")
    if environment["GITHUB_REF"] != "refs/heads/main" or environment["GITHUB_EVENT_NAME"] not in {"schedule", "push", "workflow_dispatch"}:
        _reject("Publication requires an allowlisted main event")
    if environment.get("GITHUB_SERVER_URL", "https://github.com") != "https://github.com":
        _reject("Unsupported Actions server identity")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", environment["GITHUB_REPOSITORY"]) or SHA.fullmatch(environment["GITHUB_SHA"]) is None:
        _reject("Invalid trusted Actions identity")
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        if not re.fullmatch(r"[1-9][0-9]*", environment[key]):
            _reject("Invalid trusted Actions run identity")
    return {"repository": environment["GITHUB_REPOSITORY"], "ref": environment["GITHUB_REF"],
            "commit": environment["GITHUB_SHA"], "event": environment["GITHUB_EVENT_NAME"],
            "run_id": int(environment["GITHUB_RUN_ID"]), "run_attempt": int(environment["GITHUB_RUN_ATTEMPT"]),
            "run_url": f"https://github.com/{environment['GITHUB_REPOSITORY']}/actions/runs/{environment['GITHUB_RUN_ID']}"}


def _verify_api_identity(client, identity):
    run = client.call("GET", f"/actions/runs/{identity['run_id']}")
    if not isinstance(run, dict):
        _reject("Invalid GitHub Actions metadata identity")
    expected = {"id": identity["run_id"], "run_attempt": identity["run_attempt"], "head_sha": identity["commit"],
                "head_branch": "main", "event": identity["event"], "html_url": identity["run_url"]}
    if any(type(run.get(key)) is not type(value) or run.get(key) != value for key, value in expected.items()) or not isinstance(run.get("repository"), dict) or run["repository"].get("full_name") != identity["repository"]:
        _reject("GitHub Actions metadata identity does not match trusted run")


def _load_current(input_dir, identity):
    receipt_path = input_dir / "run.json"
    if receipt_path.is_symlink():
        _reject("Receipt input may not be a symbolic link")
    if receipt_path.exists():
        if not receipt_path.is_file() or receipt_path.stat().st_size > MAX_BLOB_BYTES:
            _reject("Invalid receipt input size")
        current = validate_receipt(_json(receipt_path.read_bytes(), "run.json"))
    else:
        # This path represents a lost/failed collection job, never a stale result.
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        collection = {"schema": "icarus.observatory.collection.v1", **identity,
                      "started_at": now, "finished_at": now, "python": "not_observed", "platform": "not_observed",
                      "validator_exit_code": None, "hub_exit_code": None, "validator_timed_out": False,
                      "hub_timed_out": False, "collection_errors": ["Collection artifact or normalized receipt is missing"],
                      "dependencies": [], "inventory": {"systems": [], "connections": {}, "adversarial": [], "coverage": {}}}
        current = validate_receipt(report.normalize(collection, None, None))
        if current["state"] != "incomplete":
            _reject("Missing collection must produce incomplete evidence")
        # Partial uploads may preserve useful logs while losing their final
        # normalized receipt. Hash those bounded files as unobserved evidence;
        # they never determine state or replace trusted identity metadata.
        for name in EVIDENCE_FILES:
            path = input_dir / name
            if path.exists() or path.is_symlink():
                if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BLOB_BYTES:
                    _reject(f"Invalid partial evidence file {name}")
                current["evidence_hashes"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
        current = report.seal_receipt(current)
    if any(current.get(key) != value or type(current.get(key)) is not type(value) for key, value in identity.items()):
        _reject("Receipt identity does not match trusted Actions metadata")
    return current


def _entry(receipt):
    return {"path": f"runs/{receipt['run_id']}-{receipt['run_attempt']}.json",
            **{key: receipt[key] for key in ENTRY_KEYS if key != "path"}}


def _order(receipt):
    return receipt["run_id"], receipt["run_attempt"]


def _read_history(client):
    reference = client.call("GET", f"/git/ref/heads/{BRANCH}", allow_missing=True)
    if reference is None:
        return None, [], None, None
    if not isinstance(reference, dict) or not isinstance(reference.get("object"), dict) or SHA.fullmatch(reference["object"].get("sha", "")) is None:
        _reject("Invalid history reference")
    head = reference["object"]["sha"]
    commit = client.call("GET", f"/git/commits/{head}")
    if not isinstance(commit, dict) or not isinstance(commit.get("tree"), dict) or SHA.fullmatch(commit["tree"].get("sha", "")) is None:
        _reject("Invalid history commit")
    tree = client.call("GET", f"/git/trees/{commit['tree']['sha']}?recursive=1")
    if not isinstance(tree, dict) or tree.get("truncated") is not False or not isinstance(tree.get("tree"), list) or len(tree["tree"]) > RETENTION + len(DATA_FILES) + 1:
        _reject("Invalid or truncated history tree")
    entries = {}
    total = 0
    for item in tree["tree"]:
        if not isinstance(item, dict):
            _reject("Invalid history tree entry")
        path = item.get("path")
        if path == "runs" and item.get("type") == "tree" and item.get("mode") == "040000":
            continue
        if not isinstance(path, str) or (path not in DATA_FILES and RUN_PATH.fullmatch(path) is None) or path in entries:
            _reject("History tree contains an unapproved data path")
        if item.get("type") != "blob" or item.get("mode") != "100644" or SHA.fullmatch(item.get("sha", "")) is None or type(item.get("size")) is not int or not 0 <= item["size"] <= MAX_BLOB_BYTES:
            _reject("Invalid history blob mode, identity, or size")
        entries[path] = item
        total += item["size"]
    if total > MAX_HISTORY_BYTES or not {"index.json", "latest.json", "index.html", "summary.md"}.issubset(entries):
        _reject("History is incomplete or exceeds size limit")
    def blob(path):
        item = entries[path]
        result = client.call("GET", f"/git/blobs/{item['sha']}")
        if not isinstance(result, dict) or result.get("encoding") != "base64" or not isinstance(result.get("content"), str) or result.get("size") != item["size"] or len(result["content"]) > MAX_BLOB_BYTES * 2:
            _reject("Invalid history blob encoding or size")
        try:
            raw = base64.b64decode("".join(result["content"].splitlines()), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise PublishError("Invalid history blob base64") from exc
        if len(raw) != item["size"]:
            _reject("History blob size mismatch")
        return raw
    index = _json(blob("index.json"), "history index")
    if not isinstance(index, dict) or set(index) != {"schema", "runs", "latest", "last_complete", "comparison_baseline"} or index["schema"] != HISTORY_SCHEMA or not isinstance(index["runs"], list) or not 1 <= len(index["runs"]) <= RETENTION:
        _reject("Invalid history index schema")
    runs = []
    for entry in index["runs"]:
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS or not isinstance(entry.get("path"), str) or RUN_PATH.fullmatch(entry["path"]) is None or entry["path"] not in entries:
            _reject("Invalid history index entry")
        saved = validate_receipt(_json(blob(entry["path"]), entry["path"]))
        if saved["repository"] != client.repository or _entry(saved) != entry:
            _reject("History index identity or hash mismatch")
        if runs and (_order(saved) <= _order(runs[-1]) or saved["previous_receipt_hash"] != runs[-1]["receipt_hash"]):
            _reject("Invalid history ordering or prior receipt hash")
        runs.append(saved)
    if set(path for path in entries if RUN_PATH.fullmatch(path)) != {entry["path"] for entry in index["runs"]} or index["latest"] != _entry(runs[-1])["path"]:
        _reject("History index paths do not match retained receipts")
    latest = validate_receipt(_json(blob("latest.json"), "latest receipt"))
    if latest != runs[-1]:
        _reject("History latest receipt differs from index")
    baseline = None
    if index["last_complete"] is not None:
        if "last_complete.json" not in entries:
            _reject("History complete baseline is missing")
        baseline = validate_receipt(_json(blob("last_complete.json"), "last complete receipt"))
        metadata = {key: baseline[key] for key in ("run_id", "run_attempt", "receipt_hash")}
        if baseline["repository"] != client.repository or baseline["state"] == "incomplete" or index["last_complete"] != metadata or _order(baseline) > _order(latest):
            _reject("Invalid history complete baseline identity")
    elif "last_complete.json" in entries:
        _reject("Unexpected history complete baseline")
    complete_runs = [run for run in runs if run["state"] != "incomplete"]
    if complete_runs and baseline != complete_runs[-1]:
        _reject("History last complete baseline differs from retained receipts")
    comparison_baseline = index["comparison_baseline"]
    if comparison_baseline is not None:
        validate_receipt(comparison_baseline)
        if comparison_baseline["repository"] != client.repository or comparison_baseline["state"] == "incomplete" or _order(comparison_baseline) >= _order(latest):
            _reject("Invalid history comparison baseline")
    if latest["state"] == "incomplete" and comparison_baseline != baseline:
        _reject("Incomplete history lost its comparison baseline")
    prior_complete = [run for run in runs[:-1] if run["state"] != "incomplete"]
    if prior_complete and comparison_baseline != prior_complete[-1]:
        _reject("History comparison baseline differs from preceding complete receipt")
    if not prior_complete and runs[0]["previous_receipt_hash"] is None and comparison_baseline is not None:
        _reject("History comparison baseline invents a preceding complete receipt")
    return head, runs, baseline, comparison_baseline


def _evidence(input_dir, current):
    evidence = {}
    for name, expected in current["evidence_hashes"].items():
        path = input_dir / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BLOB_BYTES:
            _reject(f"Invalid or missing evidence file {name}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            _reject(f"Evidence content hash mismatch for {name}")
        evidence[name] = raw
    # Unsealed evidence may not be introduced into a regenerated receipt.
    for name in EVIDENCE_FILES:
        if (input_dir / name).exists() and name not in evidence:
            _reject(f"Evidence file {name} lacks a receipt content hash")
    return evidence


def _write_history(client, head, runs, baseline, comparison_baseline, output_dir):
    index = {"schema": HISTORY_SCHEMA, "runs": [_entry(run) for run in runs],
             "latest": _entry(runs[-1])["path"],
             "last_complete": {key: baseline[key] for key in ("run_id", "run_attempt", "receipt_hash")} if baseline else None,
             "comparison_baseline": comparison_baseline}
    files = {"index.json": report.canonical_bytes(index), "latest.json": report.canonical_bytes(runs[-1]),
             "index.html": report.render_html(runs[-1], report.compare(runs[-1], comparison_baseline),
                                                history=runs, durable=True).encode('utf-8'),
             "summary.md": (output_dir / "summary.md").read_bytes()}
    files.update({_entry(run)["path"]: report.canonical_bytes(run) for run in runs})
    if baseline is not None:
        files["last_complete.json"] = report.canonical_bytes(baseline)
    if any(len(data) > MAX_BLOB_BYTES for data in files.values()) or sum(map(len, files.values())) > MAX_HISTORY_BYTES:
        _reject("Generated history exceeds size limits")
    entries = []
    for path, data in sorted(files.items()):
        blob = client.call("POST", "/git/blobs", {"encoding": "base64", "content": base64.b64encode(data).decode("ascii")})
        if not isinstance(blob, dict) or SHA.fullmatch(blob.get("sha", "")) is None:
            _reject("Invalid created Git blob identity")
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = client.call("POST", "/git/trees", {"tree": entries})
    if not isinstance(tree, dict) or SHA.fullmatch(tree.get("sha", "")) is None:
        _reject("Invalid created Git tree identity")
    latest = runs[-1]
    commit = client.call("POST", "/git/commits", {"message": f"Observatory run {latest['run_id']} attempt {latest['run_attempt']}",
                         "tree": tree["sha"], "parents": [head] if head else []})
    if not isinstance(commit, dict) or SHA.fullmatch(commit.get("sha", "")) is None:
        _reject("Invalid created Git commit identity")
    if head is None:
        client.call("POST", "/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    else:
        # Fast-forward-only update is the lease: a concurrent descendant of the
        # old head makes this sibling commit fail instead of replacing history.
        client.call("PATCH", f"/git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": False})
    return commit["sha"]


def _issue(client, current, comparison):
    selected = []
    for page in range(1, 101):
        issues = client.call("GET", f"/issues?state=all&per_page=100&page={page}")
        if not isinstance(issues, list) or len(issues) > 100:
            _reject("Invalid GitHub issues response")
        for issue in issues:
            if not isinstance(issue, dict):
                _reject("Invalid GitHub issue metadata")
            user = issue.get("user")
            if "pull_request" not in issue and isinstance(user, dict) and user.get("login") == "github-actions[bot]" and user.get("type") == "Bot" and isinstance(issue.get("body"), str) and MARKER in issue["body"].splitlines():
                if not _positive(issue.get("number")) or issue.get("state") not in {"open", "closed"}:
                    _reject("Invalid bot-owned incident issue identity")
                selected.append(issue)
        if len(issues) < 100:
            break
    else:
        _reject("Issue pagination exceeds bounded search")
    if len(selected) > 1:
        _reject("Multiple bot-owned Observatory incident issues exist")
    incident = selected[0] if selected else None
    if current["state"] == "healthy" and incident is None:
        return None
    lines = [MARKER, "", f"Latest observation: **{current['state']}**.", "", f"[Actions evidence and artifacts]({current['run_url']})",
             f"[Current proof atlas](https://github.com/{client.repository}/blob/{BRANCH}/index.html)",
             f"[Source revision](https://github.com/{client.repository}/commit/{current['commit']})", "", "Publication: succeeded.", ""]
    for title, key in (("New regressions", "regressions"), ("Continuing failures", "continuing_failures"),
                       ("Recoveries", "recoveries"), ("Lost observations", "lost_observations")):
        # JSON string quoting makes diagnostics/check labels literal Markdown.
        values = comparison.get(key, [])
        lines.append(f"{title}: " + (", ".join(f"`{item}`" for item in values) if values else "none") + ".")
    failures = [key for key, finding in current["findings"].items() if finding["state"] == "fail"]
    lines.extend(["", "Current failures: " + (", ".join(f"`{item}`" for item in failures) if failures else "none") + ".",
                  "", "Reasons:"])
    for reason in current["reasons"]:
        safe_reason = reason.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\r", " ").replace("\n", " ")
        # Avoid activating Markdown links, mentions, and backticks in evidence.
        safe_reason = re.sub(r"([\\`*_\[\]@])", r"\\\1", safe_reason)
        lines.append("- " + safe_reason)
    body = {"title": ISSUE_TITLE, "body": "\n".join(lines), "state": "closed" if current["state"] == "healthy" else "open"}
    if incident:
        client.call("PATCH", f"/issues/{incident['number']}", body)
        return incident["number"]
    created = client.call("POST", "/issues", {key: value for key, value in body.items() if key != "state"})
    if not isinstance(created, dict) or not _positive(created.get("number")):
        _reject("Invalid created incident issue identity")
    return created["number"]


def publish(input_dir, output_dir, client, environment=None):
    """Validate, regenerate, and publish one trusted main-run observation."""
    identity = _identity(os.environ if environment is None else environment)
    if client.repository != identity["repository"]:
        _reject("Publisher repository differs from trusted Actions identity")
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    current = _load_current(input_dir, identity)
    evidence = _evidence(input_dir, current)
    _verify_api_identity(client, identity)
    head, runs, last_complete, retry_baseline = _read_history(client)
    retry = False
    if runs:
        if _order(current) < _order(runs[-1]):
            _reject("Publication is older than latest run ordering")
        if _order(current) == _order(runs[-1]):
            # The predecessor is publisher-owned; the collected envelope has
            # no prior history identity. Everything else must be byte-identical.
            incoming = copy.deepcopy(current)
            if not (input_dir / "run.json").exists():
                # Reuse this same run's fallback observation time on retries.
                # A preceding different run is never promoted to current data.
                incoming["started_at"] = runs[-1]["started_at"]
                incoming["finished_at"] = runs[-1]["finished_at"]
            incoming["previous_receipt_hash"] = runs[-1]["previous_receipt_hash"]
            incoming = report.seal_receipt(incoming)
            if incoming != runs[-1]:
                _reject("Same run/attempt retry has different receipt content")
            current = runs[-1]
            baseline = retry_baseline
            retry = True
        else:
            current["previous_receipt_hash"] = runs[-1]["receipt_hash"]
            current = report.seal_receipt(current)
            baseline = last_complete
    else:
        baseline = None
        current["previous_receipt_hash"] = None
        current = report.seal_receipt(current)
    # Remove only generated bundle files/known evidence; never copy supplied
    # HTML/Markdown. Reading evidence first permits --input == --output.
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in EVIDENCE_FILES | {"run.json", "comparison.json", "index.html", "summary.md", "SHA256SUMS"}:
        path = output_dir / name
        if path.is_symlink():
            _reject("Output bundle contains a symbolic link")
        if path.is_file():
            path.unlink()
    for name, data in evidence.items():
        (output_dir / name).write_bytes(data)
    timeline = runs if retry else (runs + [current])[-RETENTION:]
    report.write_bundle(current, output_dir, baseline=baseline, history=timeline)
    regenerated = validate_receipt(_json((output_dir / "run.json").read_bytes(), "regenerated run.json"))
    if regenerated != current:
        _reject("Regenerated receipt differs from validated content")
    comparison = report.compare(current, baseline)
    if not retry:
        if current["state"] != "incomplete":
            last_complete = current
        head = _write_history(client, head, timeline, last_complete, baseline, output_dir)
    issue_number = _issue(client, current, comparison)
    return {"run_id": current["run_id"], "run_attempt": current["run_attempt"], "state": current["state"],
            "history_commit": head, "idempotent": retry, "incident_issue": issue_number}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        client = GitHubClient(os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", ""))
        result = publish(args.input, args.output, client)
    except (PublishError, OSError, ValueError, RecursionError) as exc:
        print(f"Observatory publication failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
