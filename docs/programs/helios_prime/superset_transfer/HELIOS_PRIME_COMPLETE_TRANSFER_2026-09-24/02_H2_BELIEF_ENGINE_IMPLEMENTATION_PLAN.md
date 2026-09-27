# H2 — BELIEF ENGINE IMPLEMENTATION PLAN

## Mission
Turn H1-qualified evidence into a falsifiable, replayable, calibrated belief state without inventing probabilities or erasing contradictions.

## Invariants
- no future information in historical beliefs;
- no evidence without H1 provenance;
- correlated source families cannot inflate independent support;
- EvidenceScore is not probability;
- no posterior without explicit likelihood model;
- contradictions are immutable history;
- prospective predictions cannot be rewritten after observation;
- UNKNOWN_OR_NOVEL remains first-class;
- synthetic evidence remains synthetic;
- no execution authority.

## H2.1 Hypothesis contracts
Statuses: PROPOSED, ACTIVE, WEAKENED, SUPPORTED, FALSIFIED, SUPERSEDED, UNRESOLVED. Never PROVEN/VALIDATED/CERTAIN. SUPPORTED remains falsifiable. Store scopes, falsification conditions, expected observations and parent relationships. Canonicalize ordering and make terminal states immutable.

## H2.2 EvidenceImpact
Polarity: SUPPORTS, CONTRADICTS, NEUTRAL, UNINFORMATIVE, UNKNOWN. Preserve raw strength, source reliability, timing quality, regime relevance, independence factor and effective strength separately. Shared ultimate provenance root reduces incremental independence; duplicate lineage may contribute zero new independence.

## H2.3 Prospective predictions
PredictionExpectation records prediction ID, hypothesis, observable, creation/evaluation times, expected outcome, tolerance, optional probability/scoring rule, evidence cutoff and method version. Require created_ns < evaluate_after_ns. Probability requires a scoring rule. Preexisting evidence cannot masquerade as future validation. Assessments: SUPPORTED, CONTRADICTED, AMBIGUOUS, NOT_OBSERVABLE, INVALIDATED_BY_DATA_QUALITY.

## H2.4 Contradiction engine
Types include prediction, source, timing, representation, regime, methodology, revision and model disagreements. Resolution is a new immutable event, never deletion. Historical snapshots must still show contradictions that existed before later resolution.

## H2.5 Evidence-score baseline
Simple interpretable vector: support, contradiction, unexplained residual, source independence, timing quality, regime relevance, method version. Deterministic and order invariant. Advanced methods must beat this baseline.

## H2.6 BeliefSnapshot
Store investigation, knowledge cutoff, hypothesis states, open contradictions, UNKNOWN state, evidence/provenance cutoff hashes, method versions and logical-state hash. Prefix invariance is mandatory: later evidence/revisions must not change snapshot(at t).

## H2.7 UNKNOWN_OR_NOVEL V1
Inputs: unexplained residual, contradiction pressure, predictive failure, OOD pressure, analogue weakness, model disagreement. combined_signal is NOT probability of a new regime. High signal may request novel-hypothesis discovery but cannot declare or validate a regime.

## H2.8 Calibration ledger
Brier/log score only genuine probabilistic forecasts. Nonprobabilistic expectations use separate hit/diagnostic metrics. Keep calibration populations split by instrument, regime, family and method version.

## H2.9 Synthetic worlds
A correlated-confirmation trap; B failed prospective story; C data-corruption explanation; D unknown/novel; E future revision; F synthetic-evidence lineage. End-to-end restart equivalence required.

## H2 gate
pytest tests/beliefs -q
pytest -q
pytest -W error::ResourceWarning -q
python -m compileall -q src tests
plus H1 firewall regression. H3 begins only after actual GREEN evidence.
