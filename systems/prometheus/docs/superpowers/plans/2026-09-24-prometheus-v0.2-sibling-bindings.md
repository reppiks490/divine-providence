# PROMETHEUS v0.2 Sibling Bindings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind PROMETHEUS to the recovered NEXUS v0.3 same-instant sibling bundle, normalize NEXUS/ARGUS/ATHENA/DAEDALUS evidence into typed PROMETHEUS observations without inventing missing semantics, and feed those observations into the existing disagreement/research loop with contract-drift protection.

**Architecture:** Add a read-only `adapters` layer in PROMETHEUS. The NEXUS adapter validates the exact outer same-instant bundle invariants and the recovered NEXUS v0.3 contract snapshot hash, then emits immutable `ObservationEnvelope` rows only from fields that NEXUS already exposes. A small sibling projection layer preserves evidence tier, authority role, source-health/frame identity, and explicit missingness; the existing SENTINEL/FORGE loop consumes the normalized observations unchanged. No sibling repo is imported at runtime and no sibling write path is added.

**Tech Stack:** Python 3.11+, standard library only for production code, pytest for tests, static JSON fixture copied from the recovered NEXUS v0.3 handoff shape.

**Spec:** `docs/superpowers/specs/2026-09-24-prometheus-autonomous-systems-evolution-design.md`

## Global Constraints

- PROMETHEUS remains research-only and cannot create, mutate, or represent production authorization as true.
- NEXUS remains authoritative for market-data identity, causal timing, replay, frame hashes, source-health state, and same-instant sibling routing.
- The NEXUS adapter must not synthesize a common clock, availability time, microstructure truth, supervisory WorldState, or DAEDALUS promotion state.
- ARGUS `CANDLE_PROXY` remains proxy evidence and must not be relabeled authenticated trade/depth/order-flow truth.
- ATHENA payloads are advisory/supervisory evidence; PROMETHEUS may compare them but cannot override them.
- DAEDALUS payloads remain `RESEARCH_CANDIDATE_ONLY`; local PROMETHEUS results cannot fabricate DAEDALUS acceptance.
- AION is used as evidence lineage/memory context; this slice does not create a competing durable market-history store.
- Missing/unknown sibling fields fail or degrade explicitly; no adapter may guess fields absent from the authoritative recovered contract.
- The recovered NEXUS v0.3 sibling-contract drift snapshot hash `1119ef3d9b561dc89668a9768893a2b1ab09cd542ffd1d7a02dd73f5a81388a2` is the binding reference for this slice.
- Existing plugin audit rules remain unchanged: every top-level loop inventories visible plugins, invokes every materially beneficial policy-eligible plugin, and requires Deep Research when available.
- No runtime dependency on the NEXUS source tree or any sibling repository is permitted.

## Review Focus

- A bundle says `production_authorized=true`: reject immediately before producing any PROMETHEUS observation.
- The outer decision instant disagrees with ARGUS/ATHENA/DAEDALUS payload `decision_ns`: reject rather than reconcile silently.
- ARGUS evidence tier is anything other than the provided contract value: preserve the literal tier and never upgrade it; unknown/missing tier is explicit failure for ARGUS comparison.
- NEXUS contract snapshot hash differs from the pinned v0.3 hash: quarantine the adapter input as contract drift rather than trying best-effort parsing.
- A sibling omits a comparison dimension: keep the sibling observation with only supported dimensions and let disagreement detection compare only dimensions present in at least two observations.

---

### Task 1: Pin the authoritative NEXUS v0.3 binding and fixture

**Files:**
- Create: `src/prometheus_loop/adapters/__init__.py`
- Create: `src/prometheus_loop/adapters/nexus.py`
- Create: `tests/fixtures/nexus_v03_same_instant_bundle.json`
- Create: `tests/test_nexus_adapter.py`

**Interfaces:**
- Consumes: `ObservationEnvelope` and `content_id` from the v0.1 package.
- Produces: `NEXUS_V03_CONTRACT_SNAPSHOT_HASH`, `NexusBundleBinding`, `validate_nexus_bundle(payload, contract_snapshot_hash) -> NexusBundleBinding`.

- [ ] **Step 1: Write failing tests for the recovered outer bundle invariants.** Add tests that load `tests/fixtures/nexus_v03_same_instant_bundle.json` and assert validation accepts `decision_ns`, `frame_hash`, `bundle_hash`, `aion`, `argus`, `athena`, `daedalus`, and fixed `production_authorized=false`. Add separate tests for missing `frame_hash`, `production_authorized=true`, and mismatched pinned contract snapshot hash.
- [ ] **Step 2: Run `PYTHONPATH=src pytest tests/test_nexus_adapter.py -q` and verify failure because `prometheus_loop.adapters.nexus` does not exist.**
- [ ] **Step 3: Implement `NexusBundleBinding` as a frozen dataclass containing `decision_ns: int`, `frame_hash: str`, `bundle_hash: str`, `contract_snapshot_hash: str`, and the four sibling payload mappings.** Validation must require the exact pinned snapshot hash, SHA-256-shaped frame/bundle values when present in the recovered contract, mapping-shaped sibling payloads, and `production_authorized is False` both on the outer bundle and wherever the recovered payload explicitly carries that field.
- [ ] **Step 4: Run `PYTHONPATH=src pytest tests/test_nexus_adapter.py -q` and then `PYTHONPATH=src pytest -q`.**
- [ ] **Step 5: Commit `feat: bind prometheus to nexus v0.3 bundle`.**

### Task 2: Normalize NEXUS, ARGUS, ATHENA and DAEDALUS sibling evidence

**Files:**
- Modify: `src/prometheus_loop/adapters/nexus.py`
- Create: `src/prometheus_loop/adapters/siblings.py`
- Modify: `tests/test_nexus_adapter.py`
- Create: `tests/test_sibling_normalization.py`

**Interfaces:**
- Consumes: validated `NexusBundleBinding`.
- Produces: `normalize_nexus_bundle(binding) -> tuple[ObservationEnvelope, ...]` and private deterministic projection helpers for NEXUS, ARGUS, ATHENA and DAEDALUS.

- [ ] **Step 1: Write failing normalization tests.** The fixture must yield observations for `NEXUS`, `ARGUS`, `ATHENA`, and `DAEDALUS` at one decision instant; every observation must retain a deterministic source reference rooted in the NEXUS `bundle_hash`/`frame_hash`; ARGUS must retain `evidence_tier=CANDLE_PROXY`; DAEDALUS must expose only research-candidate status and never a production decision.
- [ ] **Step 2: Add failing clock-consistency tests.** Mutate ARGUS, ATHENA, and DAEDALUS `decision_ns` individually and assert normalization rejects each mismatch. Do not infer or repair time.
- [ ] **Step 3: Implement projection only from recovered fields.**
  - `NEXUS` dimensions may include contract/data plane plus factor, quality, OOD, and source-health summary fields that are already present in the same-instant bundle. Numeric values must be serialized deterministically as strings without inventing categorical meaning.
  - `ARGUS` dimensions may include its literal `evidence_tier`, `microstructure_truth`, contract/data plane, and any explicitly provided comparison dimensions. Never translate factor sign into a trade direction unless the payload itself provides a direction field.
  - `ATHENA` dimensions may include literal `purpose`, `advisory_only`, contract/data plane, and explicitly provided supervisory comparison fields. NEXUS state-input ingredients are not treated as ATHENA conclusions.
  - `DAEDALUS` dimensions may include literal `schema`, `status`, and candidate kind; `production_authorized` must remain false.
  - `availability_state` is `KNOWN` only because the bundle passed NEXUS same-instant validation and carries the authoritative decision instant; the adapter must not create per-source historical availability timestamps that are absent from the payload.
- [ ] **Step 4: Run `PYTHONPATH=src pytest tests/test_nexus_adapter.py tests/test_sibling_normalization.py -q` and full `PYTHONPATH=src pytest -q`.**
- [ ] **Step 5: Commit `feat: normalize nexus sibling evidence`.**

### Task 3: Feed authoritative sibling bundles into the existing PROMETHEUS loop

**Files:**
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Modify: `src/prometheus_loop/contracts.py`
- Create: `tests/test_sibling_loop.py`
- Modify: `tests/test_loop.py`

**Interfaces:**
- Consumes: `normalize_nexus_bundle(binding)` and existing plugin audit/SENTINEL/FORGE interfaces.
- Produces: `NexusRunInput` (or an equivalent constructor) that transforms one validated NEXUS bundle into the existing `RunInput` without duplicating orchestration logic.

- [ ] **Step 1: Write a failing end-to-end test using the pinned NEXUS fixture plus deterministic host plugin results.** Assert the loop reaches the existing research-only result path, stores the adapter-derived observations/disagreement artifacts, and retains the same plugin finalization rules.
- [ ] **Step 2: Add a failing test proving a bundle with no comparable disagreement does not fabricate one.** The loop must return/raise the existing explicit no-disagreement outcome rather than synthesize direction/regime labels from numeric factor signs.
- [ ] **Step 3: Implement a thin bundle-input constructor or overload that calls the NEXUS adapter, then delegates to the existing `PrometheusLoop.run` path.** Do not fork plugin selection, memory, hypothesis, adversarial, or replay logic.
- [ ] **Step 4: Run `PYTHONPATH=src pytest tests/test_sibling_loop.py tests/test_loop.py -q` and full `PYTHONPATH=src pytest -q`.**
- [ ] **Step 5: Commit `feat: run prometheus from nexus sibling bundle`.**

### Task 4: Contract-drift quarantine and research failure artifact

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Create: `src/prometheus_loop/sentinel/failure.py`
- Modify: `src/prometheus_loop/adapters/nexus.py`
- Create: `tests/test_contract_drift.py`

**Interfaces:**
- Consumes: NEXUS binding validation failures and the pinned snapshot hash.
- Produces: immutable `FailureCase` with fields `failure_type`, `source_system`, `expected_contract_hash`, `observed_contract_hash`, `decision_instant`, `details`, and deterministic `artifact_id`.

- [ ] **Step 1: Write a failing test where the observed contract snapshot hash differs from the pinned NEXUS v0.3 value.** Assert the result is a deterministic `FailureCase(failure_type="CONTRACT_DRIFT")` and no sibling observations are emitted.
- [ ] **Step 2: Write a failing test for a same-instant invariant violation (`decision_ns` mismatch).** Assert `FailureCase(failure_type="CAUSAL_INSTANT_MISMATCH")` and no attempt to continue through FORGE.
- [ ] **Step 3: Implement failure construction as a pure research artifact.** The adapter may expose a `try_bind_nexus_bundle(...) -> NexusBundleBinding | FailureCase` helper while strict validation continues to raise for direct callers. No failure case may contain an action that writes into NEXUS.
- [ ] **Step 4: Run `PYTHONPATH=src pytest tests/test_contract_drift.py -q` and full `PYTHONPATH=src pytest -q`.**
- [ ] **Step 5: Commit `feat: quarantine sibling contract drift`.**

### Task 5: Documentation, provenance and final gate

**Files:**
- Modify: `README.md`
- Create: `docs/architecture/sibling-bindings.md`
- Create: `docs/adr/0002-pin-nexus-v03-contract.md`
- Create: `docs/changes/2026-09-24-prometheus-v0.2-sibling-bindings.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `CODEX.md`
- Modify: `docs/VALIDATION_STATUS.md`

**Interfaces:**
- Consumes: completed adapter and loop behavior.
- Produces: one authoritative explanation of what is bound, what remains fixture-only, and exactly what event makes the binding stale.

- [ ] **Step 1: Document provenance.** Record that the binding was derived from the recovered NEXUS v0.3 handoff and its sibling-contract drift snapshot hash `1119ef3d9b561dc89668a9768893a2b1ab09cd542ffd1d7a02dd73f5a81388a2`; do not claim direct live access to AION/ARGUS/ATHENA/DAEDALUS repos in this slice.
- [ ] **Step 2: Document when not to use the binding.** Reject/refresh it when the NEXUS sibling contract snapshot changes, when NEXUS same-instant bundle fields change, or when authoritative sibling schemas are newly recovered and contradict the fixture projection.
- [ ] **Step 3: Update routers and validation status with the exact new modules/tests and preserved authority boundaries.**
- [ ] **Step 4: Run the complete verification gate below and record the exact test count and commit in `docs/VALIDATION_STATUS.md`.**
- [ ] **Step 5: Commit `docs: finalize prometheus v0.2 sibling bindings`.**

## Execution assumptions

- The recovered NEXUS package is the authoritative source for the NEXUS-facing v0.3 binding; its sibling contract drift snapshot hash is known and pinned.
- The actual current source trees for AION, ARGUS, ATHENA and DAEDALUS are not assumed to be locally available in this continuation workspace. The adapter binds the exact payloads NEXUS already emits to those siblings rather than guessing independent sibling internals.
- PROMETHEUS will not derive `direction`, `regime`, `risk`, `confidence`, or execution feasibility from generic numeric NEXUS factors unless the authoritative payload explicitly names that semantic dimension.
- This slice does not write evidence into AION or submit a real candidate into DAEDALUS; it only preserves explicit adapter boundaries so those writes can be implemented when their authoritative service contracts are available.
- Existing v0.1 plugin orchestration remains the only host-plugin path. No connector runtime is added to the Python package.

## Knowledge delta by path

- Plan: `docs/superpowers/plans/2026-09-24-prometheus-v0.2-sibling-bindings.md` — exact TDD implementation sequence.
- Architecture: `docs/architecture/sibling-bindings.md` — NEXUS v0.3 binding, projection rules, and stale conditions.
- ADR: `docs/adr/0002-pin-nexus-v03-contract.md` — why the binding pins a recovered contract hash rather than importing sibling repos.
- Change record: `docs/changes/2026-09-24-prometheus-v0.2-sibling-bindings.md` — before/change/now/verification.
- Routers: `AGENTS.md`, `CLAUDE.md`, `CODEX.md` — new adapter boundary and no-guess rule.
- Validation: `docs/VALIDATION_STATUS.md` — post-gate test/compile/architecture results.
- Rules: no new standalone rule file planned; the existing spec/routers already prohibit authority leakage and guessed sibling semantics.
- Skills: none — this adds product behavior, not a new repeated operator procedure.
- Business/product/ops docs: none — no commercial, user-facing, deployment, migration, restart, or broker behavior is introduced.

## Final gate

Run once after all tasks:

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m prometheus_loop.cli demo --memory /tmp/prometheus-v02-demo.jsonl
! grep -R "production_authorized *= *True\|production_authorized=true" -n src tests
! grep -R "ib_insync\|interactivebrokers\|broker_order\|place_order" -n src
! grep -R "sys.path.*nexus\|import nexus\|from nexus" -n src
```

The branch is acceptable only if every command exits 0, the new NEXUS fixture path produces research-only artifacts, contract drift is quarantined deterministically, and no runtime sibling-repository dependency exists.
