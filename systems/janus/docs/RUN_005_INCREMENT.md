# JANUS ∞ Run 005 — Proof-Carrying Temporal Normalization Ledger

Run 005 adds an immutable normalization-decision ledger over Run 004 proposals. Approval or rejection requires proof references and an explicit decider. Approval creates a derived overlay that closes an older fact only during reconstruction; the original fact row is never mutated. Approved decisions can be revoked with actor, reason, and time, after which the overlay no longer applies at later knowledge boundaries. Decisions and revocations participate in the state digest and handoff round-trip.

Safety invariant: temporal interpretation is append-only evidence, never destructive history rewriting.
