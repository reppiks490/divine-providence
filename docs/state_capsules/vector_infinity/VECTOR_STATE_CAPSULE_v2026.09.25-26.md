# VECTOR ∞ STATE CAPSULE — v2026.09.25-26

## Authoritative checkpoint
Promotion authority remains the Adversarial Router Lab. Immediate predecessor: v25 Conditioning Admissibility Under Structural Uncertainty. Offline/synthetic/shadow only.

## Cycle
Structural-Posterior Calibration & Decision-Theoretic Adjustment Lab.

## Verified synthetic evidence
Source calibration: 9,000 labeled synthetic structural-role cases.
Shift adaptation: 5,000 cases.
Shift evaluation: 14,000 cases.
Role priors changed from source [0.32, 0.2, 0.05, 0.38, 0.05] to shifted [0.22, 0.18, 0.15, 0.37, 0.08], with collider frequency increasing 5%→15% and unknown 5%→8%.

### Calibration
- Fitted scalar temperature T=0.900 on source calibration data.
- Source raw NLL 0.4973, Brier 0.2528, ECE 0.0254.
- Source temperature-scaled NLL 0.4947, Brier 0.2519, ECE 0.0094.
- Shift raw NLL 0.6515, Brier 0.3245, ECE 0.0163.
- Shift temperature-scaled NLL 0.6597, Brier 0.3261, ECE 0.0302.
Temperature scaling is a challenger, not promoted merely for improving one calibration metric.

### Decision policies under shifted priors
- Cost-blind MAP/raw mean realized loss: 1.3554; collider unsafe conditioning 17.422%; coverage 100.000%.
- v25 hand gate on temperature-scaled posterior: loss 0.7823; collider unsafe conditioning 7.303%; coverage 74.486%.
- Expected-loss/raw posterior: loss 0.5437; collider unsafe conditioning 2.148%; coverage 71.457%.
- Expected-loss/temperature-scaled: loss 0.5734; collider unsafe conditioning 3.055%; coverage 74.207%.
- Expected-loss/temp + naive selectively observed prior: loss 0.5065; coverage 76.064%.
- Expected-loss/temp + IPW feedback-corrected prior: loss 0.5102; collider unsafe conditioning 1.050%; coverage 72.829%.
- Expected-loss/temp + true adaptation-window prior (oracle benchmark): loss 0.5092; coverage 72.829%.

### Selective-feedback bias
- Only 73.640% of adaptation labels were observed under decision-dependent logging.
- Naive observed-prior L1 error vs full adaptation prior: 0.1226.
- Inverse-propensity-corrected prior L1 error: 0.0181.
Requested-but-unobserved labels are not treated as evidence.

### Rare high-cost collider stress
Conditioning-on-collider loss was varied from 10→80 while all posterior evidence stayed fixed. The decision controller changed authority/coverage as cost changed rather than treating one probability threshold as universal. Exact per-cost results are serialized in the state.

- Deterministic checkpoint serialization restored byte-exact.
- State SHA-256: 0b3db7952cc1b4aec35ec960b129aa1f54357d0048d00d1a1f80e3d5b12f1f25
- Synthetic only; logits, priors, loss matrix, observation propensities and cost values are constructed, not production parameters.

## Architecture refinement
- StructuralPosteriorCalibrator (SPC): calibration is versioned by context/horizon/regime and evaluated with NLL, Brier, class-wise/top-label calibration and rare-role diagnostics.
- DecisionTheoreticAdjustmentController (DTAC): chooses CONDITION / DO_NOT_CONDITION / ABSTAIN by expected structural loss, not maximum posterior class or one hard probability threshold.
- StructuralLossContract (SLC): costs are explicit, versioned, target-semantic-specific and cannot be silently changed to improve results. Rare collider harm may outweigh common low-cost errors.
- SelectiveFeedbackCorrector (SFC): calibration/base-rate updates account for decision-dependent label observation using bounded propensity correction, ESS and positivity checks.
- PriorShiftSentinel (PSS): changing structural-role base rates trigger recalibration/prior adaptation; source-calibrated posteriors do not retain permanent authority.
- Calibration improvement does not by itself imply decision improvement; promotion evaluates both probability quality and realized structural loss.
- Unknown-role probability remains explicit and can make abstention optimal.

## Research grounding
- 2024 LaSCal shows calibration can degrade under label shift and develops label-shift-aware calibration rather than assuming source calibration transfers.
- Selective-classification research under distribution shift treats coverage and selection risk jointly and warns that ordinary softmax confidence can be unreliable under shift.
- Recent cost-sensitive/selective work supports explicit expected-loss or reject-option decisions for asymmetric errors rather than accuracy-only optimization.

## Deep Research
DEEP RESEARCH ACTUALLY INVOKED = NO; DEEP RESEARCH UNAVAILABLE.
Exact plugin-directory search for “Deep Research” again returned installed research providers but no exact first-party Deep Research capability.

## Plugins/skills/tools actually used
- Superpowers using-superpowers
- Superpowers brainstorming
- Superpowers verification-before-completion
- Exa Search skill + 3 research workstreams
- Consensus academic search
- Scite literature search
- isolated visible Python synthetic lab + artifact generation
- File Library / Google Drive persistence attempt

## Available but not materially invoked
- Codex Coordinator, Baton Pass, Akinator are installed, but this cycle performed no repository mutation/handoff; invoking them would add no test evidence and could cross VECTOR ownership scope.

## Partially blocked
- real Icarus/VECTOR replay
- repository implementation and commit identity
- real-market calibration and structural loss elicitation
- forward-shadow/live evidence
- reliable target-domain label-shift estimation without oracle labels
- validated selective-feedback propensities

## READY_TO_COMMIT
NO. No sibling/live/registry/execution/shared-schema mutation.

## Risks
- calibration can fail differently by role even if top-label ECE improves
- loss-matrix misspecification can dominate posterior quality
- label shift may coexist with covariate/concept shift
- propensity correction can explode under poor positivity
- rare collider costs are difficult to estimate
- decision-dependent observation creates selective-label bias
- abstention can become avoidance if its cost is set too low

## Next
VECTOR Structural-Loss Uncertainty & Robust Decision Lab.
Treat loss entries themselves as uncertain intervals/distributions; compare nominal Bayes action, minimax regret, distributionally robust action and abstention. Stress simultaneous posterior miscalibration + loss misspecification + prior/concept drift.

## Exact resume
1. Keep Adversarial Router Lab as promotion baseline.
2. Load v25-v26; do not restart.
3. Attempt exact first-party Deep Research first.
4. Stress uncertain loss contracts and simultaneous posterior/prior drift.
5. Preserve CHPD/CEF, DDE/DDS, DA-EIEC, CEG/CAA/CTC/CTL/LCB, SRP/PCG/RPDS and reversible MERGE.
6. Calibration or cost updates cannot erase multiplicity/freshness/selective-label debt.
7. No repo/live/sibling mutation until READY_TO_COMMIT gates pass.
