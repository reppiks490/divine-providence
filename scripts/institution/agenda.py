"""Use ORACLE's existing scheduler to allocate the bounded corpus budget."""
from pathlib import Path
import sys
import time
from dataclasses import asdict, replace

from . import common


def select_sources(queue, memory, context_hash, root, limit):
    sys.path.insert(0, str(Path(root) / "systems/oracle/src"))
    from oracle.contracts import ResearchJob
    from oracle.hypothesis_factory import Trigger, from_anomaly
    from oracle.scheduler import ResearchScheduler, priority

    scheduler = ResearchScheduler()
    decision_ns = time.time_ns()
    by_job, groups, counts, hypotheses, feasibility = {}, {}, {}, {}, {}
    def group(source):
        return source["repository_url"] + "::" + source["archive"]
    for experiment in memory["experiments"].values():
        if experiment["context_hash"] == context_hash and experiment["outcome"] != "interrupted":
            key = group(experiment["source"])
            counts[key] = counts.get(key, 0) + 1
    for source in queue:
        experiment_id = common.experiment_id(source["sha256"], context_hash)
        job_id = "JOB-" + common.digest({"experiment": experiment_id, "decision_ns": decision_ns})[:24]
        hypothesis = from_anomaly(Trigger("untested_source_context", decision_ns, source["sha256"],
                                  0.0, 0.0, {"budget_rows": source["rows_budget_estimate"]}, (source["sha256"],)),
                                  horizon="5 source bars")
        hypothesis = replace(hypothesis, statement="Do lagged bar features in source " + source["sha256"] +
                             " predict five-bar outcomes beyond training prevalence across spread, purged development windows?")
        estimated_features = max(0, source["rows_budget_estimate"] - 55)
        reserved = min(estimated_features, max(250, min(2000, round(.2 * estimated_features))))
        estimated_development = max(0, estimated_features - reserved - 5)
        feasible = max(0, min(5, 1 + (estimated_development - 250 - 505) // 255))
        priors = common.PROTOCOL["agenda_information_priors"]
        information_prior = priors["five_estimated_folds"] if feasible == 5 else (
            priors["two_to_four"] if feasible >= 2 else priors["insufficient"])
        # These numbers are declared allocation priors, not estimated predictive
        # accuracy, empirical information gain, or confidence in an edge.
        job = ResearchJob(job_id, hypothesis.hypothesis_id, "development_coverage_tournament",
                          decision_ns, information_prior, 1, 1, 1, 1,
                          1 + source["rows_budget_estimate"] / 60000, ("DAEDALUS",))
        scheduler.submit(job)
        by_job[job_id] = source
        hypotheses[job_id] = hypothesis
        feasibility[job_id] = feasible
        groups[job_id] = group(source)
    selected = scheduler.rank(decision_ns, groups=groups, group_counts=counts, limit=limit)
    choices = []
    for job in selected:
        key = groups[job.job_id]
        choices.append({"job_id": job.job_id, "hypothesis_id": job.hypothesis_id,
                        "job_specification": asdict(job), "hypothesis": asdict(hypotheses[job.job_id]),
                        "source_sha256": by_job[job.job_id]["sha256"], "group": key,
                        "prior_group_selections": counts.get(key, 0),
                        "base_priority": priority(job), "marginal_priority": priority(job) / (1 + counts.get(key, 0)),
                        "estimated_compute_units": job.estimated_compute_cost,
                        "estimated_development_folds": feasibility[job.job_id],
                        "basis": "registered metadata cost and marginal provenance diversity; no empirical edge probability"})
        counts[key] = counts.get(key, 0) + 1
    record = {"owner": "ORACLE.ResearchScheduler", "decision_ns": decision_ns,
              "policy": "marginal_provenance_diversity.v1", "choices": choices}
    return [by_job[j.job_id] for j in selected], common.read_json(common.canonical(record))
