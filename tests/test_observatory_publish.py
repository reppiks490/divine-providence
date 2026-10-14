"""Publisher contracts exercised against an in-memory GitHub REST server."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest


REPOSITORY = "reppiks490/divine-providence"
MARKER = "<!-- icarus-observatory:incident:v1 -->"


def module():
    assert importlib.util.find_spec("scripts.observatory.publish"), "publisher is not implemented"
    return importlib.import_module("scripts.observatory.publish")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def seal(receipt):
    result = copy.deepcopy(receipt)
    for finding in result["findings"].values():
        finding.pop("finding_hash", None)
        finding["finding_hash"] = hashlib.sha256(canonical(finding)).hexdigest()
    result.pop("receipt_hash", None)
    result["receipt_hash"] = hashlib.sha256(canonical(result)).hexdigest()
    return result


def environment(run_id=1, attempt=1):
    return {"GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": str(run_id),
            "GITHUB_RUN_ATTEMPT": str(attempt), "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_SERVER_URL": "https://github.com"}


def receipt(run_id=1, state="healthy", attempt=1):
    finding_state = {"healthy": "pass", "unhealthy": "fail", "incomplete": "not_observed"}[state]
    value = {"schema": "icarus.observatory.run.v1", "run_id": run_id,
             "run_attempt": attempt, "event": "workflow_dispatch", "repository": REPOSITORY,
             "ref": "refs/heads/main", "commit": "a" * 40,
             "run_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
             "started_at": "2026-10-14T04:17:00Z", "finished_at": "2026-10-14T04:18:00Z",
             "python": "3.11", "platform": "Linux", "validator_exit_code": 0,
             "hub_exit_code": 0 if state == "healthy" else 1,
             "inventory": {"systems": ["nexus"], "connections": {"fixture": {"systems": ["nexus"], "contract": "fixture.v1"}},
                           "adversarial": ["hostile.py"], "coverage": {"nexus": {"status": "connected"}}},
             "dependencies": [], "environment_hash": hashlib.sha256(canonical({"python": "3.11", "platform": "Linux", "dependencies": []})).hexdigest(),
             "state": state, "reasons": [] if state == "healthy" else ["fixture observation"],
             "findings": {"hub/tests": {"id": "hub/tests", "state": finding_state,
               "counts": {"passed": 1} if state == "healthy" else {"failed": 1} if state == "unhealthy" else None,
               "seconds": 1.0 if state != "incomplete" else None,
               "diagnostic": "fixture", "systems": [], "run_id": run_id, "commit": "a" * 40}},
             "evidence_hashes": {}, "previous_receipt_hash": None,
             "execution_authorized": False, "production_authorized": False,
             "live_engine": "not_observed"}
    for finding_id in ("suite/nexus", "compile/nexus", "adversarial/hostile.py", "connection/fixture"):
        value["findings"][finding_id] = {"id": finding_id, "state": "not_observed" if state == "incomplete" else "pass",
                "counts": {"passed": 1} if finding_id.startswith("suite/") and state != "incomplete" else None,
                "seconds": 1.0 if finding_id.startswith("suite/") and state != "incomplete" else None,
                "diagnostic": "fixture", "systems": ["nexus"] if finding_id != "adversarial/hostile.py" else [],
                "run_id": run_id, "commit": "a" * 40}
    return seal(value)


def input_bundle(tmp_path, run_id=1, state="healthy", attempt=1):
    path = tmp_path / f"in-{run_id}-{attempt}"
    path.mkdir(exist_ok=True)
    (path / "run.json").write_bytes(canonical(receipt(run_id, state, attempt)))
    return path


class GitHub:
    """Stateful fake supports Git data, run identity, and issue endpoints."""

    def __init__(self):
        self.head = None
        self.blobs = {}
        self.trees = {}
        self.commits = {}
        self.issues = []
        self.calls = []
        self.run_overrides = {}
        self.deny = None
        self.deny_path = None
        self.conflict = False

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, copy.deepcopy(body)))
        if (self.deny and method == self.deny) or (self.deny_path and path.removeprefix(f"/repos/{REPOSITORY}") == self.deny_path and method != "GET"):
            return 403, {"message": "Resource not accessible by integration"}
        path = path.removeprefix(f"/repos/{REPOSITORY}")
        if path.startswith("/actions/runs/"):
            run_id = int(path.rsplit("/", 1)[-1])
            return 200, {"id": run_id, "run_attempt": self.run_overrides.get("run_attempt", 1),
                         "head_sha": "a" * 40, "head_branch": "main", "event": "workflow_dispatch",
                         "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
                         "repository": {"full_name": REPOSITORY}, **self.run_overrides}
        if method == "GET" and path == "/git/ref/heads/observatory-history":
            return (200, {"object": {"sha": self.head}}) if self.head else (404, {})
        if method == "GET" and path.startswith("/git/commits/"):
            return 200, self.commits[path.rsplit("/", 1)[-1]]
        if method == "GET" and path.startswith("/git/trees/"):
            key = path.rsplit("/", 1)[-1].split("?", 1)[0]
            return 200, {"tree": self.trees[key], "truncated": False}
        if method == "GET" and path.startswith("/git/blobs/"):
            data = self.blobs[path.rsplit("/", 1)[-1]]
            return 200, {"encoding": "base64", "size": len(data),
                         "content": base64.b64encode(data).decode()}
        if method == "POST" and path == "/git/blobs":
            data = base64.b64decode(body["content"]) if body["encoding"] == "base64" else body["content"].encode()
            key = hashlib.sha1(data).hexdigest()
            self.blobs[key] = data
            return 201, {"sha": key}
        if method == "POST" and path == "/git/trees":
            assert "base_tree" not in body, "history commits contain only approved data"
            key = hashlib.sha1(canonical(body)).hexdigest()
            self.trees[key] = [{**entry, "size": len(self.blobs[entry["sha"]])} for entry in body["tree"]]
            return 201, {"sha": key}
        if method == "POST" and path == "/git/commits":
            key = hashlib.sha1(canonical(body)).hexdigest()
            self.commits[key] = {**body, "tree": {"sha": body["tree"]}}
            return 201, {"sha": key}
        if method == "POST" and path == "/git/refs":
            assert body["ref"] == "refs/heads/observatory-history"
            if self.head or self.conflict:
                return 422, {"message": "Reference already exists"}
            self.head = body["sha"]
            return 201, {"object": {"sha": self.head}}
        if method == "PATCH" and path == "/git/refs/heads/observatory-history":
            assert body["force"] is False
            assert self.commits[body["sha"]]["parents"] == [self.head]
            if self.conflict:
                return 422, {"message": "Update is not a fast forward"}
            self.head = body["sha"]
            return 200, {"object": {"sha": self.head}}
        if method == "GET" and path.startswith("/issues?"):
            page = int(path.rsplit("page=", 1)[-1])
            return 200, copy.deepcopy(self.issues[(page - 1) * 100:page * 100])
        if method == "POST" and path == "/issues":
            issue = {"number": len(self.issues) + 1, "state": "open", "user": {"login": "github-actions[bot]", "type": "Bot"}, **body}
            self.issues.append(issue)
            return 201, issue
        if method == "PATCH" and path.startswith("/issues/"):
            issue = next(item for item in self.issues if item["number"] == int(path.rsplit("/", 1)[-1]))
            issue.update(body)
            return 200, issue
        raise AssertionError((method, path, body))

    def files(self):
        if not self.head:
            return {}
        return {entry["path"]: self.blobs[entry["sha"]] for entry in self.trees[self.commits[self.head]["tree"]["sha"]]}


def publish(github, input_path, output_path, env=None):
    p = module()
    return p.publish(input_path, output_path, p.GitHubClient("test-secret", REPOSITORY, github), environment=env or environment())


def test_incident_lifecycle_reuses_one_bot_issue_and_never_comments(tmp_path):
    github = GitHub()
    for run_id, state in [(1, "unhealthy"), (2, "incomplete"), (3, "healthy"), (4, "unhealthy")]:
        publish(github, input_bundle(tmp_path, run_id, state), tmp_path / "out", environment(run_id))
        assert len(github.issues) == 1
        assert github.issues[0]["state"] == ("closed" if state == "healthy" else "open")
        assert MARKER in github.issues[0]["body"].splitlines()
    assert not any("comments" in path for _, path, _ in github.calls)
    assert github.issues[0]["body"].count("actions/runs/4") >= 1
    assert "Publication: succeeded" in github.issues[0]["body"]


def test_history_keeps_ninety_receipts_and_last_complete_after_long_gap(tmp_path):
    github = GitHub()
    initial = None
    for run_id in range(1, 94):
        publish(github, input_bundle(tmp_path, run_id, "healthy" if run_id == 1 else "incomplete"),
                tmp_path / "out", environment(run_id))
        if run_id == 1:
            initial = json.loads(github.files()["latest.json"])
    files = github.files()
    assert len([path for path in files if path.startswith("runs/")]) == 90
    assert "runs/1-1.json" not in files
    assert json.loads(files["last_complete.json"]) == initial
    oldest = json.loads(files["runs/4-1.json"])
    assert oldest["previous_receipt_hash"] is not None
    index = json.loads(files["index.json"])
    assert index["schema"] == "icarus.observatory.history.v1"
    assert [entry["run_id"] for entry in index["runs"]] == list(range(4, 94))
    comparison = json.loads((tmp_path / "out" / "comparison.json").read_text())
    assert comparison["baseline_run_id"] == 1
    source = input_bundle(tmp_path, 94)
    publish(github, source, tmp_path / "out", environment(94))
    head = github.head
    publish(github, source, tmp_path / "out", environment(94))
    assert github.head == head
    assert json.loads(github.files()["last_complete.json"])["run_id"] == 94
    assert json.loads((tmp_path / "out" / "comparison.json").read_text())["baseline_run_id"] == 1


def test_order_and_idempotency_retry_without_history_writes(tmp_path):
    github = GitHub()
    source = input_bundle(tmp_path, 7, "unhealthy")
    publish(github, source, tmp_path / "out", environment(7))
    head = github.head
    github.calls.clear()
    publish(github, source, tmp_path / "out", environment(7))
    assert github.head == head
    assert not any("/git/" in path and method != "GET" for method, path, _ in github.calls)
    with pytest.raises(module().PublishError, match="older|order"):
        publish(github, input_bundle(tmp_path, 6), tmp_path / "out", environment(6))
    assert github.head == head
    github.run_overrides["run_attempt"] = 2
    publish(github, input_bundle(tmp_path, 7, "healthy", 2), tmp_path / "out", environment(7, 2))
    assert json.loads(github.files()["latest.json"])["run_attempt"] == 2


@pytest.mark.parametrize("field,value", [("GITHUB_REF", "refs/heads/topic"), ("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_RUN_ID", "9"), ("GITHUB_SHA", "b" * 40)])
def test_trusted_environment_guard_rejects_before_api_writes(tmp_path, field, value):
    github = GitHub()
    env = environment()
    env[field] = value
    with pytest.raises(module().PublishError):
        publish(github, input_bundle(tmp_path), tmp_path / "out", env)
    assert not any(method != "GET" for method, _, _ in github.calls)


def test_github_run_metadata_must_agree_with_receipt(tmp_path):
    github = GitHub()
    github.run_overrides["head_sha"] = "b" * 40
    with pytest.raises(module().PublishError, match="identity|metadata"):
        publish(github, input_bundle(tmp_path), tmp_path / "out")
    assert not any(method != "GET" for method, _, _ in github.calls)


@pytest.mark.parametrize("coverage", ["connected", {"status": "connected", "connections": 1},
                                     {"status": "standalone", "reason": ["oops"]}, {"status": "invented"}])
def test_malformed_coverage_rejected_before_api_writes(tmp_path, coverage):
    source = input_bundle(tmp_path)
    value = json.loads((source / "run.json").read_text())
    value["inventory"]["coverage"]["nexus"] = coverage
    (source / "run.json").write_bytes(canonical(seal(value)))
    github = GitHub()
    with pytest.raises(module().PublishError, match="coverage"):
        publish(github, source, tmp_path / "out")
    assert not any(method != "GET" for method, _, _ in github.calls)


@pytest.mark.parametrize("mutation", ["hash", "schema", "authority", "finding_hash", "identity", "boolean_run", "unknown_field", "environment_hash", "complete_unobserved", "missing_suite_duration", "missing_failed_test_counts"])
def test_invalid_receipts_are_rejected(tmp_path, mutation):
    source = input_bundle(tmp_path)
    value = json.loads((source / "run.json").read_text())
    if mutation == "hash":
        value["reasons"].append("tampered")
    elif mutation == "schema":
        value["schema"] = "unknown"
        value = seal(value)
    elif mutation == "authority":
        value["production_authorized"] = True
        value = seal(value)
    elif mutation == "finding_hash":
        value["findings"]["hub/tests"]["finding_hash"] = "0" * 64
        value.pop("receipt_hash")
        value["receipt_hash"] = hashlib.sha256(canonical(value)).hexdigest()
    elif mutation == "identity":
        value["findings"]["hub/tests"]["run_id"] = 2
        value = seal(value)
    elif mutation == "boolean_run":
        value["run_id"] = True
        value = seal(value)
    elif mutation == "unknown_field":
        value["execute"] = "oops"
        value = seal(value)
    elif mutation == "environment_hash":
        value["environment_hash"] = "0" * 64
        value = seal(value)
    elif mutation == "complete_unobserved":
        value["state"] = "unhealthy"
        value["hub_exit_code"] = 1
        value["findings"]["hub/tests"]["state"] = "fail"
        value["findings"]["compile/nexus"]["state"] = "not_observed"
        value = seal(value)
    elif mutation == "missing_suite_duration":
        value["findings"]["suite/nexus"]["seconds"] = None
        value = seal(value)
    elif mutation == "missing_failed_test_counts":
        value["state"] = "unhealthy"
        value["hub_exit_code"] = 1
        value["findings"]["hub/tests"].update(state="fail", counts=None)
        value = seal(value)
    (source / "run.json").write_bytes(canonical(value))
    github = GitHub()
    with pytest.raises(module().PublishError):
        publish(github, source, tmp_path / "out")
    assert not any(method != "GET" for method, _, _ in github.calls)


def test_evidence_hash_verified_and_dashboard_regenerated(tmp_path):
    source = input_bundle(tmp_path)
    log = b"bounded fixture log\n"
    (source / "hub.stdout.log").write_bytes(log)
    (source / "index.html").write_text("<script>injected()</script>")
    value = json.loads((source / "run.json").read_text())
    value["evidence_hashes"] = {"hub.stdout.log": hashlib.sha256(log).hexdigest()}
    (source / "run.json").write_bytes(canonical(seal(value)))
    github = GitHub()
    publish(github, source, tmp_path / "out")
    assert (tmp_path / "out" / "hub.stdout.log").read_bytes() == log
    assert "injected()" not in (tmp_path / "out" / "index.html").read_text()
    (source / "hub.stdout.log").write_text("changed")
    with pytest.raises(module().PublishError, match="evidence|hash"):
        publish(github, source, tmp_path / "out")


@pytest.mark.parametrize("mutation", ["receipt_hash", "script", "baseline_hash", "index_order"])
def test_history_is_validated_as_bounded_data(tmp_path, mutation):
    github = GitHub()
    publish(github, input_bundle(tmp_path), tmp_path / "out")
    tree = github.trees[github.commits[github.head]["tree"]["sha"]]
    if mutation == "script":
        tree.append({"path": "install.py", "mode": "100644", "type": "blob", "sha": "unused", "size": 1})
    else:
        path = {"receipt_hash": "latest.json", "baseline_hash": "last_complete.json", "index_order": "index.json"}[mutation]
        item = next(entry for entry in tree if entry["path"] == path)
        value = json.loads(github.blobs[item["sha"]])
        if mutation == "index_order":
            value["runs"][0]["run_id"] = 99
        else:
            value["receipt_hash"] = "0" * 64
        github.blobs[item["sha"]] = canonical(value)
        item["size"] = len(github.blobs[item["sha"]])
    github.calls.clear()
    with pytest.raises(module().PublishError):
        publish(github, input_bundle(tmp_path, 2), tmp_path / "out", environment(2))
    assert not any(method != "GET" for method, _, _ in github.calls)


def test_human_marker_issue_is_never_edited(tmp_path):
    github = GitHub()
    github.issues.append({"number": 1, "state": "open", "title": "human issue", "body": MARKER,
                          "user": {"login": "maintainer", "type": "User"}})
    publish(github, input_bundle(tmp_path, state="unhealthy"), tmp_path / "out")
    assert github.issues[0]["title"] == "human issue"
    assert len(github.issues) == 2
    assert github.issues[1]["user"]["type"] == "Bot"


def test_bot_incident_search_paginates_and_requires_standalone_marker(tmp_path):
    github = GitHub()
    github.issues = [{"number": i, "state": "open", "title": "other", "body": "unrelated " + MARKER,
                      "user": {"login": "github-actions[bot]", "type": "Bot"}} for i in range(1, 101)]
    github.issues.append({"number": 101, "state": "closed", "title": "old incident", "body": MARKER,
                         "user": {"login": "github-actions[bot]", "type": "Bot"}})
    publish(github, input_bundle(tmp_path, state="unhealthy"), tmp_path / "out")
    assert len(github.issues) == 101
    assert github.issues[-1]["state"] == "open"
    assert github.issues[0]["title"] == "other"


def test_corrupt_latest_comparison_baseline_rejected_when_prior_complete_is_retained(tmp_path):
    github = GitHub()
    for run_id in (1, 2):
        publish(github, input_bundle(tmp_path, run_id), tmp_path / "out", environment(run_id))
    tree = github.trees[github.commits[github.head]["tree"]["sha"]]
    item = next(entry for entry in tree if entry["path"] == "index.json")
    index = json.loads(github.blobs[item["sha"]])
    index["comparison_baseline"] = None
    github.blobs[item["sha"]] = canonical(index)
    item["size"] = len(github.blobs[item["sha"]])
    github.calls.clear()
    with pytest.raises(module().PublishError, match="comparison baseline"):
        publish(github, input_bundle(tmp_path, 3), tmp_path / "out", environment(3))
    assert not any(method != "GET" for method, _, _ in github.calls)


def test_missing_artifact_generates_incomplete_receipt_with_trusted_identity(tmp_path):
    github = GitHub()
    publish(github, tmp_path / "missing", tmp_path / "out", environment(42))
    value = json.loads(github.files()["latest.json"])
    assert value["state"] == "incomplete"
    assert value["run_id"] == 42
    assert value["validator_exit_code"] is None
    assert value["execution_authorized"] is False
    assert len(github.issues) == 1


def test_partial_artifact_without_receipt_retains_evidence_as_incomplete(tmp_path):
    source = tmp_path / "partial"
    source.mkdir()
    evidence = b'{"schema":"icarus.observatory.collection.v1"}'
    (source / "collection.json").write_bytes(evidence)
    github = GitHub()
    publish(github, source, tmp_path / "out")
    value = json.loads(github.files()["latest.json"])
    assert value["state"] == "incomplete"
    assert value["evidence_hashes"]["collection.json"] == hashlib.sha256(evidence).hexdigest()
    assert (tmp_path / "out" / "collection.json").read_bytes() == evidence


def test_absent_artifact_retry_keeps_current_run_receipt_identity(tmp_path):
    github = GitHub()
    publish(github, tmp_path / "missing", tmp_path / "out")
    previous_head = github.head
    publish(github, tmp_path / "missing", tmp_path / "out")
    assert github.head == previous_head


def test_unicode_diagnostics_preserve_canonical_hashes(tmp_path):
    source = input_bundle(tmp_path)
    value = json.loads((source / "run.json").read_text())
    value["findings"]["hub/tests"]["diagnostic"] = "観測結果 — π"
    (source / "run.json").write_bytes(canonical(seal(value)))
    github = GitHub()
    publish(github, source, tmp_path / "out")
    assert json.loads(github.files()["latest.json"])["findings"]["hub/tests"]["diagnostic"] == "観測結果 — π"


def test_denied_permissions_fail_after_preserving_regenerated_bundle(tmp_path):
    github = GitHub()
    github.deny = "POST"
    with pytest.raises(module().PublishError, match="403"):
        publish(github, input_bundle(tmp_path), tmp_path / "out")
    assert (tmp_path / "out" / "run.json").is_file()
    assert github.head is None


def test_denied_issue_creation_retries_existing_history_without_duplicate_receipt(tmp_path):
    github = GitHub()
    github.deny_path = "/issues"
    source = input_bundle(tmp_path, state="unhealthy")
    with pytest.raises(module().PublishError, match="403"):
        publish(github, source, tmp_path / "out")
    assert github.head is not None
    previous_head = github.head
    github.deny_path = None
    github.calls.clear()
    publish(github, source, tmp_path / "out")
    assert github.head == previous_head
    assert len(github.issues) == 1
    assert not any("/git/" in path and method != "GET" for method, path, _ in github.calls)


def test_ref_race_is_rejected_without_force_or_issue_update(tmp_path):
    github = GitHub()
    publish(github, input_bundle(tmp_path), tmp_path / "out")
    previous_head = github.head
    github.conflict = True
    with pytest.raises(module().PublishError, match="422"):
        publish(github, input_bundle(tmp_path, 2, "unhealthy"), tmp_path / "out", environment(2))
    assert github.head == previous_head
    assert not github.issues
