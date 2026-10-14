# ICARUS ORACLE — Financial & Research Automation Fabric

ORACLE turns Icarus Financial/Research tabs into a closed-loop research operating system. It aggregates causal financial state, creates falsifiable hypotheses, schedules information-value research, exchanges evidence with NEXUS/AION/ARGUS/ATHENA/DAEDALUS, tracks thesis health, and emits research-only candidate packets.

**Hard boundary:** ORACLE has no broker/order API and never directly authorizes production execution.

See `docs/ARCHITECTURE.md` and `docs/CURRENT.md`.

The 2026-10-14 research upgrade adds as-of contribution assessment, duplicate
observation voting protection, source matching, future-context dispatch guards,
and opt-in marginal group-diversity ranking in the existing scheduler. Ranking
preserves immutable job specifications; allocation priors are not calibrated
edge probabilities. Owner SQLite connections close explicitly. The unattended
institution now uses this scheduler and persists pre-test questions and job
specifications alongside DAEDALUS results. These changes do not complete deployed
sibling-service adapters, promotion authority or a full trading application.
