# VECTOR ∞ STATE CAPSULE — v2026.09.25-32

## Authoritative checkpoint
Promotion authority remains the Adversarial Router Lab. Immediate predecessor: v31 Recurrent-Prototype Aging, Tail-Profile Matching & False-Recurrence Red-Team Lab. Offline/synthetic/shadow only.

## Cycle
Recurrence Evidence Sufficiency, Tail-Estimator Stability & Multi-Horizon Revalidation Lab.

## Deep Research status
DEEP RESEARCH ACTUALLY INVOKED = YES.
First-party Deep Research session was started for this target, but returned a rate-limited widget state and no completed report was available to this cycle. Independent literature research was therefore used fail-open; it is not substituted for the missing Deep Research report.

## Verified synthetic evidence

### Tail-estimator stability
Heavy-tailed reference distribution: |Student-t(df=3)|. Oracle values approximated from 1,000,000 draws.
- oracle q90=2.3481, q95=3.1780, ES95=5.0229
- 3,000 replications at each n in [20, 50, 100, 250].
{
  "20": {
    "q90_mae": 0.5611538450616316,
    "q95_mae": 0.895869704997676,
    "es95_mae": 2.1465940947278073,
    "hill_median": 2.1397041775596555,
    "hill_iqr": 1.442813194169731
  },
  "50": {
    "q90_mae": 0.36342095266860575,
    "q95_mae": 0.5915496977490454,
    "es95_mae": 1.399965605907848,
    "hill_median": 2.357935945049323,
    "hill_iqr": 1.1408807160169228
  },
  "100": {
    "q90_mae": 0.2556749730716762,
    "q95_mae": 0.42827882808622636,
    "es95_mae": 1.0733839230365791,
    "hill_median": 2.503041339338652,
    "hill_iqr": 1.022287269503407
  },
  "250": {
    "q90_mae": 0.16606108838944306,
    "q95_mae": 0.28381588385236006,
    "es95_mae": 0.7209403122713334,
    "hill_median": 2.6173576685482707,
    "hill_iqr": 0.8378847438675852
  }
}

Interpretation: high-tail features are highly sample-size-sensitive. Strong recurrence authority must not treat q95/ES/Hill estimates from n=20 as equivalent to n=250 evidence.

### Sequential fresh evidence under serial dependence
- 12 fresh probes per horizon; AR(1) dependence rho=0.65.
- True recurrence mean evidence 1H=0.72, 4H=0.68; false recurrence mean=0.
- 18% of true cases deliberately had 1H recurrence while 4H remained unconfirmed.
- Threshold score=2.0.
{
  "naive_1h": {
    "true_confirm_rate": 0.5931726907630522,
    "false_confirm_rate": 0.14894336432797972,
    "disagreement_strong_rate": 0.5945701357466063
  },
  "ess_adjusted_1h": {
    "true_confirm_rate": 0.3542168674698795,
    "false_confirm_rate": 0.0566356720202874,
    "disagreement_strong_rate": 0.34841628959276016
  },
  "ess_adjusted_multi_horizon": {
    "true_confirm_rate": 0.12248995983935743,
    "false_confirm_rate": 0.0040574809805579036,
    "disagreement_strong_rate": 0.026244343891402715
  },
  "multi_horizon_sequential": {
    "true_confirm_rate": 0.2178714859437751,
    "false_confirm_rate": 0.014877430262045646,
    "disagreement_strong_rate": 0.06334841628959276,
    "median_arrived_probe_count_true": 6.0,
    "median_confirmation_latency_true": 14.0
  }
}

### Dependence-adjusted effective sample size
{
  "4": {
    "mean_nominal_n": 4.0,
    "mean_estimated_ess": 2.9325601925179554,
    "p10_ess": 1.0,
    "p50_ess": 4.0
  },
  "6": {
    "mean_nominal_n": 6.0,
    "mean_estimated_ess": 3.9632606323354853,
    "p10_ess": 1.0,
    "p50_ess": 4.212495974844997
  },
  "8": {
    "mean_nominal_n": 8.0,
    "mean_estimated_ess": 4.633690095466671,
    "p10_ess": 1.3657181706563941,
    "p50_ess": 4.240067416735716
  },
  "12": {
    "mean_nominal_n": 12.0,
    "mean_estimated_ess": 5.642560175802742,
    "p10_ess": 1.9782202842997711,
    "p50_ess": 4.839253493540731
  }
}

### Circular-evidence / duplicate-root attack
{
  "nominal_claims": 12,
  "unique_roots": 8,
  "count_inflation": 1.5,
  "false_strong_naive": 0.1019,
  "false_strong_unique_root": 0.05,
  "false_strong_with_feedback_loop": 0.19485
}
Agreement from aliases/descendants is not independent evidence. Feedback-generated claims cannot create new root evidence.

## Core findings
- Small-n tail fingerprints are too unstable for strong reuse by themselves; sample size/ESS must govern which tail estimators can carry authority.
- Serially dependent fresh probes inflate apparent evidence if nominal n is treated as independent n.
- Dependence-adjusted ESS reduces false strong recurrence but also lowers true-confirmation coverage; evidence sufficiency is an authority tradeoff, not a cosmetic correction.
- Multi-horizon strong reuse is stricter than 1H-only reuse and correctly blocks cases where 1H recurs but 4H remains unconfirmed.
- Higher-horizon delay increases confirmation latency; pending 4H evidence cannot be borrowed from 1H.
- Duplicate descendant claims and explicit feedback loops inflate naive evidence. Root-ID deduplication materially reduces false strong recurrence in the null attack.
- One fresh probe is insufficient. Strong reuse should require sequential accumulation of fresh, root-independent evidence with dependence-adjusted ESS.
- No higher horizon can retroactively certify a lower-horizon root that it consumed.

## Architecture refinement
- RecurrenceEvidenceAccumulator (REA): append-only fresh evidence by horizon, with source-event time, arrival time, root IDs, alias lineage, freshness, and consumption state.
- DependenceAdjustedFreshESS (DAF-ESS): converts nominal fresh probe count into effective independent support using serial-dependence and root-overlap corrections.
- TailEstimatorAuthorityTier (TEAT): tail estimators have sample-size/ESS-specific authority. Very small samples may inform shadow diagnostics but cannot independently promote strong reuse.
- MultiHorizonRevalidationLedger (MHRL): each horizon owns its revalidation state; higher horizons can veto propagation but cannot erase valid local recurrence.
- RootIndependentEvidenceGate (RIEG): only unique root evidence can raise recurrence authority; aliases, transforms, descendants, and feedback edges contribute zero incremental root count.
- SequentialStrongReuseGate (SSRG): STRONG_REUSE requires sufficient fresh ESS, horizon-specific confirmation, no circular provenance, and delayed evidence completion. Similarity and one-shot probes remain provisional.
- Pending/missing evidence remains non-evidence.
- Revalidation failure rolls back provisional reuse through existing tombstone/reversible-MERGE semantics.

## Literature-supported constraints
- Recurrent concept drift research supports reusing historical models only after fresh exchangeability/performance checks rather than unconditional reuse.
- Delayed-feedback adaptive conformal research shows delay cost depends on residual memory and provides finite-sample/long-run coverage analysis under delayed updates.
- Anytime-valid/conformal-martingale research supports sequential evidence accumulation without fixing one terminal sample size in advance.
- These results motivate but do not directly validate VECTOR's specific thresholds, ESS formula, tail tiers, or multi-horizon gate.

## Integrity
- Exact serialized checkpoint/restore: True.
- Malformed ESS/root-lineage states rejected from authority: 100.0%.
- State SHA-256: 2689cdd5935da5c49d46108c49559f1fa7636f76d49565d094950ceb81957dbd.
- Synthetic only. Distribution, thresholds, rho, delays, feature means, estimator tiers and sample sizes are experimental design choices, not production parameters.

## Plugins/skills/tools actually used
- first-party Deep Research App: INVOKED, report unavailable due rate-limit state
- Superpowers process skills
- Exa research
- Consensus academic search
- Scite literature search
- ordinary current web research
- isolated visible Python synthetic lab + artifact generation
- File Library / Google Drive persistence attempt

## Partially blocked
- completed first-party Deep Research report
- real Icarus/VECTOR replay
- repository implementation and commit identity
- market-calibrated tail-estimator uncertainty
- actual fresh-evidence dependence/ESS by horizon
- real root-provenance graph from Icarus
- forward-shadow/live evidence
- production-safe sequential thresholds

## READY_TO_COMMIT
NO. No sibling/live/registry/execution/shared-schema mutation.

## Risks
- ESS correction is model-dependent and can be wrong under nonlinear/long-memory dependence
- Hill/EVT estimators are threshold-sensitive and unstable with few extremes
- multi-horizon gating can over-delay genuine recurrence
- root identity may be incomplete or corrupted
- circular evidence can hide through transformations
- sequential thresholds can create multiplicity if tuned on replay
- tail scarcity can make strong-reuse evidence take too long to accumulate
- delayed rollback still incurs provisional damage

## Next
VECTOR Sequential Recurrence Evidence, Anytime-Validity & Root-Provenance Attack Lab.
Replace fixed terminal thresholds with governed sequential evidence/e-process candidates; attack optional stopping, adaptive probe selection, hidden alias roots, delayed horizon arrivals, and recurrence evidence starvation. Compare fixed-N, naive sequential, anytime-valid, and fresh-holdout confirmation.

## Exact resume
1. Keep Adversarial Router Lab as promotion baseline.
2. Load v31-v32; do not restart.
3. Attempt/continue exact first-party Deep Research first and record whether a report actually becomes available.
4. Stress optional stopping and adaptive probe selection with root-independent sequential evidence.
5. Preserve all provenance, CEF, freshness, multiplicity, tail-tier, horizon-ownership, quarantine and reversible-MERGE controls.
6. Similarity nominates only. STRONG_REUSE requires sequential fresh independent evidence.
7. No repo/live/sibling mutation until READY_TO_COMMIT gates pass.
