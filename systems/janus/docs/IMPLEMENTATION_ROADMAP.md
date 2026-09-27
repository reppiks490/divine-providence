# JANUS ∞ Implementation Roadmap

## Milestone 1 — Deterministic knowledge substrate
- schema migrations
- strict timestamp parsing
- bitemporal queries: as-valid-at + as-known-at
- supersession graph
- fact source hashes
- deterministic state digest
- import/export round-trip test

## Milestone 2 — Evidence and authority
- source trust classes
- declared vs inferred facts
- authority ownership registry
- contract fingerprints
- proof bundle lifecycle
- prohibition checks for unauthorized promotion

## Milestone 3 — Project graph
- explicit dependency ingestion
- Python import graph adapter
- test-to-module linkage
- doc/contract linkage
- centrality calculation
- blast-radius estimator

## Milestone 4 — Reconciliation
- filesystem snapshot parity
- git commit/tree identity
- semantic fingerprints for Python interfaces
- stale-hand-off detection
- duplicate-work fingerprints
- minimal reconciliation plans

## Milestone 5 — Evolution loop
- opportunity generation
- transparent priority scoring
- proof-plan generation
- falsification templates
- branch/capsule manifests
- human-governed one-pass executor

## Milestone 6 — Handoff compression
- proof-delta packets
- round-trip reconstruction
- token/context budget measurements
- stale/superseded narrative pruning
- required-first-read ordering

## Milestone 7 — Advanced research
- learned but explainable leverage-weight calibration
- project graph communities
- causal regression attribution
- verification-budget optimization
- multi-agent empirical task routing



## After Run 007

Highest-leverage next work:
1. Proof lifecycle conflict quarantine for contradictory same-boundary events.
2. Replacement-chain validation for `superseded_by`, including cycle detection.
3. Historical evidence archive format so compact handoffs can optionally replay full prior conflict surfaces.
4. Live-repository reconciliation only after repository access and ownership claims are verified.
