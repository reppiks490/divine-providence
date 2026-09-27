# PROMETHEUS v0.4 Provenance Attestation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind every DAEDALUS review packet to one deterministic, immutable PROMETHEUS research provenance manifest and fail closed on lineage drift.

**Architecture:** Add a focused provenance artifact/builder, thread source-contract and parent-manifest identities through orchestration, and require promotion validation against the current run evidence. Preserve the existing research-only authority boundary.

**Tech Stack:** Python 3.11+, standard library, dataclasses, pytest, existing content-addressed ID helpers.

**Spec:** `docs/superpowers/specs/2026-09-25-prometheus-v0.4-provenance-attestation-design.md`

## Global Constraints

- PROMETHEUS remains research-only; no production authorization, broker, order, or sibling-write path.
- DAEDALUS remains authoritative for validation/promotion.
- NEXUS remains authoritative for causal/sibling contract identity.
- Raw plugin bodies and secrets remain outside provenance artifacts.
- No new production dependency.
- Behavior changes use TDD.

## Review Focus

- Same content in different tuple order must canonicalize to one manifest ID.
- Duplicate IDs must fail instead of silently deduplicating caller mistakes.
- A stale manifest from another loop/candidate/experiment must not produce a packet.
- NEXUS runs must bind the validated release contract identity without inventing sibling data.
- Negative/degraded paths must not accidentally emit a provenance-backed promotion packet.

---

### Task 1: Provenance manifest contract

**Files:**
- Create: `src/prometheus_loop/provenance.py`
- Modify: `src/prometheus_loop/contracts.py`
- Test: `tests/test_provenance.py`

**Interfaces:**
- Produces: `ResearchProvenanceManifest`; `build_research_provenance_manifest(...)`.

- [ ] Write failing tests for deterministic canonical ID, required fields, and duplicate rejection.
- [ ] Run those tests and confirm RED.
- [ ] Implement the minimal immutable contract and builder.
- [ ] Run task tests and confirm GREEN.
- [ ] Commit.

### Task 2: Provenance-bound promotion gate

**Files:**
- Modify: `src/prometheus_loop/policy/promotion.py`
- Modify: `src/prometheus_loop/contracts.py`
- Modify: `tests/test_promotion_packet.py`

**Interfaces:**
- Consumes: `ResearchProvenanceManifest`.
- Produces: promotion packet with `provenance_manifest_id`; exact manifest validation.

- [ ] Add failing tests for manifest reference, stale/tampered bindings, and packet evidence inclusion.
- [ ] Confirm RED.
- [ ] Implement exact fail-closed validation.
- [ ] Confirm focused tests GREEN.
- [ ] Commit.

### Task 3: Orchestration and NEXUS lineage

**Files:**
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Modify: `tests/test_loop.py`
- Modify: `tests/test_sibling_loop.py`

**Interfaces:**
- Consumes: source contract IDs and optional parent manifest IDs.
- Produces: persisted manifest ID on eligible `LoopRunResult`; NEXUS contract snapshot binding.

- [ ] Add failing end-to-end tests for persisted manifest and NEXUS source-contract binding.
- [ ] Confirm RED.
- [ ] Thread identities through run inputs/run ID and build manifest before promotion.
- [ ] Confirm focused and full tests GREEN.
- [ ] Commit.

### Task 4: Documentation and release verification

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/architecture/plugin-evidence-and-promotion.md`
- Create: `docs/changes/2026-09-25-prometheus-v0.4-provenance-attestation.md`
- Modify: `docs/VALIDATION_STATUS.md`

**Interfaces:**
- Documents the final contract and evidence limits.

- [ ] Update architecture/agent rules and validation notes.
- [ ] Run compileall, full pytest, demo, authority/import/credential/bytecode scans, and `git diff --check`.
- [ ] Commit only after fresh verification evidence.
