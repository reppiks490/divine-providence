# Automation / Loop Control-State Snapshot

Snapshot basis: current ChatGPT automation state observed during the 2026-09-25/26 handoff rebuild.
Scope: all known non-3D ICARUS/AEGIS/HELIOS loops plus the explicitly excluded 3D loop for exclusion accounting.

## Active non-3D loops

### AEGIS Masterbuild Loop
- Enabled: true
- Timing: hourly, minute 10 (America/Chicago)
- Last observed run: 2026-09-26T04:10:45.240831Z
- Role: architecture-to-implementation / repair lane, not duplicate assurance/research.
- Invariants: deterministic canonical serialization/replay; strict temporal integrity; fail-closed qualification; tamper-evident provenance/audit; uncertainty cannot increase authority; no synthetic bars as empirical evidence; no invented features; no Pulse rewrite; `execution_authorized=false`.
- Current priority order:
  1. `AEGIS-BACKTEST-PREWINDOW-TRADE-STATE-LEAK-001` — prevent warm-up positions/orders/P&L from contaminating scored-window performance while preserving legitimate indicator warm-up.
  2. PR #18 / PR #29 CLI contract defect and regression coverage for `icarus-plant setup --root DIR`.
  3. AEGIS KERNEL FIRST GATE: serialization/replay, fail-closed chains, provenance/tamper validation, execution authorization immutability, doctor/ledger verification, recovery/checkpoint equivalence, independent regression oracle.
- Required outputs: exact affected interface/file, RED expectation, GREEN criteria, compatibility constraints, focused/full regression plan, or precise blocker.

### ICARUS Loop Governor
- Enabled: true
- Timing: every 2 hours at minute 05 (America/Chicago)
- Last observed run: 2026-09-26T04:07:00.068621Z
- Role: supervisory control tower only; does not do subordinate architecture/coding/research work.
- Permanent rule: never pause/disable/delete/replace/demote the Governor without explicit user instruction.
- Portfolio target: approximately four active subordinate work loops plus the Governor, fewer when added lanes would be duplicative or unsafe.
- Mandatory health classifications: HEALTHY, LATE, STALE, MISCONFIGURED, BLOCKED, UNKNOWN; repeated no-delta work becomes STAGNATING.
- Decision classes: KEEP, MODIFY, PAUSE, ACTIVATE.
- Core constraints: anti-thrashing, preserve distinct roles, retarget high-severity defects to build lane while preserving independent red-team lane, no live-trading authorization, no merge/deploy/publication authority.

### AEGIS Red-Team Loop
- Enabled: true
- Timing: hourly, minute 35 (America/Chicago)
- Last observed run: 2026-09-26T04:33:34.460761Z
- Role: independent adversarial falsification lane complementary to Masterbuild.
- Attack surfaces include timestamp/lookahead leakage, train/holdout contamination, multiple testing/overfitting, OOD/calibration, nonstationarity, redundant-evidence/common-driver errors, execution-cost blindness, schema ambiguity, fault propagation, checkpoint corruption, replay nondeterminism, provenance tampering, privilege violations, and tautological test oracles.
- Output contract: either a minimal reproducible defect package with independent oracle and remediation target, or stronger evidence that a claim survives a meaningful adversarial test.
- State labels: ATTACKED / SURVIVED / FAILED / BLOCKED.
- Safety: `execution_authorized=false`; no merge/deploy/publish/repository mutation without authorization.

### ICARUS Unified Control Cycle
- Enabled: true
- Timing: hourly, minute 00 (America/Chicago)
- Last observed run: 2026-09-26T04:02:00.872216Z
- Replaces legacy independently scheduled S1-S5 chain for authoritative same-cycle operation.
- Policy: `PIPELINE_POLICY_VERSION='icarus-control-v1'`
- Handoff schema: `icarus-pipeline-v1`
- Cycle ID: scheduled America/Chicago local hour `YYYYMMDD-HH`
- Execution instance: `CYCLE_ID + '-UNIFIED'`
- Safety: `execution_authorized=false`, no synthetic empirical bars, no invented trainer slots/features, no Pulse rewrite, fail-closed qualification, deterministic replay, tamper-evident provenance, strict temporal integrity, uncertainty cannot increase authority.
- Required gates:
  - single-flight/overlap guard
  - hard hourly liveness boundary
  - cross-cycle continuity validation
  - immutable repo snapshot set
  - stable evidence/claim/research-attempt IDs
  - dependency/conflict/supersession tracking
  - maturity ladder
  - adaptive depth / value-of-information gating
  - anti-stagnation fingerprint
- Sequential stages:
  1. Evidence Convergence
  2. Deterministic Subsystem Rotation: NEXUS -> AION -> ARGUS -> ATHENA -> DAEDALUS -> ORACLE
  3. Empirical Research
  4. Repair / Architecture Forge
  5. Verification / Release Assurance
- Only S5 can promote `VERIFIED_FOR_INTEGRATION`.

## Paused non-3D loops

### ICARUS Release Cohesion Loop
- Enabled: false
- Last observed run: 2026-09-26T03:38:52.135773Z
- Role: independent integration/regression/qualification lane.
- Current dominant blocker: pre-window executable-state leakage.
- Secondary composition target: PR #29 CLI fix and compatibility with global-root form.
- Post-repair target: AEGIS kernel entry gate.

### ICARUS Implementation Extraction Loop
- Enabled: false
- Last observed run: 2026-09-25T07:15:59.551325Z
- Role: convert verified findings/designs into smallest executable implementation-ready packages.
- Current known extraction target: `ORACLE_CANONICAL_ADMISSION_BLOCKED`.
- Must establish canonical identity, exact interface/schema, provenance/versioning, temporal semantics, replay semantics, failure behavior, tests, target module, and rollback/non-goals without inventing missing authority.

### HELIOS Prime Integration Loop
- Enabled: false
- Last observed run: none
- Role: sibling integration/evolution lane across ICARUS/AEGIS, AION, DAEDALUS and other recovered subsystems.
- Focus: H1-H6 contracts, H5 adapter boundaries, serialized compatibility, provenance ownership, migration/replay tests, compatibility matrices.
- No repository mutation without authorization.

### ICARUS Assurance Loop
- Enabled: false
- Last observed run: 2026-09-25T01:24:04.397806Z
- Role: implementation-and-verification lane; executable gaps only, not new speculative research.
- Constraints mirror ICARUS safety/integrity invariants.

### Legacy S3 Agent Reach Edge Research
- Enabled: false
- Last observed run: 2026-09-24T10:22:41.942619Z
- Role: empirical edge research.
- Major gates: attempt ledger / multiple testing, mechanism decomposition, data sufficiency, estimator validity, signal-lineage and redundancy analysis, OOS incremental tests, costs, walk-forward/holdout, failure regimes.
- Important classification: current hand-built `XGBoost5` composite is derived evidence unless canonical evidence proves independent training.

### Legacy S1 Evidence Convergence
- Enabled: false
- Last observed run: 2026-09-24T11:02:18.437443Z
- Role: pin repo truth, policy epoch, snapshot, evidence lineage, claim/dependency/conflict ledgers.

### Legacy S4 Repair & Architecture Forge
- Enabled: false
- Last observed run: 2026-09-24T06:34:42.830750Z
- Role: RED->GREEN verified defect repair or approved implementation/design package.
- Requires independent test-oracle evidence and does not self-promote to release authority.

### Legacy S2 Subsystem Rotation
- Enabled: false
- Last observed run: 2026-09-24T06:09:41.966314Z
- Role: round-robin NEXUS -> AION -> ARGUS -> ATHENA -> DAEDALUS -> ORACLE.
- Requires same-cycle pinned evidence and exact policy compatibility.

### Legacy S5 Verification & Release
- Enabled: false
- Last observed run: 2026-09-24T05:47:08.023541Z
- Role: independent final-stage verification/release assurance.
- Only stage that may promote to `VERIFIED_FOR_INTEGRATION`.
- Requires policy/snapshot/handoff-chain coherence, dependency closure, conflict resolution, non-inflated evidence lineage, and sufficiently independent verification oracle.

### HELIOS Audit Loop
- Enabled: false
- Last observed run: none
- Role: read-only audit of HELIOS PRIME / ICARUS state.
- Mandate: inspect repo/PR/Actions/handoff evidence; classify components EXISTS/PARTIAL/MISSING/DUPLICATED/BROKEN/UNVERIFIED/STALE/SUPERSEDED/CONTRADICTED/OWNED_BY_OTHER_AGENT.

## Excluded active loop

### 3D Masterbuild Loop
- Enabled: true at snapshot time.
- Explicitly excluded from this handoff per user instruction.
- No 3D prompt, package, reference image, model, key/signature, mesh, texture, or pipeline artifact is intentionally included in the non-3D corpus.

## Important limitation
The automation interface exposes state to ChatGPT but does not provide a direct raw-export-to-container primitive. This file is a faithful structured reconstruction of the observed automation state and control mandates; it is not claimed to be a byte-for-byte serialization of the scheduler's internal database.
