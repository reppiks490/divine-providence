# VECTOR ∞ STATE CAPSULE — v2026.09.25-24

## Authoritative checkpoint
Promotion authority remains the Adversarial Router Lab. Immediate predecessor: v23 Dependency Multiplicity, Conditional Independence & Factor-Graph Lab. Offline/synthetic/shadow only.

## Cycle
Conditioning-Set Governance & Hidden-Confounder Stress Lab.

## Verified synthetic evidence
Each scenario used 3,500 Monte Carlo episodes.

### Confounder + collider attack
No X→Y edge; Z→X,Y and X→C←Y.
- Marginal false dependence: 100.000%
- Approved conditioning on Z only: 0.600%
- Naive condition-on-everything (Z+C): 100.000%
- Data-mined best of admissible/unsafe candidate sets: 100.000%

### Mediator target-contract attack
True total path X→M→Y plus Z confounding.
- Total-effect detection conditioning on Z: 100.000%
- Detection after over-conditioning on mediator M: 0.600%

### Hidden-confounder proxy degradation
- Oracle conditioning on hidden H: 0.714% residual false dependence
- Good noisy proxy: 25.457%
- Bad noisy proxy: 100.000%

### High-dimensional over-conditioning
Weak true direct signal.
- Minimal/unconditioned detection: 90.114%
- Conditioning on 35 nuisance variables: 85.200%

### Factor-rotation attack
Common factor proxy changes at midpoint.
- Stale static proxy false residual dependence: 100.000%
- Epoch-aware proxy conditioning: 10.514%

### Conditioning-set search multiplicity
Independent X,Y; 12 candidate conditioning variables.
- Naive best-of-search false discovery: 7.200%
- Freeze winner then require split confirmation: 0.600%

- Deterministic checkpoint serialization restored byte-exact.
- State SHA-256: 22dd9f69a24ffc55905539c983a1472d5612a4df097d4ca145a22ae52e37babf
- Synthetic only; graph forms, thresholds, effect sizes, sample sizes and proxy construction are deliberately chosen.

## Architecture refinement
- ConditioningAdmissibilityAuditor (CAA): candidate conditioning variables are classified as approved context/parent, possible confounder, possible mediator, possible collider/descendant, nuisance, or unresolved. Unsafe/unresolved variables cannot silently enter an authority-bearing conditioning set.
- ConditionTargetContract (CTC): every test declares whether it targets total dependence, direct incremental dependence, predictive contribution, or another semantic. A mediator may be valid for a direct-effect question but invalid for a total-effect question.
- ConditioningTrialLedger (CTL): every searched conditioning set consumes multiplicity budget; changing a set creates a new trial and descendants inherit search debt.
- LatentConfounderBound (LCB): proxy adjustment reduces confounding uncertainty but never certifies its removal. Residual-confounding bounds widen as proxy quality/support deteriorates.
- FactorEpochBinding: conditioning/factor models are bound to dependency epochs; stale factor proxies cannot retain full authority after rotation/drift.
- High-dimensional conditioning receives an information-cost/power penalty and requires evidence that added variables reduce bias rather than merely add variance.
- Exploratory conditioning-set discoveries have zero authority until chronologically/freshly confirmed.

## Research grounding
- 2026 PMLR work establishes that collider structure governs cross-sectional conditional-independence separation in stationary time series.
- 2026 adaptive MCI research shows conditioning-set choice must change with causal/autocorrelation structure and that confounders must be retained.
- 2026 model-free time-series CI work conditions on histories/confounders to distinguish direct temporal contribution from common external processes.
- 2025/2026 latent-confounding work shows pervasive and localized hidden factors can both create misleading observed dependence.

## Deep Research
DEEP RESEARCH ACTUALLY INVOKED = NO; DEEP RESEARCH UNAVAILABLE.
Plugin-directory search for “Deep Research” returned research plugins (Exa, Scite, Consensus, Tavily, Parallel Search) but no exact first-party Deep Research capability.

## Plugins/skills/tools actually used
- Superpowers using-superpowers
- Superpowers brainstorming
- Superpowers dispatching-parallel-agents guidance
- Superpowers verification-before-completion
- Exa Search skill + Exa research provider
- Consensus academic search
- Scite literature search
- ordinary current web research
- isolated visible Python Monte Carlo and artifact generation
- File Library / Google Drive persistence (pending verification at capsule creation)

## Available but not materially invoked
- Codex Coordinator, Baton Pass, Akinator: installed, but this cycle made no repository mutation or handoff; invoking their repo workflows would add no evidence and could violate VECTOR ownership scope.

## Partially blocked
- real Icarus/VECTOR replay
- repository implementation and commit identity
- forward-shadow/live evidence
- real-market conditioning-set calibration
- validated latent-confounder bounds
- causal identification beyond observational conditional-dependence evidence

## READY_TO_COMMIT
NO. No sibling/live/registry/execution/shared-schema mutation.

## Risks
- admissibility classification can itself be wrong
- hidden colliders/confounders remain possible
- target-contract mistakes can turn correct math into wrong semantics
- high-dimensional CI loses power
- proxy-quality scores can be miscalibrated
- factor epochs can rotate gradually rather than abruptly
- conditioning-set multiplicity can explode combinatorially
- conditional independence is not proof of causality

## Next
VECTOR Conditioning Admissibility Under Structural Uncertainty Lab.
Represent uncertain graph roles probabilistically rather than as hard confounder/mediator/collider labels. Stress partial ancestral graphs, ambiguous edge orientation, gradual factor rotation, missing variables, and decision rules for when uncertainty is too high to condition at all.

## Exact resume
1. Keep Adversarial Router Lab as promotion baseline.
2. Load v23-v24; do not restart.
3. Attempt exact first-party Deep Research first.
4. Stress probabilistic conditioning admissibility under ambiguous graph structure.
5. Preserve CHPD/CEF, DDE/DDS, DA-EIEC, CEG/CSR/CG, DependencyTrialLedger, horizon ownership and reversible MERGE.
6. Exploratory conditioning/common-cause edges have zero authority.
7. No repo/live/sibling mutation until READY_TO_COMMIT gates pass.
