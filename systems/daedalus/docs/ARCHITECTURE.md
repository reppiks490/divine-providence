# DAEDALUS Architecture

## 1. Immutable source catalog
Recursively discovers CSVs, filters OS metadata, fingerprints every file, profiles timestamp/bar mechanics, and marks exact byte duplicates without assuming that similar filenames are duplicates. Catalog identity is preserved even when exact-byte duplicates share compute.

## 2. Causal feature factory
Builds return, range, volatility, volume, bar-mechanics, and optional UTC-calendar features. The full predictor matrix is shifted by at least one source bar before target construction. Repeated timestamps are preserved in standalone research.

## 3. Representation-fusion path
Alternate chart constructions can be used as predictor sources while target and PnL remain anchored to an explicitly selected execution-safe stream. Alignment is strict backward-as-of with `allow_exact_matches=False`; repeated timestamps are rejected in fusion until explicit intra-timestamp ordering metadata exists.

## 4. Hypothesis laboratory
Screens feature/forward-return and bounded interaction hypotheses on development rows only. Benjamini-Hochberg FDR controls the local discovery family. These are research leads, not causal claims.

## 5. Model foundry
Uses diverse baseline families (regularized linear, random forest, extra-trees, histogram gradient boosting). Families compete only on development walk-forward evidence. Complexity receives no automatic preference.

## 6. Development-frozen ensemble
Eligible model families are ranked and weighted using development evidence only. Component membership and weights freeze before the protected tail. The protected tail therefore evaluates one already-defined ensemble object rather than serving as a model-selection tournament.

## 7. Purged walk-forward validation
Uses expanding training windows with explicit purge/embargo gaps. Source-row positions are retained after deadband/feature filtering so target overlap and non-overlapping trade accounting are measured in original source geometry rather than compressed feature-row geometry.

## 8. Development gate
Weak candidates die before protected-tail exposure. A source must meet minimum development AUC, calibration improvement, fold survival, trade count, and completed-fold requirements before it can enter the corpus holdout budget.

## 9. Corpus holdout budget
Corpus research is two-phase. Phase 1 screens exact-byte representatives development-only. Phase 2 ranks qualified sources by development evidence and spends a bounded number of protected tails while enforcing symbol/mechanics diversity caps. Qualified but unselected sources remain pristine.

## 10. Protected holdout ledger
Each protected exposure is recorded before evaluation using source hash, protocol hash, and raw source-row boundaries. A protocol change after exposure produces a conflict under strict mode rather than silently reusing the same tail. Protocol v3 includes development-defined regime diagnostics.

## 11. Adversarial validation
The frozen protected predictions face:
- circular-shift label permutation by default (serial structure preserved),
- moving-block bootstrap of realized trade PnL,
- execution-cost stress,
- probability-threshold perturbation,
- temporal-segment survival,
- development-only frozen-weight feature ablation,
- ensemble disagreement,
- distribution-drift measurement.

## 12. Regime intelligence
Development data receives two complementary treatments. Unsupervised clustering summarizes market states for context. Separately, development medians freeze a simple volatility/efficiency state map; protected predictions are then evaluated within those predeclared states without refitting. Regime-conditioned evidence can veto promotion when enough rows exist, but sparse regimes do not manufacture a score.

## 13. Promotion gate
All enabled gates must pass. A strong headline AUC cannot override poor calibration, drawdown, trade count, drift, robustness, ensemble disagreement, feature-ablation fragility, bootstrap weakness, temporal instability, or regime fragility. Execution-safe identity may also be required.

## 14. Corpus-level false-discovery control
After every selected protected tail has been evaluated, permutation p-values are corrected across the actual protected tests with Benjamini-Hochberg. Only candidates that pass both their local gate and the global q-value gate become globally eligible research candidates.

## 15. Experiment memory / graveyard
SQLite records source fingerprint, model family, configuration, evidence, and promotion state. Meta-memory summarizes accumulated model-family evidence with shrinkage toward neutral AUC, reducing the incentive to repeatedly rediscover failed families.

## 16. Shadow book
Globally eligible research candidates can be registered for forward/shadow observation. Shadow evaluation is evidence collection only; it is not an execution path.

## 17. Icarus bridge
Exports versioned JSON research-candidate manifests and hard-codes `production_authorized=false`. DAEDALUS never writes into Icarus and never places trades.

## 18. Corpus orchestration commands
- `catalog`: inventory only.
- `batch`: resumable **development-only** screening; never spends protected tails.
- `research-corpus`: development screen, diversity-aware holdout budget, protected tests, global FDR.
- `research`: single-source protected research, intentionally consumes that source's holdout under the ledger.
- `research-fusion`: protected research using an execution-safe stream plus strictly backward-aligned alternate representations.
