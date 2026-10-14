from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pandas as pd
import pytest

from scripts.institution import common, collect, driver, publish, report, sources

ROOT = Path(__file__).resolve().parents[1]


def source():
    return {"sha256": "b" * 64, "repository_url": "https://github.com/reppiks490/test",
            "revision": "c" * 40, "archive": "bars.zip", "member": "bars.csv",
            "rows_budget_estimate": 1800, "bytes": 90000, "label": "bars.csv",
            "identity_status": "filename_hint_unverified", "price_basis": "CANDLE_PROXY"}


def result(outcome="rejected"):
    return {**common.AUTHORITY, "outcome": outcome, "reasons": ["no_development_edge"],
            "models": [], "hypotheses": [], "champion": None}


@pytest.fixture
def action_env(monkeypatch):
    values = {"GITHUB_REPOSITORY": common.REPOSITORY, "GITHUB_SHA": "a" * 40,
              "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_dispatch",
              "GITHUB_RUN_ID": "100", "GITHUB_RUN_ATTEMPT": "1"}
    for k, v in values.items():
        monkeypatch.setenv(k, v)
    return publish._identity(values)


def cycle(tmp_path, monkeypatch, memory=None, parent=None, outcome="rejected"):
    memory = memory or common.empty_memory()
    monkeypatch.setattr(sources, "catalogue", lambda _: ([source()], [{"revision": "c" * 40}]))
    return collect.collect([], tmp_path, ROOT, memory_loader=lambda: (memory, parent),
                           researcher=lambda *args: result(outcome), feeds=lambda: ([], []))


def test_memory_skips_exact_failure_and_retries_interruptions(tmp_path, monkeypatch, action_env):
    run = cycle(tmp_path, monkeypatch)
    memory = common.read_json((tmp_path / "memory.json").read_bytes())
    assert run["state"] == "complete"
    assert not collect.eligible(source(), memory, run["context"]["context_hash"])
    assert collect.eligible(source(), memory, "changed-protocol")
    key = run["experiments"][0]["id"]
    memory["experiments"][key]["outcome"] = "interrupted"
    assert collect.eligible(source(), memory, run["context"]["context_hash"])
    memory["experiments"][key]["attempts"] = 3
    assert not collect.eligible(source(), memory, run["context"]["context_hash"])


def test_presentation_changes_do_not_restart_scientific_memory(tmp_path):
    scripts = tmp_path / "scripts/institution"
    scripts.mkdir(parents=True)
    for name in ("common.py", "driver.py", "sources.py", "agenda.py"):
        (scripts / name).write_text("scientific protocol")
    before = common.context(tmp_path)["context_hash"]
    (scripts / "report.py").write_text("new presentation")
    assert common.context(tmp_path)["context_hash"] == before
    (scripts / "driver.py").write_text("changed scientific implementation")
    assert common.context(tmp_path)["context_hash"] != before


def test_collection_timeout_is_incomplete_and_remembers_retry(tmp_path, monkeypatch, action_env):
    run = cycle(tmp_path, monkeypatch, outcome="interrupted")
    memory = common.read_json((tmp_path / "memory.json").read_bytes())
    assert run["state"] == "incomplete"
    assert memory["experiments"][run["experiments"][0]["id"]]["outcome"] == "interrupted"


def test_missing_memory_fails_closed_and_preserves_evidence(tmp_path, monkeypatch, action_env):
    def broken():
        raise TimeoutError()
    run = collect.collect([], tmp_path, ROOT, memory_loader=broken)
    assert run["state"] == "incomplete"
    assert run["experiments"] == []
    assert not (tmp_path / "memory.json").exists()


def test_event_observation_is_not_moved_forward():
    memory = common.empty_memory()
    earlier = {"id": "x", "first_observed_at": "2026-01-01T00:00:00Z"}
    collect.merge_events(memory, [earlier])
    collect.merge_events(memory, [{**earlier, "first_observed_at": "2026-10-14T00:00:00Z"}])
    assert memory["events"]["x"] == earlier


def test_oracle_agenda_diversifies_source_groups_before_results():
    from scripts.institution.agenda import select_sources
    queue = [{**source(), "sha256": str(i)*64, "archive": archive,
              "rows_budget_estimate": rows} for i, archive, rows in
             [(1, "same.zip", 2000), (2, "same.zip", 2100), (3, "other.zip", 2500)]]
    chosen, agenda = select_sources(queue, common.empty_memory(), "context", ROOT, 2)
    assert {s["archive"] for s in chosen} == {"same.zip", "other.zip"}
    assert agenda["owner"] == "ORACLE.ResearchScheduler"
    assert all(c["hypothesis"]["created_ns"] == agenda["decision_ns"] for c in agenda["choices"])
    assert all(c["job_specification"]["production_authorized"] is False for c in agenda["choices"])
    expected = {"1"*64: 4, "3"*64: 5}
    assert {c["source_sha256"]: c["estimated_development_folds"] for c in agenda["choices"]} == expected


def test_feeds_record_true_provenance_and_unavailability():
    raw = b'<rss><channel><item><title>Real release</title><link>https://www.ecb.europa.eu/news</link><pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>'
    def fetcher(url, limit):
        if "sec.gov" in url:
            raise TimeoutError()
        return raw
    events, receipts = sources.announcements(fetcher)
    assert len(events) == 2
    assert all(e["price_effect"] == "untested" for e in events)
    assert receipts[0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipts[-1]["state"] == "unavailable"


@pytest.mark.parametrize("name", ["../escape.csv", "/absolute.csv", "foo\\escape.csv", "__MACOSX/._bars.csv"])
def test_archive_paths_cannot_escape(name):
    info = zipfile.ZipInfo(name)
    info.file_size = 100
    assert not sources.safe_member(info)


def test_selected_member_hash_is_checked(tmp_path):
    archive = tmp_path / "bars.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("bars.csv", "time,open,high,low,close\n1,1,2,1,2\n")
    s = {**source(), "_archive_path": str(archive)}
    with pytest.raises(ValueError, match="changed"):
        sources.materialize(s, tmp_path / "selected.csv")
    assert not (tmp_path / "selected.csv").exists()


def test_hash_and_nested_authority_rejected():
    memory = common.empty_memory()
    memory["updated_at"] = "tampered"
    with pytest.raises(ValueError, match="hash"):
        common.validate(memory, "icarus.institution.memory.v1")
    memory = common.empty_memory()
    memory["events"] = {"x": {"production_authorized": True}}
    with pytest.raises(ValueError, match="authority"):
        common.validate(common.seal(memory), "icarus.institution.memory.v1")
    with pytest.raises(ValueError, match="Duplicate"):
        common.read_json(b'{"x":1,"x":2}')


def test_real_development_predictions_do_not_depend_on_reserved_tail(tmp_path, monkeypatch):
    # Real feature construction and logistic fitting. Protected holdout price
    # perturbation must not change any development prediction or screen.
    sys.path.insert(0, str(ROOT / "systems/daedalus/src"))
    from daedalus.models import default_model_specs
    from daedalus import models, validation
    monkeypatch.setattr(models, "default_model_specs", lambda: default_model_specs()[:1])
    def forbidden(*args, **kwargs):
        raise AssertionError("Protected holdout evaluated")
    monkeypatch.setattr(validation, "protected_holdout_ensemble_validate", forbidden)
    rng = np.random.default_rng(19)
    close = 100 * np.exp(np.cumsum(rng.normal(0, .002, 1800)))
    frame = pd.DataFrame({"time": np.arange(1800) * 60 + 1700000000,
                          "open": close, "high": close * 1.002, "low": close * .998, "close": close})
    path = tmp_path / "bars.csv"
    frame.to_csv(path, index=False)
    before = driver.research(path, ROOT)
    frame.loc[1550:, ["open", "high", "low", "close"]] *= 20
    frame.to_csv(path, index=False)
    after = driver.research(path, ROOT)
    assert before["models"] == after["models"]
    assert [h["screen"] for h in before["hypotheses"]] == [h["screen"] for h in after["hypotheses"]]
    assert before["development_last_source_position"] < before["protected_first_source_position"]
    assert before["protected_holdout_touched"] is False


def test_cross_market_refuses_to_aggregate_duplicate_timestamps(tmp_path):
    close = 100 + np.sin(np.arange(1800) / 20)
    timestamps = np.arange(1800) * 60 + 1700000000
    timestamps[500] = timestamps[499]
    frame = pd.DataFrame({"time": timestamps, "open": close,
                          "high": close + .1, "low": close - .1, "close": close})
    path = tmp_path / "repeated.csv"
    frame.to_csv(path, index=False)
    evidence = driver.cross_market(path, path, ROOT)
    assert evidence["state"] == "unavailable"
    assert "unique timestamps" in evidence["reason"]
    assert evidence["protected_holdout_touched"] is False


def test_memory_transition_cannot_erase_a_failure(tmp_path, monkeypatch, action_env):
    run = cycle(tmp_path, monkeypatch)
    memory = common.read_json((tmp_path / "memory.json").read_bytes())
    publish.validate_transition(common.empty_memory(), memory, run)
    erased = copy.deepcopy(memory)
    erased["experiments"] = {}
    erased = common.seal(erased)
    run = common.seal({**run, "memory_hash": erased["content_hash"]})
    with pytest.raises(ValueError, match="missing"):
        publish.validate_transition(common.empty_memory(), erased, run)


class GitAPI:
    def __init__(self, identity):
        self.repository = identity["repository"]
        self.identity = identity
        self.head = None
        self.blobs, self.commits, self.trees = {}, {}, {}
        self.mutations = []

    def call(self, method, path, body=None, allow_missing=False):
        if method == "GET" and path.startswith("/actions/runs/"):
            i = self.identity
            return {"id": i["run_id"], "run_attempt": i["run_attempt"], "head_sha": i["commit"],
                    "head_branch": "main", "event": i["event"], "html_url": i["run_url"],
                    "repository": {"full_name": self.repository}}
        if method == "GET" and path.startswith("/git/ref/"):
            return {"object": {"sha": self.head}} if self.head else None
        if method == "GET" and path.startswith("/git/commits/"):
            return self.commits[path.rsplit("/", 1)[1]]
        if method == "GET" and path.startswith("/git/trees/"):
            key = path.rsplit("/", 1)[1].split("?")[0]
            items = [{**i, "size": len(self.blobs[i["sha"]])} for i in self.trees[key]["tree"]]
            return {"truncated": False, "tree": items}
        if method == "GET" and path.startswith("/git/blobs/"):
            import base64
            raw = self.blobs[path.rsplit("/", 1)[1]]
            return {"encoding": "base64", "content": base64.b64encode(raw).decode()}
        self.mutations.append((method, path, body))
        key = hashlib.sha1(common.canonical(body)).hexdigest()
        if path == "/git/blobs":
            import base64
            self.blobs[key] = base64.b64decode(body["content"])
        elif path == "/git/trees":
            self.trees[key] = body
        elif path == "/git/commits":
            self.commits[key] = {"tree": {"sha": body["tree"]}}
        elif path.startswith("/git/refs"):
            assert body.get("force", False) is False
            self.head = body["sha"]
        else:
            raise AssertionError((method, path))
        return {"sha": key}


def test_publisher_preserves_memory_on_lost_artifact_and_is_idempotent(tmp_path, monkeypatch, action_env):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    cycle(input_dir, monkeypatch)
    client = GitAPI(action_env)
    publish.publish(client, action_env, input_dir, tmp_path / "published")
    _, _, before, _ = publish.read_history(client)
    count = len(client.mutations)
    assert publish.publish(client, action_env, input_dir, tmp_path / "retry")["already_published"]
    assert len(client.mutations) == count
    new = {**action_env, "run_id": 101, "run_url": action_env["run_url"].replace("100", "101")}
    client.identity = new
    missing = tmp_path / "missing"
    missing.mkdir()
    publish.publish(client, new, missing, tmp_path / "recovered")
    _, _, after, latest = publish.read_history(client)
    assert before == after
    assert latest["state"] == "incomplete"
    assert latest["reasons"] == ["collection_artifact_missing"]


def test_publisher_rejects_untrusted_run_before_writing(tmp_path, monkeypatch, action_env):
    cycle(tmp_path, monkeypatch)
    run = common.read_json((tmp_path / "run.json").read_bytes())
    run["ref"] = "refs/heads/evil"
    common.write_json(tmp_path / "run.json", common.seal(run))
    client = GitAPI(action_env)
    with pytest.raises(ValueError, match="identity"):
        publish.publish(client, action_env, tmp_path, tmp_path / "published")
    assert client.mutations == []


def test_report_escapes_source_html_and_exposes_real_graph(tmp_path, monkeypatch, action_env):
    cycle(tmp_path, monkeypatch)
    memory = common.read_json((tmp_path / "memory.json").read_bytes())
    next(iter(memory["experiments"].values()))["source"]["label"] = '</script><script>alert(1)</script>'
    common.write_json(tmp_path / "memory.json", common.seal(memory))
    report.build(tmp_path, ROOT)
    html = (tmp_path / "index.html").read_text()
    assert '</script><script>alert(1)</script>' not in html
    graph = common.read_json((tmp_path / "graph.json").read_bytes())
    assert len(graph["nodes"]) == 3
    assert graph["edges"][0]["relation"] == "tested_on_development_only"
