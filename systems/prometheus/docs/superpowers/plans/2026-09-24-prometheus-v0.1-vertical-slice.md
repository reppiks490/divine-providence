# PROMETHEUS v0.1 Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, research-only PROMETHEUS v0.1 vertical slice that performs per-run plugin selection/audit, normalizes sibling evidence, detects typed disagreement, generates constrained research hypotheses, runs deterministic adversarial/replay checks, and preserves positive/negative research memory without any production authority.

**Architecture:** A small pure-Python package uses immutable dataclasses and canonical JSON hashing for research artifacts. Plugin orchestration is represented as typed inventory/selection/use records so the ChatGPT host can record real connector usage while unit tests use deterministic fixtures. SENTINEL detects evidence/contract disagreements, FORGE creates constrained hypotheses and replay comparisons, and a local append-only JSONL store persists lineage and negative results.

**Tech Stack:** Python 3.11+, standard library only for production code, pytest for tests.

**Spec:** `docs/superpowers/specs/2026-09-24-prometheus-autonomous-systems-evolution-design.md`

## Global Constraints

- PROMETHEUS is research-only and cannot set or represent production authorization as true.
- NEXUS remains authoritative for market-data identity, causal timing, replay and source-health evidence.
- AION remains authoritative for durable sibling evidence memory; local storage is PROMETHEUS research memory only.
- DAEDALUS remains authoritative for scientific validation and production promotion.
- ARGUS true microstructure/execution-physics evidence cannot be fabricated from candle proxies.
- Every top-level run performs plugin inventory/selection and records selected and skipped candidates.
- Deep Research is required for a top-level research run when available; unavailable/failure states must be explicit.
- Plugin outputs are evidence and may not bypass authority boundaries.
- No external service is required for deterministic unit tests.

## Review Focus

- Deep Research is visible but never invoked: the containing run must not finalize as `RESEARCH_COMPLETE`.
- A plugin is skipped: its audit record must contain an explicit skip status and reason rather than disappearing from the run.
- Two sibling observations have mismatched decision instants: SENTINEL rejects the comparison instead of manufacturing alignment.
- A candidate wins a headline metric but fails a leakage or reproducibility guard: FORGE rejects it.
- An experiment has already failed with the same evidence/spec fingerprint: research memory suppresses duplicate work and returns the prior negative result.

---

### Task 1: Repository foundation and immutable artifact primitives

**Files:**
- Create: `pyproject.toml`
- Create: `src/prometheus_loop/__init__.py`
- Create: `src/prometheus_loop/ids.py`
- Create: `src/prometheus_loop/contracts.py`
- Create: `tests/test_contracts.py`

**Interfaces:**
- Consumes: no earlier task interfaces.
- Produces: `canonical_json(value) -> str`, `content_id(prefix, value) -> str`, `LoopKind`, `RunStatus`, `ObservationEnvelope`, `DisagreementCase`, `ResearchHypothesis`, `ExperimentSpec`, `ReplayResult`, `CandidateImprovement`, `RejectedHypothesis`.

- [ ] **Step 1: Write failing artifact-hashing and authority tests.** Tests create equivalent dictionaries with different key order and assert identical hashes; construct candidate artifacts and assert there is no writable `production_authorized=True` path.
- [ ] **Step 2: Run `pytest tests/test_contracts.py -q` and verify failure because the package does not exist.**
- [ ] **Step 3: Implement canonical serialization, content-derived ids, frozen dataclasses and research-only candidate status.**
- [ ] **Step 4: Run `pytest tests/test_contracts.py -q` and then `pytest -q`; both must pass.**
- [ ] **Step 5: Commit `feat: add immutable prometheus research contracts`.**

### Task 2: Plugin inventory, selection policy and per-run audit

**Files:**
- Create: `src/prometheus_loop/plugins.py`
- Create: `src/prometheus_loop/policy/plugins.py`
- Create: `tests/test_plugins.py`
- Modify: `src/prometheus_loop/contracts.py`

**Interfaces:**
- Consumes: `content_id` and `LoopKind` from Task 1.
- Produces: `PluginDescriptor`, `PluginDecisionStatus`, `PluginDecision`, `PluginUseRecord`, `PluginAudit`, `PluginSelectionPolicy.select(run_kind, objective, plugins)`, `PluginAudit.finalize(run_status)`.

- [ ] **Step 1: Write failing tests for Deep Research mandatory selection, beneficial-plugin selection, explicit skip reasons, and fail-closed finalization when Deep Research is available but not completed.**
- [ ] **Step 2: Run `pytest tests/test_plugins.py -q` and verify the expected import/behavior failures.**
- [ ] **Step 3: Implement deterministic plugin descriptors and a policy that selects all objective-matching, eligible plugins; always selects capability `deep_research` for top-level research runs when available; records all skipped candidates.**
- [ ] **Step 4: Implement `PluginAudit` transitions `SELECTED -> COMPLETED|FAILED` and finalization rules for `RESEARCH_COMPLETE` versus `DEGRADED_RESEARCH`.**
- [ ] **Step 5: Run `pytest tests/test_plugins.py -q` and full `pytest -q`.**
- [ ] **Step 6: Commit `feat: enforce per-run plugin audit`.**

### Task 3: SENTINEL same-instant validation and disagreement detection

**Files:**
- Create: `src/prometheus_loop/sentinel/__init__.py`
- Create: `src/prometheus_loop/sentinel/validate.py`
- Create: `src/prometheus_loop/sentinel/disagreement.py`
- Create: `tests/test_sentinel.py`

**Interfaces:**
- Consumes: `ObservationEnvelope`, `DisagreementCase`.
- Produces: `validate_same_instant(observations) -> None`, `detect_disagreements(observations) -> tuple[DisagreementCase, ...]`.

- [ ] **Step 1: Write failing tests for mismatched decision instants, unknown availability, identical sibling claims, and directional/confidence disagreement.**
- [ ] **Step 2: Run `pytest tests/test_sentinel.py -q` and verify failure.**
- [ ] **Step 3: Implement fail-closed instant/availability validation and deterministic typed disagreement case ids.**
- [ ] **Step 4: Run `pytest tests/test_sentinel.py -q` and full `pytest -q`.**
- [ ] **Step 5: Commit `feat: add sentinel disagreement detection`.**

### Task 4: Research memory and duplicate negative-result suppression

**Files:**
- Create: `src/prometheus_loop/memory/__init__.py`
- Create: `src/prometheus_loop/memory/store.py`
- Create: `tests/test_memory.py`

**Interfaces:**
- Consumes: any frozen artifact exposing `artifact_id` and canonical serialization.
- Produces: `ResearchMemory(path)`, `append(artifact)`, `find_by_id(artifact_id)`, `has_negative(experiment_id)`, `negative_for(experiment_id)`.

- [ ] **Step 1: Write failing tests for append/read, idempotent duplicate writes and retrieval of a prior `RejectedHypothesis`.**
- [ ] **Step 2: Run `pytest tests/test_memory.py -q` and verify failure.**
- [ ] **Step 3: Implement append-only JSONL persistence with per-line SHA-256 content fingerprint and deterministic rebuild of the in-memory index.**
- [ ] **Step 4: Run `pytest tests/test_memory.py -q` and full `pytest -q`.**
- [ ] **Step 5: Commit `feat: preserve prometheus negative research memory`.**

### Task 5: FORGE constrained hypothesis, adversarial checks and deterministic replay comparison

**Files:**
- Create: `src/prometheus_loop/forge/__init__.py`
- Create: `src/prometheus_loop/forge/hypothesis.py`
- Create: `src/prometheus_loop/forge/adversarial.py`
- Create: `src/prometheus_loop/forge/replay.py`
- Create: `tests/test_forge.py`

**Interfaces:**
- Consumes: `DisagreementCase`, `ResearchHypothesis`, `ExperimentSpec`, `ReplayResult`.
- Produces: `hypothesis_from_case(case)`, `run_adversarial(spec, baseline, candidate)`, `compare_replay(spec, baseline_metrics, candidate_metrics)`.

- [ ] **Step 1: Write failing tests for deterministic hypothesis ids, leakage rejection, reproducibility mismatch rejection, and a clean candidate that remains `PROMETHEUS_ENGINEERING_PASS` rather than production-authorized.**
- [ ] **Step 2: Run `pytest tests/test_forge.py -q` and verify failure.**
- [ ] **Step 3: Implement a closed hypothesis-family mapping from disagreement type to falsifiable claim, fixed adversarial checks (`leakage`, `ablation`, `perturbation`, `missingness`, `reproducibility`), and deterministic metric comparison.**
- [ ] **Step 4: Run `pytest tests/test_forge.py -q` and full `pytest -q`.**
- [ ] **Step 5: Commit `feat: add forge adversarial replay evaluation`.**

### Task 6: Top-level loop orchestrator and deterministic fixture vertical slice

**Files:**
- Create: `src/prometheus_loop/orchestration/__init__.py`
- Create: `src/prometheus_loop/orchestration/loop.py`
- Create: `src/prometheus_loop/fixtures.py`
- Create: `tests/test_loop.py`
- Modify: `src/prometheus_loop/__init__.py`

**Interfaces:**
- Consumes: plugin policy/audit, SENTINEL, FORGE, ResearchMemory.
- Produces: `PrometheusLoop.run(run_input) -> LoopRunResult` with research artifacts, plugin audit, status and lineage ids.

- [ ] **Step 1: Write a failing end-to-end test using deterministic NEXUS/ATHENA/ARGUS fixture observations and a plugin inventory containing Deep Research, Exa and an irrelevant Gmail-style plugin.**
- [ ] **Step 2: Verify the test fails before the orchestrator exists.**
- [ ] **Step 3: Implement the orchestrator so selected plugin records must be completed/failed by the host-facing input, disagreement is detected, duplicate negative experiments are reused, and a candidate or rejection is persisted.**
- [ ] **Step 4: Add a degraded-run test where Deep Research is unavailable and a failure test where it is available but selected yet never completed.**
- [ ] **Step 5: Run `pytest tests/test_loop.py -q` and full `pytest -q`.**
- [ ] **Step 6: Commit `feat: run prometheus v0.1 research loop`.**

### Task 7: CLI, documentation, knowledge layer and verification

**Files:**
- Create: `src/prometheus_loop/cli.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `docs/architecture/plugin-orchestration.md`
- Create: `docs/changes/2026-09-24-prometheus-v0.1.md`
- Create: `docs/adr/0001-plugin-aware-research-loop.md`
- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create: `CODEX.md`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `PrometheusLoop`.
- Produces: `prometheus-loop demo --memory PATH` command that executes only deterministic local fixtures; documentation makes clear that real ChatGPT plugin calls occur in the host and are represented by audit records in the package.

- [ ] **Step 1: Write a failing CLI test asserting JSON output contains `loop_run_id`, plugin audit, disagreement ids, research status and no production authorization field set true.**
- [ ] **Step 2: Run `pytest tests/test_cli.py -q` and verify failure.**
- [ ] **Step 3: Implement the CLI and documentation. README must explain the plugin rule, Deep Research requirement, authority boundaries, test command and demo command.**
- [ ] **Step 4: Run `python -m compileall -q src tests`, `pytest -q`, and `python -m prometheus_loop.cli demo --memory /tmp/prometheus-demo.jsonl`.**
- [ ] **Step 5: Run a repository scan confirming no production broker dependency, no sibling-repo write path and no `production_authorized=True` literal exists.**
- [ ] **Step 6: Commit `docs: finalize prometheus v0.1 vertical slice`.**

## Execution assumptions

- Real ChatGPT plugin invocation is host-side and cannot be reproduced inside offline unit tests; the package records typed host-provided plugin execution evidence instead of pretending it can call ChatGPT plugins directly.
- The current repository has no authoritative PARALLAX/ORACLE/Icarus payload schemas; v0.1 therefore uses generic `ObservationEnvelope` fixtures and does not guess those contracts.
- Standard-library-only production code is sufficient for the initial slice; adding MLflow/DVC/OPA/Vault is deferred until the minimal evidence model proves useful.
- The owner requirement for Deep Research applies to top-level loop runs, not each internal SENTINEL microcheck.

## Knowledge delta by path

- Spec: `docs/superpowers/specs/2026-09-24-prometheus-autonomous-systems-evolution-design.md` — plugin orchestration contract added.
- Plan: `docs/superpowers/plans/2026-09-24-prometheus-v0.1-vertical-slice.md` — executable TDD plan.
- Architecture: `docs/architecture/plugin-orchestration.md` — operational plugin selection/audit behavior.
- ADR: `docs/adr/0001-plugin-aware-research-loop.md` — why plugin use is host-mediated and research-only.
- Change record: `docs/changes/2026-09-24-prometheus-v0.1.md` — before/change/now/verification/staleness.
- Routers: `AGENTS.md`, `CLAUDE.md`, `CODEX.md` — same authority/plugin rules for future agents.
- Skills: none in v0.1 — no repo-local repeatable procedure is mature enough to skillify beyond existing Superpowers/Akinator/Baton Pass guidance.
- Business docs: none — no money, entitlement or commercial behavior is introduced.
- Ops docs: none beyond architecture — no deployment/migration/restart behavior exists in v0.1.

## Final gate

Run once after all tasks:

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m prometheus_loop.cli demo --memory /tmp/prometheus-demo.jsonl
! grep -R "production_authorized *= *True\|production_authorized=true" -n src tests
! grep -R "ib_insync\|interactivebrokers\|broker_order\|place_order" -n src
```

The branch is acceptable only if all commands exit 0 and the demo emits a research-only result with a complete plugin audit.
