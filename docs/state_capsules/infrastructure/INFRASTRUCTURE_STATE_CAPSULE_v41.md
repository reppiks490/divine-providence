# Infrastructure Supervisory Loop — State Capsule v41

Checkpoint: v41 governed authority-set epochs + remote transparency history + finer crash-recovery failpoints.

Predecessor: v40 ZIP SHA-256 `46c066e631d534e132ca4feefd4bd442dff53141bd779f1f6b5a954502fb1533`; inherited v40 verification reproduced 296/296 tests before v41 mutation.

v41 completed:
- `GovernanceAuthoritySetStore` append-only authority-set epochs.
- Rotation requires previous-epoch quorum, threshold non-reduction, and at least prior-threshold exact authority overlap.
- Historical verification is epoch-specific; newly introduced authority cannot retroactively authorize older epochs.
- `RemoteTransparencyHistoryStore` append-only per-peer/log checkpoint history.
- Sequence rollback rejection, idempotent exact repeats, same-sequence/different-hash rejection, and cross-log split-view evidence.
- Imported observations retain/reverify independent anchor-quorum receipts.
- `CrashReconciledGovernanceStore` sub-phase failpoints after individual governance/admission component writes and after COMMITTED journal state.
- Restart reconciliation accepts only defined component-ahead-of-journal states and cleans stale recovery payload only after committed verification.

Verification:
- Final/fresh-extract test suite: 305/305 PASS.
- compileall: PASS.
- ZIP integrity: PASS.
- Candidate ZIP SHA-256: `66dc2d7ddcb5e68daaca947812ea64db9802524d1573584aaa142c378798e5da`.

Authority: unchanged. v41 authenticates/preserves recovery and governance evidence; it does not acquire live-trading, deployment, repository-promotion, AEGIS, JANUS, VECTOR, NEXUS, or SuperMesh authority.

Status: VERIFIED LOCAL CANDIDATE ONLY. No repository adoption or production authorization is asserted. v40 remains untouched.

Resume: determine the next Infrastructure increment from the owning Infrastructure loop/capsule before mutation. Do not invent a v42 scope from this capsule alone.
