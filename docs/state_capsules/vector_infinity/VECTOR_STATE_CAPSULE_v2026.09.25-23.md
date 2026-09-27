# VECTOR ∞ STATE CAPSULE — v2026.09.25-23

## Authoritative checkpoint
Promotion authority remains the Adversarial Router Lab. Immediate predecessor: v22 Nonlinear/Lagged Dependence & Common-Cause Discovery. This cycle remains offline/synthetic/shadow only.

## Cycle
Dependency Multiplicity, Conditional Independence & Factor-Graph Lab.

## Verified synthetic evidence
Each scenario used 6,000 episodes of 300 observations; absolute dependence threshold = 0.20.

### Common-cause-only attack: Z→X, Z→Y, no X→Y
- Marginal association falsely implied direct/nonredundant dependence: 100.000%
- Conditioning on observed common cause Z: 0.000%

### Direct-plus-common-cause: Z→X, Z→Y and X→Y
- Marginal detection: 100.000%
- Conditional detection after controlling for Z: 100.000%

### Latent common cause with three noisy proxies
- Marginal false dependence: 100.000%
- Conditioning on averaged noisy factor proxy: 68.350%

### Collider trap: X→C←Y, X and Y otherwise independent
- Marginal false dependence: 0.083%
- False dependence after conditioning on collider C: 100.000%

- Deterministic checkpoint serialization restored byte-exact.
- State SHA-256: f9aa8e83c9890c988fc35c0bbcf010c760ccdbdfcb13a0a46e0936d45c02a4c0
- Synthetic only; graph forms, coefficients, threshold and proxy construction are deliberately chosen.

## Architectural refinement
- Add ConditionalEvidenceGraph (CEG): dependency authority is based on incremental information conditional on approved common-cause/context variables, not raw pairwise association alone.
- Add ConditioningSetRegistry (CSR): every conditioning set is versioned, provenance-linked and multiplicity-accounted; changing the set creates a new trial.
- Add ColliderGuard (CG): conditioning variables require structural admissibility checks; arbitrary conditioning can CREATE spurious dependence.
- Add LatentCommonCauseCandidate (LCCC): factor/common-cause proxies remain probabilistic candidates with uncertainty; proxy adjustment can reduce but not certify confounding removal.
- DependencyConfirmationGate remains mandatory: exploratory conditional edges have zero authority until chronologically/freshly confirmed.
- DA-EIEC consumes confirmed conditional dependency, not marginal correlation.
- Conditional independence does not establish causality by itself.

## Research grounding
- 2026 model-free conditional-independence testing for time series explicitly targets distinguishing causal effects from associations driven by common external processes.
- 2026 causal-dependence change detection conditions on confounders and warns that marginal distribution shifts can be mistaken for mechanism changes.
- 2026 asset-market research reports pervasive common latent factor structure across securities, supporting explicit common-cause/factor treatment.

## Deep Research
DEEP RESEARCH ACTUALLY INVOKED = NO; DEEP RESEARCH UNAVAILABLE.

## Plugins/skills/tools actually used
- Superpowers brainstorming skill
- Superpowers verification-before-completion skill
- Exa research provider
- ordinary fresh web research
- isolated visible Python synthetic lab + artifact generation
- File Library / Google Drive persistence attempt

## Available but not materially invoked
- Codex Coordinator, Baton Pass, Akinator are installed, but no repository mutation/handoff occurred in this cycle, so invoking their repo/handoff workflows would violate scope or add no evidence.

## Partially blocked
- real Icarus/VECTOR replay
- repository implementation and commit identity
- forward-shadow/live evidence
- real-market conditioning-set and latent-factor calibration
- causal identification beyond conditional dependence

## READY_TO_COMMIT
NO. No sibling/live/registry/execution/shared-schema mutation.

## Risks
- conditioning-set search creates multiplicity debt
- conditioning on colliders can manufacture dependence
- hidden confounders remain possible
- noisy factor proxies can incompletely remove common causes
- conditional tests may lose power in high dimensions
- factor/common-cause structure can drift across horizon/regime

## Next
VECTOR Conditioning-Set Governance & Hidden-Confounder Stress Lab.
Compare safe parent/context conditioning against naive all-variable conditioning, collider contamination, proxy quality decay, high-dimensional conditioning, factor rotation, and sequential multiplicity budgets. Add a Conditioning Admissibility Auditor and uncertainty-aware latent-confounder bounds.

## Exact resume
1. Keep Adversarial Router Lab as promotion baseline.
2. Load v22-v23; do not restart.
3. Attempt exact first-party Deep Research first.
4. Stress conditioning-set governance under hidden confounding/collider contamination.
5. Preserve CHPD/CEF, DDE/DDS, DA-EIEC, DependencyTrialLedger, horizon ownership and reversible MERGE.
6. Exploratory conditional/factor edges have zero authority.
7. No repo/live/sibling mutation until READY_TO_COMMIT gates pass.
