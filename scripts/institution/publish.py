"""Trusted-main data publisher; memory is never checked out or executed."""
from __future__ import annotations

import argparse
import base64
import copy
import os
from pathlib import Path
import re

from scripts.observatory.publish import GitHubClient, _identity, _verify_api_identity
from . import common, collect, report

FILES = {"latest.json", "last_complete.json", "memory.json", "graph.json", "hypotheses.json",
         "leaderboard.json", "datasets.json", "brief.md", "index.html", "view.json"}
RUN_PATH = re.compile(r"runs/([1-9][0-9]*)-([1-9][0-9]*)\.json\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
RETENTION = 90


def read_history(client):
    ref = client.call("GET", f"/git/ref/heads/{common.BRANCH}", allow_missing=True)
    if ref is None:
        return None, {}, common.empty_memory(), None
    head = ref.get("object", {}).get("sha", "")
    if not SHA.fullmatch(head):
        raise ValueError("Invalid research history reference")
    commit = client.call("GET", f"/git/commits/{head}")
    tree = client.call("GET", f"/git/trees/{commit['tree']['sha']}?recursive=1")
    if tree.get("truncated") is not False or len(tree.get("tree", [])) > RETENTION + len(FILES) + 1:
        raise ValueError("Invalid research history tree")
    entries = {}
    for item in tree["tree"]:
        path = item["path"]
        if path == "runs" and item["type"] == "tree" and item["mode"] == "040000":
            continue
        if path not in FILES and not RUN_PATH.fullmatch(path):
            raise ValueError("Research history contains an unapproved path")
        if item["type"] != "blob" or item["mode"] != "100644" or not SHA.fullmatch(item["sha"]) or item["size"] > common.MAX_JSON:
            raise ValueError("Invalid research history blob")
        entries[path] = item
    if not {"memory.json", "latest.json"}.issubset(entries):
        raise ValueError("Research memory is missing")
    def load(name, schema):
        raw = client.call("GET", f"/git/blobs/{entries[name]['sha']}")
        if raw.get("encoding") != "base64":
            raise ValueError("Invalid research blob encoding")
        content = base64.b64decode("".join(raw["content"].splitlines()), validate=True)
        if len(content) != entries[name]["size"]:
            raise ValueError("Research blob size mismatch")
        return common.validate(common.read_json(content), schema)
    memory = load("memory.json", "icarus.institution.memory.v1")
    latest = load("latest.json", "icarus.institution.run.v1")
    if latest["repository"] != client.repository or latest["memory_hash"] != memory["content_hash"]:
        raise ValueError("History identity or memory binding mismatch")
    return head, entries, memory, latest


def validate_run(run, identity):
    common.validate(run, "icarus.institution.run.v1")
    if any(run.get(k) != v or type(run.get(k)) is not type(v) for k, v in identity.items() if k != "run_url"):
        raise ValueError("Research artifact Actions identity mismatch")
    if run["state"] not in {"complete", "incomplete"} or not isinstance(run["experiments"], list) or len(run["experiments"]) > 2:
        raise ValueError("Invalid research run state or budget")
    if run["context"] is not None:
        ctx = run["context"]
        if ctx["context_hash"] != common.digest({k: v for k, v in ctx.items() if k != "context_hash"}) or ctx["protocol"] != common.PROTOCOL:
            raise ValueError("Invalid research protocol binding")
        for experiment in run["experiments"]:
            if experiment["id"] != common.experiment_id(experiment["source"]["sha256"], ctx["context_hash"]):
                raise ValueError("Experiment identity mismatch")
    elif run["experiments"]:
        raise ValueError("Experiments lack a context")
    if run["state"] == "complete" and (not run["context"] or not run["memory_hash"] or run["reasons"]):
        raise ValueError("Complete research lacks evidence")
    return run


def validate_transition(prior, current, run):
    common.validate(current, "icarus.institution.memory.v1")
    expected = copy.deepcopy(prior)
    ctx = run["context"]
    for experiment in run["experiments"]:
        if not collect.eligible(experiment["source"], prior, ctx["context_hash"]):
            raise ValueError("Research repeats an already resolved context")
        record = current["experiments"].get(experiment["id"])
        if record is None:
            raise ValueError("Experiment missing from durable memory")
        collect.remember(expected, experiment, ctx["context_hash"], run)
        # Wall-clock observation is data, not a freshly generated publisher time.
        expected["experiments"][experiment["id"]]["observed_at"] = record["observed_at"]
    if expected["experiments"] != current["experiments"]:
        raise ValueError("Durable memory transition changed unrelated evidence")
    for pair in run.get("cross_market", []):
        if pair["id"] != common.digest({k: pair[k] for k in ("left", "right", "context_hash")}):
            raise ValueError("Cross-market identity mismatch")
        expected["connections"][pair["id"]] = pair
    if expected["connections"] != current["connections"]:
        raise ValueError("Cross-market memory changed unrelated evidence")
    for key in prior["events"].keys() & current["events"].keys():
        if prior["events"][key] != current["events"][key]:
            raise ValueError("An announcement's first observation or content was rewritten")
    if run["memory_hash"] != current["content_hash"]:
        raise ValueError("Current run does not bind the durable memory")


def publish(client, identity, input_dir, output):
    _verify_api_identity(client, identity)
    head, entries, prior, previous = read_history(client)
    path = input_dir / "run.json"
    if path.exists():
        if path.is_symlink() or path.stat().st_size > common.MAX_JSON:
            raise ValueError("Research input may not be a symbolic link")
        run = validate_run(common.read_json(path.read_bytes()), identity)
    else:
        run = collect.initial(output)
        run.update({k: v for k, v in identity.items() if k != "run_url"})
        run["finished_at"] = common.now()
        run["reasons"] = ["collection_artifact_missing"]
        run = common.seal(run)
    order = (identity["run_id"], identity["run_attempt"])
    if previous:
        prev_order = (previous["run_id"], previous["run_attempt"])
        if order < prev_order:
            raise ValueError("Refusing to publish an older research run")
        if order == prev_order:
            # A trusted writer retry is idempotent, not a second memory transition.
            return {"state": previous["state"], "already_published": True, "head": head}
    memory_path = input_dir / "memory.json"
    if memory_path.exists() and run["memory_hash"]:
        if memory_path.is_symlink() or memory_path.stat().st_size > common.MAX_JSON:
            raise ValueError("Research memory may not be a symbolic link")
        if run["memory_parent"] != head or run["memory_parent_hash"] != (prior["content_hash"] if head else None):
            raise ValueError("Research memory parent changed; refusing lost update")
        memory = common.validate(common.read_json(memory_path.read_bytes()), "icarus.institution.memory.v1")
        validate_transition(prior, memory, run)
    else:
        if run["state"] == "complete":
            raise ValueError("Complete run lost its memory artifact")
        memory = prior
        run.update(memory_parent=head, memory_parent_hash=prior["content_hash"] if head else None,
                   memory_hash=prior["content_hash"])
        run = common.seal(run)
    output.mkdir(parents=True, exist_ok=True)
    common.write_json(output / "run.json", run)
    common.write_json(output / "memory.json", memory)
    report.build(output, Path.cwd())
    run_path = f"runs/{identity['run_id']}-{identity['run_attempt']}.json"
    payload = {"latest.json": common.canonical(run), run_path: common.canonical(run)}
    for name in FILES - {"latest.json", "last_complete.json"}:
        payload[name] = (output / name).read_bytes()
        if len(payload[name]) > common.MAX_JSON:
            raise ValueError("Published research data exceeds size limit")
    if run["state"] == "complete":
        payload["last_complete.json"] = common.canonical(run)
    retained = sorted((p for p in entries if RUN_PATH.fullmatch(p)),
                      key=lambda p: tuple(map(int, RUN_PATH.fullmatch(p).groups())))[-(RETENTION - 1):]
    tree_entries = [{"path": p, "mode": "100644", "type": "blob", "sha": entries[p]["sha"]} for p in retained]
    if "last_complete.json" in entries and "last_complete.json" not in payload:
        tree_entries.append({"path": "last_complete.json", "mode": "100644", "type": "blob", "sha": entries["last_complete.json"]["sha"]})
    for name, raw in payload.items():
        blob = client.call("POST", "/git/blobs", {"encoding": "base64", "content": base64.b64encode(raw).decode()})
        tree_entries.append({"path": name, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = client.call("POST", "/git/trees", {"tree": tree_entries})
    commit = client.call("POST", "/git/commits", {"message": f"Research cycle {identity['run_id']}-{identity['run_attempt']}: {run['state']}",
                         "tree": tree["sha"], "parents": [head] if head else []})
    # Recheck the lease before the non-force reference operation.
    ref = client.call("GET", f"/git/ref/heads/{common.BRANCH}", allow_missing=True)
    if (ref["object"]["sha"] if ref else None) != head:
        raise ValueError("Research writer lease changed")
    if head:
        client.call("PATCH", f"/git/refs/heads/{common.BRANCH}", {"sha": commit["sha"], "force": False})
    else:
        client.call("POST", "/git/refs", {"ref": "refs/heads/" + common.BRANCH, "sha": commit["sha"]})
    return {"state": run["state"], "already_published": False, "head": commit["sha"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("_institution_input"))
    parser.add_argument("--output", type=Path, default=Path("_institution_published"))
    args = parser.parse_args()
    identity = _identity(os.environ)
    client = GitHubClient(os.environ.get("GITHUB_TOKEN"), identity["repository"])
    print(publish(client, identity, args.input, args.output))


if __name__ == "__main__":
    main()
