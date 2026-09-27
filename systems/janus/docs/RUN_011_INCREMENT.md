# JANUS ∞ Run 011 — Generalized Temporal Truth Delta + Minimal Causal Proof Certificate

Run 011 extends Run 010 without changing sibling-system authority boundaries.

## Added
- `generalized_truth_delta(change_id)` read-only causal query.
- Compares complete interval-eligible observation surfaces at every automatically discovered `(valid_at, known_at-before/after)` boundary for proof-dependent subject/predicates.
- Emits added/removed/changed fact-level truth deltas even when no conflict transition occurs.
- Reuses Run 010 proof lineage, normalization lineage, conflict deltas, and transitive dependency blast radius.
- Emits `janus-minimal-causal-proof-certificate-v1`, hashing only causal identifiers/deltas needed to reproduce the explanation.

## Invariants
- No source fact, proof, normalization decision, or dependency is mutated by causal analysis.
- Unknown proofs fail closed.
- Original observations remain immutable.
- Authority/evidence adjudication remains owned by the unified kernel.
- NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus authority boundaries remain unchanged.

## Deliberate limitation
The truth surface is an evidence surface of interval-eligible unsuperseded observations, not a claim that every observation is accepted as canonical truth. This preserves ambiguity rather than hiding it behind latest-write-wins selection.
