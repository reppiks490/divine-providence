# Run 031 Independent Receiver Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Run 030 storage-state certificates independently reproducible by a fresh receiver and chain successive certificates with auditable state deltas.

**Architecture:** Extend the existing SQLite-backed JANUS core with a selective portable replay bundle rather than copying the sender database wholesale. Replay occurs in an isolated fresh receiver, verifies all content addresses/signatures/closure first, then compares the rebuilt certificate-bound state. Certificate chains are separate signed/content-addressed evidence objects so they do not self-mutate certified storage.

**Tech Stack:** Python 3, sqlite3, Ed25519/cryptography, JSON/JSON Schema, pytest.

**Spec:** `docs/RUN_031_DESIGN.md`

## Global Constraints
- Preserve sibling authority boundaries.
- TDD: every production behavior is preceded by a failing test.
- No live-repository claim without a real authoritative Git worktree.
- Portable replay must fail closed before authoritative receiver mutation on malformed or incomplete evidence.

## Review Focus
- Replay bundle omission/tampering before import.
- Fresh receiver exact state reproduction versus superficial signature validation.
- Certificate predecessor and delta integrity.
- Chain cycle/branch handling.
- Host-fault probe isolation from authoritative storage.

---

## Task 1 — Fresh receiver replay bundle
- [ ] Add failing tests for export/import/replay into a fresh receiver and tampered/missing bundle evidence.
- [ ] Run focused tests and confirm RED.
- [ ] Implement minimum portable bundle/export/receiver replay APIs.
- [ ] Run focused + full tests and confirm GREEN.

## Task 2 — Certificate chain and deltas
- [ ] Add failing tests for valid two-certificate chain and predecessor/delta tampering.
- [ ] Run focused tests and confirm RED.
- [ ] Implement content-addressed chain entry creation/verification and deterministic delta calculation.
- [ ] Run focused + full tests and confirm GREEN.

## Task 3 — Additional host fault
- [ ] Add failing test for an isolated kernel-enforced process limit fault distinct from EFBIG/EACCES.
- [ ] Run focused test and confirm RED.
- [ ] Implement safe scratch-only probe.
- [ ] Run focused + full tests and confirm GREEN.

## Task 4 — Contracts, docs, handoff
- [ ] Add schemas and architecture increment.
- [ ] Update README/handoff/state capsule.
- [ ] Run full pytest, compileall, schema meta-validation, ZIP integrity, and hashes.
- [ ] Persist versioned ZIP/capsule to Google Drive without overwrite.
