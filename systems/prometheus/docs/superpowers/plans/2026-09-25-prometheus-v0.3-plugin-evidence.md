# PROMETHEUS v0.3 Plugin Evidence and DAEDALUS Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn each selected host-plugin execution into immutable, version-bound research evidence, measure its attributable contribution without collapsing evidence into one scalar score, and emit a research-only `READY_FOR_DAEDALUS_REVIEW` handoff only when the PROMETHEUS run is complete and the candidate survives engineering guardrails.

**Architecture:** Keep host plugin execution outside the Python package; PROMETHEUS receives only host execution records and turns them into content-addressed evidence artifacts bound to the selected `PluginDescriptor.descriptor_id`. A contribution evaluator records unique/shared/no-attribution/failure dimensions for every selected plugin. The existing SENTINEL/FORGE result path remains authoritative for research evaluation; a thin promotion-packet builder may package a successful candidate for DAEDALUS review but can never represent DAEDALUS acceptance or production authorization.

**Tech Stack:** Python 3.11+, standard library only in production code, pytest, existing append-only `ResearchMemory`.

**Spec:** `docs/superpowers/specs/2026-09-24-prometheus-autonomous-systems-evolution-design.md`

## Global Constraints

- PROMETHEUS is research-only. It has zero broker, order, deployment, or production-authorization authority.
- Deep Research remains mandatory for a top-level research run when available; every other materially beneficial, policy-eligible selected plugin must have one host execution record.
- Plugin execution remains a host responsibility. The local package must not gain credential, OAuth, network, browser, shell-plugin, or app-install authority.
- Every normalized plugin evidence artifact must bind the exact `PluginDescriptor.descriptor_id`, input fingerprint, execution status, and output fingerprint or external result reference.
- Failed plugin attempts remain first-class evidence with an explicit failure class; they are never silently dropped.
- Plugin contribution evaluation is multi-dimensional. Do not create a single “truth score” or use contribution counts as proof of research quality.
- A plugin may have zero attributable local artifact IDs and still have completed successfully; record `NO_ATTRIBUTED_ARTIFACTS` rather than inventing value.
- A candidate can be packaged only as `READY_FOR_DAEDALUS_REVIEW`; PROMETHEUS must never emit `DAEDALUS_ACCEPTED` or any equivalent state.
- A degraded run cannot produce a DAEDALUS-review handoff even if the local candidate otherwise passes.
- NEXUS/AION/ARGUS/ATHENA/DAEDALUS authority boundaries and v0.2 sibling-contract invariants remain unchanged.
- All new research artifacts are deterministic/content-addressed and append-only in `ResearchMemory`.

## Review Focus

- A selected plugin result is recorded for the wrong descriptor/version: reject normalization instead of attaching it to the current plugin.
- A completed host result lacks both output fingerprint and external result reference: fail closed, preserving the existing invariant.
- Two plugins claim the same contributed artifact ID: classify it as shared contribution for both, not unique contribution for either.
- A successful candidate comes from `DEGRADED_RESEARCH`: do not emit a DAEDALUS handoff.
- A promotion packet attempts to carry production authorization or a DAEDALUS acceptance state: construction must reject it or make it structurally impossible.

---

### Task 1: Normalize selected plugin executions into immutable research evidence

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Modify: `src/prometheus_loop/plugins.py`
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Create: `tests/test_plugin_evidence.py`
- Modify: `tests/test_loop.py`

**Interfaces:**
- Consumes: `PluginDescriptor`, `PluginUseRecord`, `PluginAudit`, host plugin results.
- Produces: `PluginExecutionEvidence` and `normalize_plugin_evidence(audit, inventory) -> tuple[PluginExecutionEvidence, ...]`.

- [ ] **Step 1: Write failing tests** asserting one evidence artifact per selected plugin, descriptor-id binding, deterministic artifact IDs, completed/failed field preservation, and rejection when audit/plugin inventory identities do not line up.
- [ ] **Step 2: Run `PYTHONPATH=src pytest tests/test_plugin_evidence.py -q` and verify RED because the evidence type/normalizer does not exist.**
- [ ] **Step 3: Implement the frozen evidence contract and pure normalizer.** Successful evidence must preserve output fingerprint/external ref; failed evidence must preserve `failure_class`; no raw plugin response body or credentials are stored.
- [ ] **Step 4: Integrate evidence into `PrometheusLoop.run`, append each artifact to `ResearchMemory`, and expose `plugin_evidence_ids` on `LoopRunResult`.**
- [ ] **Step 5: Run `PYTHONPATH=src pytest tests/test_plugin_evidence.py tests/test_loop.py -q` and full `PYTHONPATH=src pytest -q`. Commit `feat: persist plugin execution evidence`.**

### Task 2: Evaluate attributable plugin contribution without a scalar truth score

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Create: `src/prometheus_loop/forge/plugin_contribution.py`
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Create: `tests/test_plugin_contribution.py`

**Interfaces:**
- Consumes: normalized `PluginExecutionEvidence` artifacts.
- Produces: `PluginContributionOutcome`, `PluginContributionReport`, and `evaluate_plugin_contributions(evidence) -> tuple[PluginContributionReport, ...]`.

- [ ] **Step 1: Write failing tests** for unique contribution, shared contribution, no-attributed-artifacts, and failed execution outcomes. Assert deterministic ordering independent of input order.
- [ ] **Step 2: Run `PYTHONPATH=src pytest tests/test_plugin_contribution.py -q` and verify RED.**
- [ ] **Step 3: Implement multi-dimensional contribution classification.** A report records unique artifact IDs and shared artifact IDs; it does not rank plugins or infer research correctness from counts.
- [ ] **Step 4: Integrate reports into the loop, append them to memory, and expose `plugin_contribution_ids` on `LoopRunResult`.**
- [ ] **Step 5: Run focused tests and full suite. Commit `feat: evaluate plugin research contribution`.**

### Task 3: Emit a research-only DAEDALUS review packet

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Create: `src/prometheus_loop/policy/promotion.py`
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Create: `tests/test_promotion_packet.py`
- Modify: `tests/test_loop.py`

**Interfaces:**
- Consumes: final `RunStatus`, `CandidateImprovement | RejectedHypothesis`, plugin evidence IDs, contribution report IDs, and existing replay/adversarial evidence IDs.
- Produces: `ResearchPromotionPacket` and `build_research_promotion_packet(...) -> ResearchPromotionPacket | None`.

- [ ] **Step 1: Write failing tests** proving a complete engineering-pass run emits `READY_FOR_DAEDALUS_REVIEW`, while degraded runs and rejected hypotheses emit no packet.
- [ ] **Step 2: Add a failing authority test** proving the packet is structurally research-only (`production_authorized` fixed false) and has no DAEDALUS-accepted state.
- [ ] **Step 3: Implement the frozen packet and builder.** Evidence IDs must include the candidate result plus plugin evidence/contribution artifacts; the packet target is `DAEDALUS` and status is exactly `READY_FOR_DAEDALUS_REVIEW`.
- [ ] **Step 4: Integrate packet creation after FORGE evaluation, persist it when present, and expose it on `LoopRunResult`.** Negative-result reuse may return no new packet unless the reused artifact itself is an engineering-pass candidate (currently negative reuse is rejected, so packet remains absent).
- [ ] **Step 5: Run focused tests and full suite. Commit `feat: package candidates for daedalus review`.**

### Task 4: Documentation, provenance, validation and handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture/plugin-orchestration.md`
- Create: `docs/architecture/plugin-evidence-and-promotion.md`
- Create: `docs/adr/0003-plugin-evidence-before-promotion.md`
- Create: `docs/changes/2026-09-25-prometheus-v0.3-plugin-evidence.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `CODEX.md`
- Modify: `docs/VALIDATION_STATUS.md`

**Interfaces:**
- Consumes: final implemented v0.3 behavior.
- Produces: current-state documentation, preserved authority rules, exact verification evidence, and staleness conditions.

- [ ] **Step 1: Document why plugin execution evidence is hashed/normalized and why raw responses/credentials remain outside PROMETHEUS.**
- [ ] **Step 2: Document contribution semantics and when NOT to interpret counts as quality/ranking.**
- [ ] **Step 3: Document the DAEDALUS review packet boundary and explicit absence of production authority.**
- [ ] **Step 4: Update routers and validation status; run the final gate below and record exact results.**
- [ ] **Step 5: Commit `docs: finalize prometheus v0.3 plugin evidence`.**

## Execution assumptions

- Host-level plugin tools are invoked by ChatGPT/the orchestration host, not by local PROMETHEUS Python code.
- Deep Research results may be referenced by an external result identifier and/or output fingerprint; raw report bodies need not be copied into PROMETHEUS memory to prove a call occurred.
- `contributed_artifact_ids` are explicit attribution claims supplied by the host. PROMETHEUS may classify overlap but does not pretend those claims establish causal usefulness.
- Existing v0.2 NEXUS fixture binding remains the current sibling integration baseline for this slice.

## Knowledge delta by path

- Plan: `docs/superpowers/plans/2026-09-25-prometheus-v0.3-plugin-evidence.md`.
- Architecture: `docs/architecture/plugin-evidence-and-promotion.md` plus update to `docs/architecture/plugin-orchestration.md`.
- ADR: `docs/adr/0003-plugin-evidence-before-promotion.md`.
- Change record: `docs/changes/2026-09-25-prometheus-v0.3-plugin-evidence.md`.
- Routers: `AGENTS.md`, `CLAUDE.md`, `CODEX.md`.
- Validation: `docs/VALIDATION_STATUS.md`.
- Rules/skills: no new standalone rule or repository skill; existing research-only authority and host-plugin boundaries are strengthened in code and routers.
- Business/product/ops: unchanged; no user-facing trading behavior, deployment, broker, or production workflow is added.

## Final gate

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m prometheus_loop.cli demo --memory /tmp/prometheus-v03-demo.jsonl
! grep -R "production_authorized *= *True\|production_authorized=true\|DAEDALUS_ACCEPTED" -n src tests
! grep -R "oauth\|api_key\|credential\|place_order\|broker_order\|interactivebrokers\|ib_insync" -n src
! grep -R "sys.path.*nexus\|import nexus\|from nexus" -n src
! find . -path '*/__pycache__/*' -o -name '*.pyc' | grep -q .
git diff --check
```

The branch is acceptable only if every command exits 0, every selected plugin has immutable execution evidence, contribution reports preserve uncertainty rather than ranking plugins, degraded runs cannot generate DAEDALUS-review handoffs, and no production or credential-handling authority enters the package.
