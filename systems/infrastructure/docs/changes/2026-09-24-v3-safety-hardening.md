# Change record: V3 safety hardening

- **When:** 2026-09-24
- **Actor / agent:** ChatGPT GPT-5.6 Sol
- **Request / source:** Continue the Infrastructure Supervisory Loop while preserving fail-open behavior, bounded autonomy, sibling-system authority boundaries, and verified increments.
- **Affected code/components:** `infrastructure_loop.py`, `tests/test_loop.py`, `README.md`, `docs/safety-contract.md`, `docs/current-state.md`.
- **Before:** outcome memory could raise low current evidence confidence above the mutation guard threshold; `critical_health_floor` and `canary_required_above_risk` existed as configuration but did not enforce behavior.
- **Change:** outcome history now adjusts expected utility only; the canary threshold is fail-closed until a real staged executor exists; high-impact actions require explicit current health context; the critical health floor blocks high-impact autonomous classes; cycle guard evaluation now receives current component health.
- **Now:** historical success cannot authorize a poorly evidenced current diagnosis, and two previously passive safety settings are active controls.
- **Why:** bounded autonomy requires current evidence to remain the authorization source and policy knobs to correspond to executable behavior rather than documentation-only intent.
- **Technical reasoning:** a fake `payload["canary"]` marker was rejected because it would label a full action as a canary without limiting blast radius. Until the adapter contract can stage and promote a canary, denial is the only truthful enforcement.
- **Compatibility:** existing `ActionGuard.approve(action)` calls remain valid because `health_score` is optional. The default policy now rejects planner-generated actions whose risk exceeds the default canary threshold, notably `graceful_restart` at risk `0.24`.
- **Rollback:** restore the previous artifact if this conservative behavior must be removed. Do not selectively restore confidence promotion; that reopens an authorization flaw.
- **Operational consequence:** no dependency or deployment change. Restarting/reloading the Python process is sufficient for code adoption where this module is used directly.
- **Verification evidence:** regression tests cover learned-confidence escalation, canary-threshold denial, critical-floor high-impact denial, and low-impact allowance; full-suite result is recorded in the cycle report after final verification.
- **Future implications:** add a genuine staged-canary adapter contract before permitting above-threshold actions; then add dependency-aware blast-radius governance.
- **Stale when:** any cited behavior, threshold semantics, or adapter execution contract changes.
