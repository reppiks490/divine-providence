"""Read-only collector, bounded experiments and context-bound durable memory."""
from __future__ import annotations

import argparse
import copy
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from urllib.error import HTTPError

from . import common, sources


def identity():
    return {"repository": os.getenv("GITHUB_REPOSITORY", common.REPOSITORY),
            "commit": os.getenv("GITHUB_SHA") or subprocess.run(
                ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
            "ref": os.getenv("GITHUB_REF", "local"), "event": os.getenv("GITHUB_EVENT_NAME", "local"),
            "run_id": int(os.getenv("GITHUB_RUN_ID", "0")), "run_attempt": int(os.getenv("GITHUB_RUN_ATTEMPT", "1"))}


def load_memory(fetcher=sources.fetch):
    url = f"https://api.github.com/repos/{common.REPOSITORY}/git/ref/heads/{common.BRANCH}"
    try:
        ref = common.read_json(fetcher(url, common.MAX_JSON))
    except HTTPError as exc:
        if exc.code == 404:
            return common.empty_memory(), None
        raise
    import re
    sha = ref.get("object", {}).get("sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid memory branch identity")
    raw = fetcher(f"https://raw.githubusercontent.com/{common.REPOSITORY}/{sha}/memory.json", common.MAX_JSON)
    return common.validate(common.read_json(raw), "icarus.institution.memory.v1"), sha


def eligible(source, memory, context_hash):
    key = common.experiment_id(source["sha256"], context_hash)
    prior = memory["experiments"].get(key)
    return prior is None or (prior["outcome"] == "interrupted" and prior["attempts"] < 3)


def merge_events(memory, events):
    for event in events:
        # Preserve the earliest actual observation across daily re-fetches.
        memory["events"].setdefault(event["id"], event)
    memory["events"] = dict(sorted(memory["events"].items(),
                                   key=lambda pair: pair[1]["first_observed_at"])[-common.MAX_EVENTS:])


def worker(source, root, output, timeout, *, peer=None):
    with tempfile.TemporaryDirectory(prefix="icarus-research-") as temp:
        temp = Path(temp)
        csv, result = temp / "source.csv", temp / "result.json"
        sources.materialize(source, csv)
        command = [sys.executable, "-m", "scripts.institution.driver", "--source", str(csv),
                   "--root", str(root), "--output", str(result)]
        if peer:
            peer_csv = temp / "peer.csv"
            sources.materialize(peer, peer_csv)
            command += ["--peer", str(peer_csv)]
        env = {**os.environ, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "MKL_NUM_THREADS": "2"}
        # Worker gets no credentials even if the runner has read credentials.
        for key in list(env):
            if "TOKEN" in key or "SECRET" in key or key.startswith("GIT_CONFIG_"):
                env.pop(key)
        with (temp / "stderr").open("wb") as error:
            process = subprocess.Popen(command,
                cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=error, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return {**common.AUTHORITY, "outcome": "interrupted", "reasons": ["scientific_worker_timeout"],
                        "models": [], "hypotheses": [], "champion": None}
        if code != 0:
            diagnostic = (temp / "stderr").read_bytes()[-4000:].decode("utf-8", "replace")
            return {**common.AUTHORITY, "outcome": "interrupted", "reasons": ["scientific_worker_failed"],
                    "diagnostic": diagnostic, "models": [], "hypotheses": [], "champion": None}
        data = common.read_json(result.read_bytes())
        if any(data.get(k) is not v for k, v in common.AUTHORITY.items()):
            raise ValueError("Worker authority mismatch")
        return data


def remember(memory, experiment, context_hash, run):
    key = experiment["id"]
    old = memory["experiments"].get(key)
    attempts = old["attempts"] + 1 if old else 1
    if len(memory["experiments"]) >= common.MAX_EXPERIMENTS and old is None:
        raise ValueError("Memory capacity reached; refusing to forget scientific failures")
    models = [{"model": m["model_name"], "metrics": m["aggregate"],
               "folds": len(m["folds"]), "fold_pass_rate": m["fold_pass_rate"]} for m in experiment["models"]]
    hypotheses = experiment["hypotheses"][:1]
    memory["experiments"][key] = {"id": key, "source": experiment["source"], "context_hash": context_hash,
        "outcome": experiment["outcome"], "reasons": experiment["reasons"], "attempts": attempts,
        "champion": experiment["champion"], "models": models, "hypotheses": hypotheses,
        "observed_at": common.now(), "run_id": run["run_id"], "run_attempt": run["run_attempt"],
        "commit": run["commit"], **common.AUTHORITY}


def initial(output):
    output.mkdir(parents=True, exist_ok=True)
    # Each attempt starts fresh. A prior local invocation or interrupted job
    # cannot donate a stale memory file to the new receipt.
    for name in ("memory.json", "graph.json", "hypotheses.json", "leaderboard.json", "datasets.json", "view.json", "index.html", "brief.md"):
        path = output / name
        if path.exists() or path.is_symlink():
            path.unlink()
    run = {"schema": "icarus.institution.run.v1", **identity(), **common.AUTHORITY,
           "started_at": common.now(), "finished_at": None, "state": "incomplete",
           "reasons": ["collection_not_completed"], "memory_parent": None,
           "memory_parent_hash": None, "memory_hash": None, "context": None,
           "source_receipts": [], "feed_receipts": [], "catalogue": [], "experiments": [], "cross_market": [], "queue": None}
    common.write_json(output / "run.json", common.seal(run))
    return run


def collect(roots, output, root, *, memory_loader=load_memory, researcher=worker, feeds=sources.announcements):
    run = initial(output)
    try:
        memory, parent = memory_loader()
        common.validate(memory, "icarus.institution.memory.v1")
        run.update(memory_parent=parent, memory_parent_hash=memory["content_hash"] if parent else None)
        memory = copy.deepcopy(memory)
        ctx = common.context(root)
        run["context"] = ctx
        inventory, receipts = sources.catalogue(roots)
        run["catalogue"] = [{k: v for k, v in s.items() if not k.startswith("_")} for s in inventory]
        run["source_receipts"] = receipts
        events, run["feed_receipts"] = feeds()
        merge_events(memory, events)
        queue = [s for s in inventory if eligible(s, memory, ctx["context_hash"])]
        run["queue"] = {"sources": len(inventory), "pending_before": len(queue), "tested": 0,
                        "already_remembered": len(inventory) - len(queue), "budget": common.PROTOCOL["budget_per_run"]}
        for source in queue[:common.PROTOCOL["budget_per_run"]]:
            result = researcher(source, root, output, common.PROTOCOL["timeout_seconds_per_source"])
            experiment = {**result, "id": common.experiment_id(source["sha256"], ctx["context_hash"]),
                          "source": {k: v for k, v in source.items() if not k.startswith("_")}}
            run["experiments"].append(experiment)
            remember(memory, experiment, ctx["context_hash"], run)
            run["queue"]["tested"] += 1
            print(f"Research {run['queue']['tested']}: {source['label']} -> {result['outcome']}", flush=True)
        if len(queue[:common.PROTOCOL["budget_per_run"]]) == 2:
            left, right = queue[:2]
            paired = researcher(left, root, output, 60, peer=right)
            pair = {**paired, "left": left["sha256"], "right": right["sha256"],
                    "context_hash": ctx["context_hash"]}
            pair["id"] = common.digest({k: pair[k] for k in ("left", "right", "context_hash")})
            run["cross_market"] = [pair]
            if len(memory["connections"]) >= 2048 and pair["id"] not in memory["connections"]:
                raise ValueError("Cross-market memory capacity reached")
            memory["connections"][pair["id"]] = pair
        run["queue"]["pending_after"] = sum(eligible(s, memory, ctx["context_hash"]) for s in inventory)
        run["state"] = "complete"
        run["reasons"] = []
        if not inventory:
            run["state"] = "incomplete"
            run["reasons"].append("no_usable_corpus_sources")
        if any(e["outcome"] == "interrupted" for e in run["experiments"]):
            run["state"] = "incomplete"
            run["reasons"].append("scientific_worker_interrupted")
        if any(c.get("outcome") == "interrupted" for c in run["cross_market"]):
            run["state"] = "incomplete"
            run["reasons"].append("cross_market_worker_interrupted")
        if any(f["state"] != "observed" for f in run["feed_receipts"]):
            run["state"] = "incomplete"
            run["reasons"].append("official_feed_unavailable")
        memory["updated_at"] = common.now()
        memory["last_run"] = {k: run[k] for k in ("run_id", "run_attempt", "commit")}
        memory = common.seal(memory)
        common.validate(memory, "icarus.institution.memory.v1")
        common.write_json(output / "memory.json", memory)
        run["memory_hash"] = memory["content_hash"]
    except Exception as exc:
        run["state"] = "incomplete"
        run["reasons"] = ["collection_failed:" + type(exc).__name__]
        print("Collection incomplete: " + type(exc).__name__, flush=True)
    run["finished_at"] = common.now()
    run = common.seal(run)
    common.write_json(output / "run.json", run)
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("_institution"))
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.initialize:
        initial(args.output)
    elif args.finalize:
        run = common.validate(common.read_json((args.output / "run.json").read_bytes()), "icarus.institution.run.v1")
        if run["finished_at"] is None:
            run["finished_at"] = common.now()
            common.write_json(args.output / "run.json", common.seal(run))
    else:
        collect(args.source_root, args.output, Path.cwd())


if __name__ == "__main__":
    main()
