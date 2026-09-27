# HELIOS PRIME Handoff Package for Builders  

**Executive Summary:** This report details the complete HELIOS PRIME handoff bundle ready for repo-capable developers. It includes a prioritized checklist of required artifacts (docs, ADRs, contracts, tests, fixtures, ledgers, pinned commits), a Git branching/commit strategy with example messages, a step-by-step RED→GREEN TDD workflow by plane (H1–H6), interface mappings to sibling systems (AION, DAEDALUS, ICARUS, ARGUS, NEXUS) with schemas/fields, a recommended implementation sequence (with effort estimates and blockers), a suite of synthetic benchmark scenarios and fixtures (with tournament instructions), a security-and-firewall checklist (AST scans, keys, network restrictions, content quarantine), promotion/policy gating for advanced capabilities with objective criteria, an onboarding checklist for incoming agents (including the exact handoff message and SDD ledger format), and a deliverable manifest plus step-by-step transfer to a new GitHub repo. All internal HELIOS specifications are assumed authoritative; we reference relevant standards and best-practices to justify design choices.  

## 1. Artifacts Commit Checklist  
Ensure the following files/directories (with **exact paths**) exist and contain at least the minimal required content before any implementation:  

- **Top-level files:**  
  - `README.md` – Overview of HELIOS PRIME scope, architecture reference, and usage.  
  - `AGENTS.md` – Agent collaboration rules and onboarding instructions.  
  - `STATE.md` – Current development status (e.g. “APPROVED/FROZEN through H5; implementation not started; tests not yet executed; production NOT READY”).  
  - `HANDOFF.md` – This handoff guide’s introduction or pointer.  
  - `pyproject.toml` – Basic Python project config (with project name, version, dependencies placeholder).  

- **docs/** (documentation):  
  - `docs/SOURCE_REQUIREMENTS.md` – Summary of source data quality and standards (e.g. JSON formats, timestamps, identifiers).  
  - `docs/ARCHITECTURE.md` – System-wide architecture overview with diagrams.  
  - `docs/OWNERSHIP.md` – Module/subsystem ownership boundaries.  
  - `docs/CAPABILITY_MATRIX.md` – Table of capability tiers (FOUNDATIONAL, QUALIFIED, etc.) and gating rules.  
  - `docs/INTEGRATION_READINESS.md` – Current readiness of external adapters (AION, DAEDALUS, ICARUS, etc.) and pinned commits.  
  - `docs/RISK_LEDGER.md` – Known risks (e.g. ICARUS_RISK_001) and mitigation.  
  - `docs/UNFINISHED_MATRIX.md` – List of incomplete features or deferred design choices.  
  - `docs/TEST_EVIDENCE.md` – Log of test results, coverage, and quality measures.  
  - `docs/SECURITY.md` – Security policies (data sandboxing, secrets, code injection countermeasures).  
  - `docs/EXECUTION_FIREWALL.md` – Details of no-exec authority rule and enforcement.  
  - `docs/CAUSAL_TIME.md` – Explanation of knowledge-time ordering and event clocks.  
  - `docs/PROVENANCE.md` – Provenance DAG model (mention W3C PROV concepts).  
  - `docs/RECOVERY.md` – Restart and crash-recovery protocol.  
  - `docs/DURABILITY.md` – Persistence guarantees (e.g. SQLite WAL journaling).  

- **docs/audits/** (if available): Audit reports of related systems. For example:  
  - `docs/audits/aion-audit.md` – Summary of AION integration audit.  
  - `docs/audits/daedalus-audit.md`, `icarus-audit.md`, etc.  

- **docs/plans/** (design plans by plane):  
  - `docs/plans/H1-foundation.md` (H1 architecture details).  
  - `docs/plans/H2-belief-engine.md`.  
  - `docs/plans/H3-robust-interrogation.md`.  
  - `docs/plans/H4-source-economy.md`.  
  - `docs/plans/H5-sibling-integrations.md`.  
  - `docs/plans/H6-meta-research.md`.  

- **docs/adr/** (Architecture Decision Records): e.g.:  
  - `docs/adr/0001-authority-boundaries.md` (HELIOS vs. ICARUS vs. external).  
  - `docs/adr/0002-canonical-serialization.md` (adoption of RFC8785 JSON canonicalization【3†L67-L72】).  
  - `docs/adr/0003-knowledge-time.md` (causal timestamp model).  
  - `docs/adr/0004-evidence-independence.md` (identifying correlated sources).  
  - `docs/adr/0005-sqlite-durability.md` (SQLite WAL journal).  
  - `docs/adr/0006-audit-trust.md` (audit log strategy).  
  - `docs/adr/0007-external-effects.md` (no trade/broker actions).  
  - `docs/adr/0008-execution-firewall.md` (ICARUS no-trading integration).  
  - `docs/adr/0009-source-qualification.md` (source manifest standards).  
  - `docs/adr/0010-sibling-packet-boundary.md` (serialized contracts only).  

- **src/helios/** (source code):  
  - `src/helios/contracts/` – (module contracts, e.g. `evidence.py`, `interrogation.py`, `acquisition.py`).  
  - `src/helios/persistence/` – (SQLite-based stores, e.g. `investigation_store.py`, `source_economy_store.py`).  
  - `src/helios/provenance/` – (provenance graph code).  
  - `src/helios/audit/` – (audit logging utilities).  
  - `src/helios/tasks/` – (durable task framework).  
  - `src/helios/recovery/` – (restart checks).  
  - `src/helios/security/` – (content sandboxing, file handling, deserialization guards).  
  - `src/helios/beliefs/` – (H2 belief engine).  
  - `src/helios/interrogation/` – (H3 action planner).  
  - `src/helios/sources/` – (H4 source economy).  
  - `src/helios/integrations/` – (H5 AION/DAEDALUS/ICARUS adapters).  
  - `src/helios/services/` – (any service interface layer).  

- **tests/** (unit and integration tests): mirror `src/helios` structure under `tests/` for corresponding test files.  
  - E.g. `tests/beliefs/test_*.py`, `tests/interrogation/test_*.py`, `tests/sources/test_*.py`, `tests/integrations/test_*.py`, etc.  
  - **fixtures/**: synthetic-world generators. E.g. `tests/fixtures/belief_worlds.py`, `interrogation_worlds.py`, `source_worlds.py`, `integration_world.py`.  

- **.superpowers/sdd/** (Design/Development ledger files):  
  - `helios-h1/progress.md`, `helios-h2-belief-engine/progress.md`, etc., as sub-directories of `.superpowers/sdd/` for each workstream’s ledger (task, RED/commit evidence, rulings).  

**Minimal Content:** At minimum, each file listed should exist (with brief stub content or a heading). For example, `STATE.md` must list the current status (see above), `OWNERSHIP.md` should list "HELIOS owns: ...; HELIOS does *not* own: ...", etc.  The exact initial content can be minimal bullet points that will be expanded by developers.  

> **Citations:** Use RFC8785 for canonical JSON【3†L67-L72】 (we rely on JCS for signing JSON data), OWASP File Upload for content quarantine best-practices【16†L200-L209】, AWS guidance on idempotent APIs【21†L326-L334】【21†L394-L402】, etc.

## 2. Git Branch & Commit Strategy  
- **Repository:** Create a *new, separate* GitHub repo (e.g. `myorg/helios-prime`). Do **not** embed HELIOS within the ICARUS/AION repos.  
- **Branch:** Develop on a feature branch, *never* on `main`. We recommend a protected integration branch such as `codex/helios-prime-masterbuild`. All commits should merge into this branch.  
- **Initial Commit:** A first commit with all the stub docs/files above (`README.md`, `docs/`, `src/` with empty files, etc.) and minimal code to satisfy structure.  
- **Commit messages:** Use conventional commits. Examples:  
  - `docs: add initial architecture overview`  
  - `feat: add HELIOS hypothesis and evidence contracts`  
  - `feat: add causal source reference contract`  
  - `feat: add evidence provenance graph module`  
  - `fix: correct numbering in SDD ledger`  
  - Each commit should contain a brief summary and, if needed, a description of what tests have been run.  
- **Code Comments:** Use inline TODOs sparingly; prefer updating the docs and plans.  

> **Template Example:** For a new feature, use `feat:`. For example, when adding a new contract file:  
> ```
> git add src/helios/contracts/interrogation.py
> git commit -m "feat: add HELIOS research action contract"
> ```  
> For docs, use `docs:` prefix, etc. Always mention what was added/changed.  

## 3. RED→GREEN TDD Workflow (H1–H6)  
Each plane (H1–H6) follows strict Test-Driven Development. For each task or module:  

1. **Write a failing test (RED):** Identify a minimal behavior or contract. Add a pytest in `tests/...`. Run `pytest tests/<module>` to see it fail.  
2. **Implement the feature (GREEN):** Write just enough code in `src/helios/...` to satisfy the test. Rerun tests.  
3. **Refactor (REFACTOR):** Clean code without changing behavior.  
4. **Commit:** After GREEN, commit tests+code with a clear message.  

Important commands:  
```bash
pytest tests/<subset> -q        # run tests for a subset of modules
pytest -W error::ResourceWarning -q  # catch resource warnings 
python -m compileall -q src tests  # ensure no syntax errors
```

### H1 (Integrity Foundation)  
- **Tests:** Property-based and fixed fixtures for: canonical serialization (RFC8785 compliance), deterministic ID generation, transactional persistence, audit log invariants, crash recovery replay.  
- **RED→GREEN Criteria:** All invariants hold on restart. Audit hash chain verifies. Cannot write to disk without logging. Security policy rejects any unauthorized action.  
- **Acceptance:** `pytest tests/recovery` and `tests/firewall` must pass.  

### H2 (Belief Engine)  
- **Tests:** Falsification: feeding evidence should change beliefs as expected. Contradictions recorded. Calibration checks (prob predictions vs outcomes). Synthetic labeled worlds to check that `UNKNOWN_OR_NOVEL` triggers when no hypothesis fits.  
- **RED→GREEN Criteria:** Evidence scores remain comparative only; no hidden probabilistic normalization unless a proper model exists. Belief snapshots reproducible. Predictions follow calibration.  
- **Acceptance:** `pytest tests/beliefs` (especially test that no fake probability is silently created).

### H3 (Robust Interrogation)  
- **Tests:** See each task in plan. Examples:  
  - **H3.1 (Actions):** Invalid action types rejected, cost/latency bounds enforced, `ABSTAIN` has no target, etc. (tests/test_actions.py).  
  - **H3.2 (Feasibility):** Source readiness from H5 should gate; multiple failure reasons collected (tests/test_feasibility.py).  
  - **H3.3 (Elimination Baseline):** Check expected eliminated hypotheses is correct with probabilities (tests/test_elimination.py).  
  - **H3.4 (EIG Baseline):** On toy discrete model, EIG computed correctly; if no probabilistic model, EIG is “unavailable” (tests/test_information.py).  
  - **H3.5 (Pareto):** Actions nondominated form the frontier, tie-break deterministic (tests/test_pareto.py, test_planner.py).  
  - **H3.6 (Robust/Misinformation):** Under synthetic perturbations (stress worlds), robust EIG shows min/median gains; actions that increase confidence but worsen predictive score are flagged (tests/test_robustness.py, test_misinformation.py).  
  - **H3.7 (Stopping):** Given context, returns correct stopping reason (tests/test_stopping.py).  
  - **H3.8 (Realized Info):** Datastore records expected vs realized information and cost, calculates bias (tests/test_realized.py).  
  - **H3.9 (Sequential Planner):** Depth-2 planning yields better decisions when it unlocks future gains; respects budget and recursion limits (tests/test_sequential.py).  
  - **H3.10 (Tournament):** Run all planners (random, elimination, EIG, robust-EIG, misinformation-aware) on synthetic worlds. Check expected outcomes per world (tests/test_tournament.py) and property tests (order invariance, monotonicity, no forbidden dependencies). Include metamorphic and fault injection as property tests.  

- **Commands:** 
  - Run targeted tests per task, e.g. `pytest tests/interrogation/test_actions.py`.
  - Full suite: `pytest tests/interrogation -q`.  

- **Acceptance:** No test failures in `tests/interrogation`. All forbidden behaviors (e.g. trading actions) must be caught by tests.

### H4 (Source Economy)  
- **Tests:**  
  - **H4.1 (Capability):** Endpoint capability identity stable, unknown access ≠ available (tests/test_capability.py).  
  - **H4.2 (Probe):** Source probe records schema/semantic issues correctly; timed vs untimed payloads (tests/test_probe.py).  
  - **H4.3 (Health):** Compute availability/success rates from probes; flag insufficient history (tests/test_health.py).  
  - **H4.4 (Economics):** Cost/quality vector values bounded, non-negative (tests/test_economics.py).  
  - **H4.5 (Substitution):** Semantic compatibility graph identifies exact/degraded substitutes correctly (tests/test_substitution.py).  
  - **H4.6 (Access Policy):** Future policy changes produce warnings, not premature blocking (tests/test_access_policy.py).  
  - **H4.7 (Acquisition Router):** Given an `AcquisitionRequest`, only qualified adapters are feasible; cost/latency budgets enforced; independence requirement checked (tests/test_acquisition.py).  
  - **H4.8 (Realized Value):** Records of source performance separate from expectation; computes per-adapter profiles without pooling incompatible data (tests/test_value.py).  
  - **H4.9 (Source Pareto):** Pareto selection of sources yields nondominated set; uses defined tie-break (tests/test_tournament.py) including synthetic worlds A–J and metamorphic checks.  

- **Commands:** `pytest tests/sources -q`.  

- **Acceptance:** All tests in `tests/sources` pass; no coherence errors (e.g. using unknown rights as “free” in economics).  

### H5 (Sibling Integration Fabric)  
- **Sub-projects:** Each has its own RED→GREEN tasks:  
  - **H5-A Integration Core:** Define `IntegrationReadiness`, `SiblingPacket` contracts (tests/test_contracts.py). Enforce AST firewall (no direct `import aion` etc.) (tests/test_registry.py or dedicated test).  
  - **H5-B AION Adapter:** In AION repo, add a `helios` export view (schema `aion-evidence-v1`, production/execution flags false). In HELIOS, write packet validator (reject wrong schema, future as-of times) (tests/test_aion.py).  
  - **H5-C DAEDALUS Adapter:** Add HELIOS export (`daedalus-validation-v1`), include all needed fields (validation results, holdout stats, etc.), signed by source_commit. HELIOS validator: preserve all dimensions, do not treat “promoted=true” as grant of authority (tests/test_daedalus.py).  
  - **H5-D ICARUS Adapter:** Implement read-only HTTP client (`GET /healthz`, `/status/public`) limited to localhost; forbid any other endpoint (tests/test_read_only_http.py). Parse ICARUS status into `IcarusPublicStatus` (tests/test_icarus.py). Accept only research_candidate artifacts from ICARUS (`execution_authorized=false`) (tests/test_icarus_artifact.py). AST scan to ensure no imports of `icarus_engine` or `icarus_bridge` and no references to trading fields (tests/test_icarus_integration.py).  
  - **H5-E Drift Detection:** Compute a fingerprint of sibling contract schemas and source commits (tests/test_drift.py). Unverified commits are marked `VERIFIED_DEGRADED` until re-verified.  
  - **H5-F Evidence Envelope:** Map all sibling packets to a unified `IntegrationEvidence` object (tests verifying fields and upstream refs). Ensure AION-derived DAEDALUS results are linked in provenance (test: `test_daedalus_derived_not_independent`).  
  - **H5-G End-to-End World:** Create a fixture `integration_world.py` where AION frame → H2 → H3 → DAEDALUS validation → HELIOS, then ICARUS status. Test that this flow works, and no order execution occurs (tests/test_end_to_end.py).  
  - **H5-H Failure Worlds:** Simulate failures (AION future frame, DAEDALUS wrong identity, ICARUS offline, schema changes). Verify HELIOS recovers or fails closed as expected (same `test_end_to_end.py`).  

- **Commands:** Focused `pytest tests/integrations -q`.  

- **Acceptance:** All sibling integration tests pass. HELIOS never processes any ICARUS order or broker data (enforced by tests). No ACL violations.

### H6 (Meta-Research & Self-Audit)  
- **Tests:** (Preliminary) Tournaments comparing new methods vs baselines. Drift monitors raising alerts on synthetic shifts. Self-audit checks that no module has exceeded complexity budget.  
- **Acceptance:** This plane mainly sets up scaffolding. Proof-of-concept tests should show how a promoted method suspends if calibration degrades. All existing invariants (especially from H1–H5) must hold.

## 4. Interfaces: Planes & Siblings  
We list each relevant interface and data contract between HELIOS planes and sibling systems:

| **Interface**                    | **Producer (System)**   | **Consumer (HELIOS Plane)**            | **Schema/Packet Type**     | **Key Fields**                                          | **Validation Rules**                                          |
|-------------------------------|-----------------------|--------------------------------------|--------------------------|--------------------------------------------------------|--------------------------------------------------------------|
| **AION → HELIOS**              | AION (`aion/parallax`) | H2/H3 (Historical Evidence)           | `aion-evidence-v1`         | `asof_ns`, `frame_hash`, `source_hashes`, synthetic flag, `prices`, `flow`, `books`             | `asof_ns <= decision_ns`; `execution_authorized=false`; preserve AION EvidenceTier as label (no mapping to ARGUS levels). Missing data flagged (quality gaps).【3†L67-L72】 |
| **HELIOS → AION**              | HELIOS                | *None (no write/side-effect)*         | N/A                        | N/A                                                    | HELIOS does not send any data to AION.                         |
| **DAEDALUS → HELIOS**          | DAEDALUS (`daedalus-research`) | H2/H3 (Scientific Validation) | `daedalus-validation-v1`   | `experiment_id`, `source_sha256`, `source_identity` (symbol, chart type), `validation` (metrics, drift), `holdout` stats, `promotion.*` | All fields treated as *evidence*. `promotion.promoted=true` *does not* grant execution authority. `source_identity.execution_safe` ignored for authority. `execution_authorized=false`. Packet hash covers entire payload. |
| **HELIOS → DAEDALUS**          | HELIOS                | *None (no side-effects)*              | N/A                        | N/A                                                    | HELIOS only **requests** evaluations via DAEDALUS API; does not alter DAEDALUS registry or experiment config. |
| **ICARUS (Public) → HELIOS**   | ICARUS (`Icarus`)     | H5 (ICARUS Status Adapter)            | *None (HTTP GET)*          | JSON response from `/status/public`                    | Only allow loopback GET on `/healthz` or `/status/public`. No redirects. Map keys (e.g. `healthy`, asset lists) into `IcarusPublicStatus`. Additional fields are ignored or trigger contract drift review. |
| **HELIOS → ICARUS**            | HELIOS                | *ICARUS Advisory (future)*           | `icarus-advisory-v1` (hypothetical) | `investigation_id`, `decision_id`, evidence refs, `reason_codes`   | **CONTRACT_ONLY** (no endpoint defined). No calls are made yet. When implemented, must forbid trading fields (order, stop, secret). |
| **ARGUS → HELIOS**             | ARGUS (Market Data)   | H2/H4 (Tick-level Data)**             | (internal AR-DIF format)    | (instrument, timestamp, bid/ask)                       | ARGUS data used only for sources/evidence. HELIOS cannot push orders to ARGUS.|
| **HELIOS → ARGUS**             | HELIOS                | *Order Execution*                    | *External*                 | *N/A (not allowed)*                                    | Not permitted: HELIOS has no execution authority.             |
| **NEXUS → HELIOS**             | NEXUS (Trading Network)** | H3/H4 (Orderbook Queries)          | *undocumented**           | *N/A (we have not integrated NEXUS yet)*              | Placeholder. If used, must follow similar contract-based gating. |
| **ATHENA/ORACLE → HELIOS**     | (Supervisor/Watchdog) | H6 (Risk Alerts)                     | *None*                     | *N/A (future)*                                        | ATHENA/ORACLE are out of scope; HELIOS can listen to alerts but does not replace them. |

_*Notes:_ AION and DAEDALUS packets are strictly *read-only* imports. All schema versions and source commit SHAs must match pinned values. For example, if AION’s commit is `12a7cb8`, HELIOS validation should include `source_commit = "12a7cb8"` (see `IntegrationReadiness`). ICARUS public endpoints are accessed only by HTTP GET from localhost – no other access is allowed.  

## 5. Implementation Sequence & Effort  
We strongly recommend implementing in the H1→H2→H3→H4→H5 order (H6 last). Each plane depends on the previous. Below is a suggested task sequence with *relative effort* (Low/Med/High) and known blockers:

| **Phase/Task**                          | **Effort** | **Blockers/Risks**                       |
|-----------------------------------------|-----------|------------------------------------------|
| **H1 Foundation (Integrity)**           |           |                                          |
| 1. Core contracts & types               | Med       | Must finalize data model first (knowledge time, evidence ID format). |
| 2. Persistence layer (SQLite)           | High      | Requires careful schema design and WAL tests. |
| 3. Provenance graph module              | Med       | Complexity in ensuring referential integrity. |
| 4. Audit log (append-only)              | Med       | Blocker: need stable data model to compute hashes. |
| 5. Durable tasks/decision trace         | Med       | Integration with tasks and audit needed. |
| 6. Firewall/security (ICARUS, secrets)  | Med       | Needs config for allowlists, AST scanning code. |
| 7. Recovery (checkpoint/replay)         | High      | Must interoperate with persistence layer. |
| *Blocker:* None of H2+ can start until H1 passes full suite.  |           |                                          |
| **H2 Belief Engine**                    |           |                                          |
| 1. Hypothesis/evidence models           | Med       | Depends on H1 types. Calibration design needed. |
| 2. Evidence scoring baseline            | Med       | Define interface; must not output probabilities. |
| 3. Belief snapshot & ledger             | Med       | Tied to audit logs.                        |
| 4. Contradiction tracking               | Low       | Pure logic; few dependencies.             |
| 5. Calibration ledger                   | High      | Requires infrastructure to store/pause calibrations. |
| 6. Synthetic belief benchmarks (worlds) | Low       | Writers of synthetic scenarios (fixtures). |
| *Blocker:* Probabilistic H2-X methods require baseline H2 running and benchmarks.  |           |                                          |
| **H3 Interrogation**                    |           |                                          |
| 1. ResearchAction contract (H3.1)       | Low       | Depends on H2 output schema.              |
| 2. Feasibility gate (H3.2)             | Med       | Needs H5 readiness information (use stubs initially). |
| 3. Elimination baseline (H3.3)         | Low       | Independent of H2 if discrete model provided. |
| 4. EIG baseline (H3.4)                 | Med       | Requires H2 support model.                |
| 5. Pareto planner (H3.5)               | Med       | Builds on results of 3 and 4.            |
| 6. Robust/Misinformation (H3.6)        | High      | Requires a variety of stress scenarios and H2 calibration metrics. |
| 7. Stopping engine (H3.7)              | Low       | Logic on top of metrics.                 |
| 8. Realized info ledger (H3.8)         | Med       | Integrates with persistence.             |
| 9. Sequential planner (H3.9)           | High      | Must combine all above; careful to bound depth. |
| 10. Tournament (H3.10)                 | Med       | Writing synthetic worlds and verifying expected outcomes. |
| *Blocker:* Needs all H3 subcomponents plus basic H2 to test multi-step flows.  |           |                                          |
| **H4 Source Economy**                    |           |                                          |
| 1. Endpoint capability contract (H4.1)  | Low       | Independent.                             |
| 2. Source probe & schema check (H4.2)   | Med       | Simple parsing logic, handle errors.     |
| 3. Source health module (H4.3)         | Med       | Based on probe history; needs persistence stubs. |
| 4. Economics vector (H4.4)             | Low       | Define vector schema.                    |
| 5. Source substitution graph (H4.5)    | High      | Complex semantic compatibility logic.    |
| 6. Access policy / future credentials (H4.6) | Low  | Time-based state transitions.           |
| 7. Acquisition request & router (H4.7) | High      | Ties H3 action to actual source adapters; many conditions. |
| 8. Realized source value (H4.8)        | Med       | Similar to H3 realized info.             |
| 9. Pareto source tournament (H4.9)     | Med       | Synthetic source worlds (see below).     |
| *Blocker:* H4 needs H3 to produce `AcquisitionRequest`s, but development can proceed with mocks.  |           |                                          |
| **H5 Sibling Integration**             |           |                                          |
| A. Integration core (contracts/registry) | Low      | Just data models.                         |
| B. AION export & HELIOS adapter       | Med       | Requires AION codebase mod + HELIOS parser. |
| C. DAEDALUS export & HELIOS adapter   | Med       | Must not touch DAEDALUS registry; output parsing needed. |
| D. ICARUS firewall (HTTP client)      | Low       | Mostly network ACL config.               |
| E. ICARUS artifacts (parse candidate) | Med       | Must reject any execution_authorized=true. |
| F. AST-level safety checks            | Low       | Static analysis of imports (can be simple script/test). |
| G. Cross-system provenance (evidence envelope) | Med | Build unified `IntegrationEvidence`.   |
| H. End-to-end synthetic integration (fixtures + test) | Low | Use above pieces in sequence. |
| I. Failure scenarios (integration)    | Low       | As above, test error branches.           |
| *Blocker:* Must wait for AION/DAEDALUS release to produce the packets. Also ICARUS endpoints must be reachable on localhost.  |           |                                          |
| **H6 Meta-Research (Self-Audit)**       |           |                                          |
| (Plan development)                    | Low       | Requires core system to exist first.    |
| *Blocker:* Deferred until H1–H5 are stable.  |           |                                          |

**Prioritization:** H1–H5 tasks are strictly sequential. Within each plane, start with basic contracts and core functionality before advanced features (e.g. do H3.1–3.5 before H3.6–3.10). Early tasks generally have *Low/Med* effort; integration and robustness tasks tend to be *High*. Known blockers are noted above.  

## 6. Synthetic Benchmark Worlds & Fixtures  
Include the following test worlds/fixtures (under `tests/fixtures/`) to verify planner logic. Each world simulates a scenario with known outcomes:  

- **H2 World A (Correlated Vendors):** Two “duplicate” sources reveal same truth; belief should not double-count evidence.  
- **H2 World B (False Story Persistence):** Misleading rumor sustains belief until countered.  
- **H2 World C (Data Corruption):** Vendor shows contradictory price; HELIOS should flag semantic conflict, not accept as truth.  
- **H2 World D (Novelty):** New phenomenon appears; no hypothesis fits, raising high `UNKNOWN` vector.  
- **H2 World E (Future Revision):** Historical price is later updated; HELIOS must respect revision logic and not consider original false after correction.  
- **H2 World F (Synthetic Provenance):** Simulate a provenance chain and verify independence analysis.  

- **H3 World 1 (Cheap Discriminator):** One low-cost action separates hypotheses definitively (expected: all planners choose it).  
- **H3 World 2 (Correlated Evidence Trap):** Two actions query nearly identical info (shared upstream); independence-aware planner should avoid redundant second query.  
- **H3 World 3 (Fragile EIG):** Action A has higher nominal EIG but under a slightly changed model is misleading; Action B is robust. Robust planner should favor B.【21†L326-L334】  
- **H3 World 4 (Expensive vs. Cheap):** Action A resolves all uncertainty (very high cost), Action B resolves most cheaply. Pareto planner should retain both; policy decides.  
- **H3 World 5 (Unavailable Source):** Best action is unreachable (SOURCE_REQUIRED); feasible set is limited.  
- **H3 World 6 (Scheduled Update):** A high-value outcome will arrive soon (future observation); HELIOS should `WAIT_FOR_OBSERVATION`.  
- **H3 World 7 (Stuck Unknown):** All known models fail; action gains are low; result is `UNKNOWN_NOVEL`.  
- **H3 World 8 (Misinformation):** Action A increases confidence in the wrong model and hurts predictive score (flagged as `POTENTIALLY_MISINFORMATIVE`).  
- **H3 World 9 (Source Outage):** Planned best source fails after planning; system should replan, not treat it as evidence.  
- **H3 World 10 (Restart):** Simulate persistence crash; verify decision ID and actions remain stable on restart.  

- **H4 World A (Entitlement Trap):** Source A (high quality, *ENTITLEMENT_BLOCKED*), Source B (slower, AVAILABLE). Router picks B.  
- **H4 World B (Correlated Sources):** Two sources from same provider (lack independence) vs. an independent one. Prefer independent (Source C).  
- **H4 World C (Spot vs Futures):** Request “MGC futures price”. Available: gold spot (not exact) and MGC futures. Should choose exact futures or denote gold as unacceptable.  
- **H4 World D (Staleness vs Freshness):** Source A has perfect data but is stale; B is fresh with slightly lower quality. If freshness required, choose B.  
- **H4 World E (Policy Change):** API becomes credentialed at future date. Before date, source is still AVAILABLE (maybe with a warning flag); after date it becomes CREDENTIAL_REQUIRED.  
- **H4 World F (Placeholder Values):** API returns valid price but zeros or placeholders for other fields. System accepts valid data but quarantines suspicious fields (OWASP guidance)【16†L200-L209】.  
- **H4 World G (Timeout/Failure):** Provider timeout yields no payload. HELIOS must record a failure, decrement health, but not treat it as data.  
- **H4 World H (Exact Substitute):** Primary source down, an exact-semantic substitute exists. Router uses substitute and logs substitution.  
- **H4 World I (Degraded Substitute):** No exact substitute, only degraded (different venue/representation). Mark as `DEGRADED` and use only if request allows it.  
- **H4 World J (Restart):** Selected adapter persists; on restart, verify same adapter is chosen (idempotency).  

Each world is represented as code or data fixtures (e.g. dictionaries of sources, actions, etc.), used by `test_tournament.py`. **Running tournaments:** A wrapper should iterate actions through each planner (P0–P5) and compare metrics. Use `pytest` to invoke these or a custom script:  
```bash
pytest tests/beliefs
pytest tests/interrogation
pytest tests/sources
```
Or run specific world tests. Ensure reproducibility by setting random seeds where needed (see tests with `random_seed`).  

## 7. Security & Firewall Checklist  

- **AST Import Scan:** Write a static test (`pytest tests/firewall`) that fails if any HELIOS code `import`s forbidden modules: `icarus_engine`, `icarus_bridge`, any broker/execution modules, etc. No implicit exec.  
- **Forbidden Secrets:** ENV vars like `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `WEBHOOK_SECRET`, `ADMIN_TOKEN` must *not* be loaded into HELIOS. If present, the environment should prevent them or code should reject.  
- **Network Restrictions:** Only allow HTTP(S) calls to known endpoints. Specifically, for ICARUS adapter allowlist only `localhost` and `/healthz`, `/status/public`. Disallow other hosts/ports.  
- **No Outside Calls:** HELIOS should not initiate any outbound orders or trades. Tests must ensure no code path calls an exchange API (e.g. raise if any mention of “submit_order”, “market_position”, etc. in source).  
- **Archive & File Handling:** Content from sources is untrusted. When handling file uploads/downloads, follow OWASP guidelines:  
  - Only allow known safe extensions; never execute or parse unknown binaries.  
  - Validate MIME type and content signature. Rename files to safe names, enforce length limits.  
  - Store any files outside application root or in a quarantine area.  
  - Use antivirus/sandbox if possible for complex types【16†L200-L209】.  
  - Reject known dangerous types (e.g. `.exe`, `.sh`, `.dll`, as per OWASP).  
- **Input Validation:** All external inputs (API payloads, sibling packets) must be validated against schema. Fail-closed on schema drift (e.g. missing required fields).  
- **Replay/Idempotency:** All external operations (source queries, experiments) must use idempotent identifiers. Follow AWS advice: include a unique request ID and assume retries may happen【21†L394-L402】. This prevents duplicate side-effects.  
- **Records Signing:** All critical stored records (contracts, logs) should be cryptographically signed or hashed. Use RFC8785 canonical JSON for consistent hashes【3†L67-L72】. Consider Sigstore/Rekor for public audit logs (not implemented initially but noted in `docs/RISK_LEDGER.md`).  
- **Database Encryption:** (If any sensitive data) ensure SQLite database is file-encrypted or on encrypted disk. (Optional, if handling secrets).  
- **Scoping:** HELIOS must enforce least privilege: routers and plugins declare their minimal capabilities (`CAPABILITY manifest` per H3 planner). Test that no plugin can perform unexpected side-effects.  

## 8. Promotion & Policy Gates for Advanced Capabilities  
Advanced components (marked with `-X` or H6 features) must be gated by empirical tests. For each new capability:  

- **Theory/Invariant Check:** Document admissibility and assumptions (in ADR or doc).  
- **Unit Tests:** Write deterministic tests.  
- **Hostile Worlds:** Evaluate on synthetic adversarial scenarios (e.g. distribution shifts, correlated sources).  
- **Baseline Comparison:** Compare against a simpler fallback (the “baseline” planner or default algorithm).  
- **Ablation:** Disable the feature to ensure performance degrades.  
- **Historic Replay:** On past real/simulated data, the new method should not worsen any key metric.  
- **Shadow Evaluation:** Run in parallel for a while, logging results without affecting decisions.  
- **Cost/Complexity Audit:** Quantify added compute or complexity; ensure benefit justifies cost.  

Specifically:  
- **H2-X (Robust Epistemics):** New belief methods must show strictly better calibration or accuracy on held-out prediction tasks without sacrificing them under shift. No silent assumption of probabilistic interpretation (i.e. never treat `EvidenceScore` as `P`).  
- **H3-X (Robust Interrogation):** Any alternative acquisition metric (ambiguous EIG, predictive gain, representativeness) must *never* lead to increased confidence in wrong hypotheses on stress tests. The “misinformation stress suite” must flag it as unsafe if so. Default policy: automatically refuse actions flagged `POTENTIALLY_MISINFORMATIVE`【21†L326-L334】【21†L394-L402】.  
- **H4-X (Acquisition Mesh):** Multi-provider routing (redundancy, failover) is gated by showing improved realized information per cost in experiments. Substitutions must be semantically preserved; any phantom improvement (using unrelated fields) is forbidden.  
- **H6 (Meta Research):** Tournament-based selectors or drift detectors must be externally validated; do not blindly trust learned models. For example, do not activate a learned policy until it outperforms all rule-based baselines.  

## 9. Onboarding Checklist for Agents/Subagents  
When a new developer or agent joins, ensure they have:  

1. **Read Key Docs:** `STATE.md`, `OWNERSHIP.md`, `CAPABILITY_MATRIX.md`, `RISK_LEDGER.md`, `AGENTS.md`.  
2. **Check Git State:** Confirm on correct branch (e.g. `codex/helios-prime-masterbuild`). Ensure no uncommitted changes.  
3. **Sibling Commits:** Verify pinned commits for AION, DAEDALUS, ICARUS in `docs/INTEGRATION_READINESS.md`.  
4. **Follow the Plan:** Read the relevant `docs/plans/Hx-*.md` for assigned plane.  
5. **Task Registration:** Claim a specific task in `docs/UNFINISHED_MATRIX.md` or via project boards. Note it in the SDD ledger file.  
6. **RED→GREEN TDD:** Write a failing test first. Use the example pytest commands.  
7. **No Silent Changes:** Any deviation from plan (e.g. necessary contract tweak) must be recorded as a “ruling” in the SDD ledger.  
8. **Commit Often:** After each test suite passes, commit with descriptive message.  
9. **Mark Evidence:** For each task, record in the SDD ledger: the commit SHA, key commands (pytest output, compiler result), any design decisions.  

**Exact Handoff Message:** When assigning tasks, use the following template (exact wording):  

> *“You are joining the HELIOS PRIME build. Read `STATE.md`, `AGENTS.md`, `docs/OWNERSHIP.md`, `docs/RISK_LEDGER.md`, and the plan for your assigned plane before touching code. Preserve AION, DAEDALUS, NEXUS, ARGUS, ATHENA, and ICARUS ownership. HELIOS never obtains trading or execution authority. Use strict RED→GREEN TDD. Record rulings/deviations in the SDD ledger. Commit frequently. Never claim tests passed without fresh evidence. If a sibling contract differs from the plan, the verified implementation is authoritative unless it violates a frozen HELIOS invariant. Do not silently adapt contract drift.”*  

**SDD Ledger Template:** Each sub-agent should maintain an `.superpowers/sdd/<stream>/progress.md` with entries like:  
```
# SDD Ledger — plan: docs/plans/Hx-xxxx.md

## Task Y: <short title>
- RED: pytest output showing failure (e.g. `self.assertEqual(x, y)`) 
- Implementation: <brief summary of code added>
- GREEN: pytest output showing success
- Regression check: `pytest -q`, `compileall`
- Commit: `<git commit hash>` (should match commit adding GREEN)
- Rulings: <notes on any deviations>
```
This ensures traceability of each change and decision.  

## 10. Deliverable Manifest & Transfer Procedure  
Structure the repository as follows (a schematic tree):  

```text
helios-prime/
├── README.md
├── AGENTS.md
├── STATE.md
├── HANDOFF.md
├── pyproject.toml
├── docs/
│   ├── SOURCE_REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   ├── OWNERSHIP.md
│   ├── CAPABILITY_MATRIX.md
│   ├── INTEGRATION_READINESS.md
│   ├── RISK_LEDGER.md
│   ├── UNFINISHED_MATRIX.md
│   ├── TEST_EVIDENCE.md
│   ├── SECURITY.md
│   ├── EXECUTION_FIREWALL.md
│   ├── CAUSAL_TIME.md
│   ├── PROVENANCE.md
│   ├── RECOVERY.md
│   └── DURABILITY.md
│   ├── audits/       # (if available)
│   └── plans/        # H1–H6 design docs
│       ├── H1-foundation.md
│       ├── ... etc
│   └── adr/          # Architecture Decision Records
│       ├── 0001-authority-boundaries.md
│       ├── ... etc
└── src/helios/
    ├── contracts/
    ├── persistence/
    ├── provenance/
    ├── audit/
    ├── tasks/
    ├── recovery/
    ├── security/
    ├── beliefs/
    ├── interrogation/
    ├── sources/
    ├── integrations/
    └── services/

tests/
├── contracts/
├── persistence/
├── provenance/
├── audit/
├── recovery/
├── firewall/
├── security/
├── beliefs/
├── interrogation/
├── sources/
├── integrations/
└── fixtures/

.superpowers/sdd/
├── helios-h1/
├── helios-h2-belief-engine/
├── helios-h3-interrogation/
├── helios-h4-source-economy/
└── helios-h5-integrations/
```  

All code and docs should be under version control. Ensure `.gitignore` excludes build artifacts.  

**Transfer Steps:**  
1. **Initialize repo:** On GitHub (or on-prem), create `helios-prime`. Set `main` as protected, create branch `codex/helios-prime-masterbuild`.  
2. **Commit stubs:** Populate with the above structure and stub files. Commit to `codex/helios-prime-masterbuild`.  
3. **Push:** `git push -u origin codex/helios-prime-masterbuild`.  
4. **CI Setup (optional):** If using a CI (e.g. GitHub Actions), add a basic workflow to run `pytest` and `compileall` on push/PR.  
5. **Notify team:** Share the repo/branch link with the team, referencing this handoff.  

**Deliverable Package (zip/tar):** The entire repository (with full directory structure above) is the deliverable. For offline transfer, include the `.git` folder to preserve history or prefix commit hashes. Usually, providing the GitHub repo link is sufficient, but an archived snapshot can be prepared via:  
```bash
git checkout codex/helios-prime-masterbuild
git archive --format=tar --prefix=helios-prime/ -o helios-prime.tar HEAD
```  

**Assumptions:** The target Git organization/repo is unspecified (use your org). CI system is unspecified (we assume Python pytest). Repo access (SSH/HTTPS) should be pre-arranged for developers. We assume Linux-like environment.  

## References (Standards & Best Practices)  
- **JSON Canonicalization:** HELIOS uses RFC8785 JCS for signing JSON data【3†L67-L72】.  
- **Provenance:** Concepts aligned with W3C PROV model (e.g. entities, activities).  
- **SQLite Durability:** Use WAL mode and `BEGIN IMMEDIATE` to ensure crash-safety.  
- **Logging/Trace:** Consider Sigstore/Rekor for public audit (see Sigstore docs).  
- **Security:** Follow OWASP Upload Cheat Sheet for handling untrusted file content【16†L200-L209】.  
- **Idempotency:** Follow AWS guidelines: design APIs with caller-supplied unique IDs so retries have no side-effects【21†L394-L402】.  
- **Information Theory:** Use proper scoring rules for calibration【3†L118-L127】; robust design avoids maximizing EIG at cost of truth【21†L326-L334】.  

All code changes and documents should be versioned and reviewed according to this plan. The goal is to hand off a self-contained, well-documented HELIOS codebase ready for development.