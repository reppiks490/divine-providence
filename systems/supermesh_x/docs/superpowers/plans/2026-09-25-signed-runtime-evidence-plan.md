# Signed Runtime Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add authenticated runtime evidence and concrete-adapter conformance receipts without expanding execution authority.

**Architecture:** Add one focused signing module layered over v2.9 EvidenceJournal. Ed25519 signs canonical envelopes; a public-key trust store controls verification, rotation, and revocation; SignedEvidenceJournal verifies before append and enforces replay/fence/run binding.

**Tech Stack:** Python 3, cryptography Ed25519, pytest.

**Spec:** docs/superpowers/specs/2026-09-25-signed-runtime-evidence-design.md

## Global Constraints
- Preserve v2.9 and earlier public contracts.
- No private key or secret material in receipts.
- Signatures never grant execution authority.
- Fail closed on unknown/revoked keys, tamper, replay, stale fence, or run mismatch.

## Review Focus
- Canonical serialization must be deterministic.
- Replay identity must survive equivalent dict ordering.
- Rotation must not silently reactivate revoked keys.
- Signature verification must happen before mutation.
- Signed claims must not add capabilities.

### Task 1: Signing and trust boundary
Create `scripts/signed_runtime_evidence.py`; test signer/verifier, trust lifecycle, tamper, wrong key, and canonical envelopes in `tests/test_signed_runtime_evidence.py` using RED→GREEN.

### Task 2: Signed journal admission
Extend the same module/tests with run/fence/replay/authority guards and v2.9 EvidenceJournal integration using RED→GREEN.

### Task 3: Package contract and documentation
Update manifest, smoke, validator, changelog/build report/reference docs; add v3.0 contract test. Run focused then full verification and package only after all gates pass.
