# ORACLE and DAEDALUS research upgrade

User intent: substantially improve the research engines, with unattended operation
and measurable evidence. Existing user preference is no manual setup or repeated
approval steps. This is an extension of existing engines and flows, not a rebuild.
No claim of exponential predictive accuracy or financial return is justified.

## Audited problems

- DAEDALUS's five sequential folds cover only about 1,250 early test rows even
  when a source has tens of thousands of development rows.
- Batch resume treats any source-named JSON as reusable, without checking the
  configuration, code, dependency context, or result integrity.
- ORACLE assessment includes future-received contributions and counts multiple
  textual claims of the same evidence as additional voting strength.
- ORACLE ranking optimizes each job independently; a small budget can select
  several similar jobs while leaving other research groups unexplored.
- Both owners use SQLite context managers without an explicit close lifecycle.

## Selected implementation

1. Add opt-in spread development folds and a bounded rolling training window.
   Keep existing sequential defaults and all protected acceptance thresholds.
   Report sampled rows and source-row span separately: a broader span is not
   more independent test observations or confirmed alpha.
2. Bind batch reuse to source/configuration/scientific code/dependencies and
   result integrity. Refresh stale or corrupt cache data without spending tails.
3. Enforce as-of assessment and one vote per immutable evidence item. Reject
   source spoofing and past-time dispatch using a future financial state.
4. Extend the existing ORACLE scheduler with deterministic marginal diversity
   ranking. Immutable jobs retain their specifications; group penalties and
   priors are explicit policy, not measured confidence or causal truth.
5. Explicitly close owner-local SQLite connections, preserving transaction and
   schema semantics. No cross-system persistence ownership is introduced.
6. Use the spread/rolling protocol and ORACLE scheduling in the daily institution.
   Research groups use actual repository/archive provenance, not assumed symbols.
   Historical memory is retained under its original protocol/context.

## Alternatives and authority

Rejected: larger models without evidence, weakening gates to generate winners,
spending protected tails for a benchmark, rebuilding ORACLE's scheduler/outbox,
and interpreting historical chart prices as broker fills. The 408 budget-eligible
sources are a subset of the audited 659-member public corpus, not the historical
handoff's claimed 800+ authoritative Work corpus.

Success means reproducing the prior bugs with regression tests, broader real-data
development span at a registered training bound, honest elapsed-time measurements,
cache invalidation when scientific context changes, deterministic diverse job
selection, preserved promotion/firewall boundaries, and successful unattended
publication. Predictive benefit remains an empirical question.
