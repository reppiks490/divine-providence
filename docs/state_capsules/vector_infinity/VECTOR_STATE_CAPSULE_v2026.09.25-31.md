# VECTOR ∞ STATE CAPSULE — v2026.09.25-31

## Authoritative checkpoint
Promotion authority remains the Adversarial Router Lab. Immediate predecessor: v30 Delayed-Feedback Memory Matching & Recurrent-Regime Calibration Lab. Offline/synthetic/shadow only.

## Cycle
Recurrent-Prototype Aging, Tail-Profile Matching & False-Recurrence Red-Team Lab.

## Verified synthetic evidence
- 8,000 recurrence episodes across four families: genuine recurrence, tail-lookalike false recurrence, poisoned prototype, and aged recurrence.
- Prototype/current features included mean, scale, lag-1 memory, excess kurtosis, q95, and mean excess above q95.
- Two horizons (1H and 4H) were generated separately to expose horizon-local similarity that fails to propagate.
- Prototype age ranged 5–499 observations; poisoned prototypes carried 25%–65% contamination before small background contamination.

### Policy comparison
{
  "mean_scale": {
    "true_reuse_rate": 0.9566094853683148,
    "false_reuse_rate": 0.7655172413793103,
    "tail_lookalike_false": 0.9888579387186629,
    "poisoned_false": 0.4448,
    "aged_true_reuse": 0.9041184041184042
  },
  "dynamic": {
    "true_reuse_rate": 0.974167507568113,
    "false_reuse_rate": 0.7139573070607553,
    "tail_lookalike_false": 0.9949860724233983,
    "poisoned_false": 0.3104,
    "aged_true_reuse": 0.9311454311454311
  },
  "dynamic_tail": {
    "true_reuse_rate": 0.9985872855701312,
    "false_reuse_rate": 0.19967159277504104,
    "tail_lookalike_false": 0.012813370473537604,
    "poisoned_false": 0.468,
    "aged_true_reuse": 0.9954954954954955
  },
  "fresh_probe_gated_strong": {
    "true_reuse_rate": 0.6151362260343087,
    "false_reuse_rate": 0.0019704433497536944,
    "tail_lookalike_false": 0.003342618384401114,
    "poisoned_false": 0.0,
    "aged_true_reuse": 0.575933075933076,
    "provisional_rate": 0.385125,
    "strong_rate": 0.38175
  }
}

### Cross-horizon recurrence
- Among candidates matching the 1H tail-aware gate, 0.774% failed the multi-horizon compatibility check.
- A 1H recurrence therefore cannot promote or retro-validate a 4H recurrence claim.

### Delayed rollback attack
{
  "false_active_rate": 0.1475,
  "mean_irreversible_damage_per_false_active": 130.8158030365834,
  "mean_rollback_damage_per_false_active": 23.081033054333073,
  "residual_damage_ratio": 0.17643918027150227,
  "median_revocation_delay": 18.0
}

### Prototype quarantine
{
  "overall": 0.29325,
  "poisoned_quarantined": 1.0,
  "aged_recurrence_quarantined": 0.15315315315315314
}

## Core findings
- Mean/scale recurrence matching remains vulnerable to tail aliases.
- Adding memory improves discrimination, but tail-profile features are required to expose regimes with similar center/volatility and different extreme behavior.
- Tail-aware similarity alone is still insufficient: age, contamination, horizon disagreement, and fresh delayed outcomes must govern authority.
- Full fresh-probe gating materially reduces false strong reuse, but also lowers true recurrence coverage; this is a safety/coverage tradeoff, not a free improvement.
- Recurrent evidence is horizon-owned. Lower-horizon recurrence cannot validate the higher horizon whose context contributed to the lower-horizon claim.
- Provisional reuse plus delayed rollback reduces false-recurrence damage relative to irreversible reuse, but residual damage accumulates until feedback arrives.
- Quarantine preserves prototypes for audit/possible future research but removes their ability to seed authority.
- No historical prototype may update itself from a candidate recurrence until that candidate clears fresh revalidation.

## Architecture refinement
- TailProfileFingerprint (TPF): adds high-quantile, excess-tail, shape and volatility-clustering evidence to recurrence identity; fingerprints are versioned by horizon and epoch.
- PrototypeAgeAuthorityDecay (PAAD): similarity can nominate aged prototypes, but reuse authority decays with age/support/freshness rather than remaining permanent.
- RecurrenceAuthorityTier (RAT): NONE → SHADOW_CANDIDATE → PROVISIONAL_REUSE → STRONG_REUSE, with strong reuse requiring fresh evidence.
- CrossHorizonRecurrenceVeto (CHRV): local recurrence can survive locally while higher-horizon disagreement blocks propagation/merge.
- FreshProbeRevalidationGate (FPRG): fresh, unconsumed delayed evidence is mandatory before strong authority; historical similarity is only a prior.
- PrototypeQuarantineLedger (PQL): poisoned, malformed, excessively aged or provenance-corrupt prototypes are retained as immutable audit objects but have zero reuse authority.
- False recurrence rollback uses existing tombstone/reversible-MERGE semantics and cannot erase the history of the failed activation.

## Research grounding
- 2025 PMLR recurrent-concept-drift work reuses earlier models only when current data passes exchangeability and performance checks, supporting fresh validation before recurrence reuse.
- 2026 delayed-feedback ACI work shows that revalidation latency should be interpreted relative to the memory timescale of the residual process.
- 2026 time-series conformal theory explicitly ties validity loss to temporal dependence and predictor memory, supporting dynamic rather than purely marginal recurrence fingerprints.

## Deep Research
DEEP RESEARCH ACTUALLY INVOKED = NO; DEEP RESEARCH UNAVAILABLE.
Exact plugin-directory search for “Deep Research” returned research providers but no exact first-party Deep Research capability.

## Plugins/skills/tools actually used
- Superpowers using-superpowers
- Superpowers brainstorming
- Superpowers verification-before-completion
- Exa Search skill + recurrence/tail-aging research
- Consensus academic search
- Scite literature search
- ordinary current web research
- isolated visible Python synthetic red-team + artifact generation
- File Library / Google Drive persistence attempt

## Available but not materially invoked
- Codex Coordinator, Baton Pass, Akinator are installed, but no repository mutation or coding handoff occurred.

## Partially blocked
- real Icarus/VECTOR replay
- repository implementation and commit identity
- empirical tail-profile calibration on actual markets
- real prototype contamination/aging statistics
- real cross-horizon recurrence labels
- genuine forward-shadow/live evidence
- production-safe authority-tier thresholds

## READY_TO_COMMIT
NO. No sibling/live/registry/execution/shared-schema mutation.

## Risks
- synthetic tail fingerprints are low-dimensional compared with real financial tails
- kurtosis/high quantiles are unstable in small samples
- age decay can incorrectly suppress genuine long-cycle recurrence
- fresh-probe gating can lower true recurrence coverage
- multi-horizon veto can delay legitimate propagation
- contamination can be hidden rather than explicit
- delayed rollback still incurs damage before revocation
- thresholds can overfit replay and inherit multiplicity debt

## Next
VECTOR Recurrence Evidence Sufficiency, Tail-Estimator Stability & Multi-Horizon Revalidation Lab.
Stress small-sample tail estimates, rare-event scarcity, horizon-specific delays, recurrence evidence ESS, and whether strong reuse should require sequential evidence accumulation rather than one fresh probe.

## Exact resume
1. Keep Adversarial Router Lab as promotion baseline.
2. Load v30-v31; do not restart.
3. Attempt exact first-party Deep Research first.
4. Stress recurrence evidence sufficiency and tail-estimator stability under delayed multi-horizon labels.
5. Preserve CHPD/CEF, all freshness/multiplicity/ambiguity controls, horizon ownership, prototype quarantine and reversible MERGE.
6. Similarity may nominate; only fresh independent evidence may increase authority.
7. No repo/live/sibling mutation until READY_TO_COMMIT gates pass.
