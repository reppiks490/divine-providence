# PROMETHEUS v0.4 Lineage + Disagreement Diagnosis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic root-cause diagnosis for disagreement cases and append-only lineage manifests that detect stale research evidence when contract fingerprints change.

**Architecture:** Extend existing immutable PROMETHEUS artifacts rather than creating a parallel subsystem. Disagreement diagnosis remains conservative and evidence-derived; lineage records artifact ancestry plus contract fingerprints and can be checked against current fingerprints without mutating prior artifacts. Promotion remains DAEDALUS-review-only and production authorization remains impossible.

**Tech Stack:** Python 3.11+, dataclasses, pytest, existing content-addressed `content_id` identity.

**Spec:** `docs/superpowers/specs/2026-09-24-prometheus-autonomous-systems-evolution-design.md`

## Global Constraints

- PROMETHEUS remains research-only and cannot authorize production.
- NEXUS remains authoritative for market-data identity, replay, and same-instant causality.
- AION remains authoritative for durable evidence memory; local research memory is only an orchestration index.
- DAEDALUS remains authoritative for protected validation and promotion.
- Existing artifacts are immutable; staleness creates new artifacts rather than rewriting old ones.
- Unknown disagreement causes must resolve to explicit ambiguity, never fabricated certainty.

## Review Focus

- Role-specific sibling fields must classify as intentional specialization rather than model failure.
- Availability mismatches must dominate lower-priority value disagreement explanations.
- Contract fingerprint changes must mark dependent lineage stale without changing the original lineage ID.
- Unknown/new dimensions must classify as irreducible ambiguity instead of inventing a root cause.
- A stale lineage must never generate a DAEDALUS review packet.

---

### Task 1: Deterministic Disagreement Diagnosis

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Create: `src/prometheus_loop/sentinel/diagnosis.py`
- Test: `tests/test_disagreement_diagnosis.py`

**Interfaces:**
- Consumes: `DisagreementCase`, `ObservationEnvelope`
- Produces: `DisagreementDiagnosis`, `DisagreementCause`, `diagnose_disagreement(...)`

- [ ] **Step 1: Write failing tests** for intentional specialization, availability mismatch, source-health mismatch, representation mismatch, regime boundary, and irreducible ambiguity.
- [ ] **Step 2: Run focused tests** and confirm failure because diagnosis types/functions do not exist.
- [ ] **Step 3: Implement minimal deterministic diagnosis** with precedence: availability mismatch → source health → representation → regime boundary → known role-specialization dimensions → irreducible ambiguity.
- [ ] **Step 4: Run focused and full suites** and confirm green.
- [ ] **Step 5: Commit** `feat: diagnose sibling disagreement causes`.

### Task 2: Append-Only Lineage + Staleness

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Create: `src/prometheus_loop/lineage.py`
- Test: `tests/test_lineage.py`

**Interfaces:**
- Consumes: artifact IDs, predecessor IDs, contract fingerprints
- Produces: `ResearchLineageManifest`, `StaleEvidenceReport`, `build_lineage_manifest(...)`, `detect_stale_lineage(...)`

- [ ] **Step 1: Write failing tests** proving deterministic identity, preserved predecessor ordering through canonical sorting, no mutation on staleness detection, and stale detection when a fingerprint changes or disappears.
- [ ] **Step 2: Run focused tests** and confirm failure because lineage functions/types do not exist.
- [ ] **Step 3: Implement immutable lineage manifest and stale report** using content-derived IDs and sorted unique IDs/fingerprints.
- [ ] **Step 4: Run focused and full suites** and confirm green.
- [ ] **Step 5: Commit** `feat: add stale-aware research lineage`.

### Task 3: Orchestration + Promotion Gate Integration

**Files:**
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Modify: `src/prometheus_loop/contracts.py`
- Modify: `src/prometheus_loop/policy/promotion.py`
- Test: `tests/test_loop_lineage.py`

**Interfaces:**
- Consumes: existing loop artifacts, diagnosis artifacts, current contract fingerprints
- Produces: `LoopRunResult.diagnoses`, `LoopRunResult.lineage_manifest_id`, lineage-bound `ResearchPromotionPacket`

- [ ] **Step 1: Write failing tests** proving diagnoses and lineage persist, NEXUS contract fingerprint is included for `run_nexus`, and stale lineage blocks promotion.
- [ ] **Step 2: Run focused tests** and confirm failure on missing orchestration fields/behavior.
- [ ] **Step 3: Integrate diagnosis + lineage** without duplicating the existing plugin/SENTINEL/FORGE path; promotion packet must carry `lineage_manifest_id` and refuse stale lineage.
- [ ] **Step 4: Run focused and full suites** and confirm green.
- [ ] **Step 5: Commit** `feat: bind lineage and diagnosis into loop`.

### Task 4: Documentation, Version Metadata, Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/VALIDATION_STATUS.md`
- Create: `docs/architecture/lineage-and-diagnosis.md`
- Create: `docs/changes/2026-09-25-prometheus-v0.4-lineage-diagnosis.md`
- Modify: `pyproject.toml`
- Modify: `src/prometheus_loop/cli.py`

**Interfaces:**
- Consumes: verified implementation behavior
- Produces: durable current-state documentation and v0.4 metadata

- [ ] **Step 1: Update docs** with diagnosis precedence, lineage/staleness semantics, and authority boundaries.
- [ ] **Step 2: Update package/CLI version wording** from stale v0.1 metadata to v0.4.
- [ ] **Step 3: Run final gate**: compile, full pytest suite, deterministic CLI demo, authority/credential/import scans, tracked-bytecode scan, `git diff --check`.
- [ ] **Step 4: Commit** `docs: record PROMETHEUS v0.4 verification`.
