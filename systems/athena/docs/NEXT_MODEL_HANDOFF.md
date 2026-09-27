# NEXT MODEL HANDOFF — ATHENA

1. Do not merge ATHENA into DAEDALUS or Icarus. Keep it a sibling repo.
2. Read `INTEGRATION_MAP.md` and `docs/BLUEPRINT.md` before coding.
3. First preserve and extend Phase-0 contracts/firewalls; all payloads need provenance and explicit data-plane labels.
4. Build a deterministic event journal + replay harness before adding ML. Preserve repeated timestamps with source-local sequence numbers.
5. Implement interpretable state baselines before deep models. Compare under time-ordered shadow/walk-forward validation.
6. Add calibration/OOD/uncertainty and prove ABSTAIN behavior under stale/missing/OOD scenarios.
7. Add expert competence surfaces using only evidence that was valid at each historical time.
8. Build digital-twin scenarios as stress tests; never convert synthetic performance into empirical proof.
9. Research scheduling may ask DAEDALUS questions but may not read/spend protected outcomes outside DAEDALUS protocol.
10. Icarus integration stays advisory-only until a separate production review.

Completion definition: deterministic replay, plane-firewall tests, state/uncertainty calibration tests, scenario invariants, shadow routing evidence, full lineage, zero broker authority.
