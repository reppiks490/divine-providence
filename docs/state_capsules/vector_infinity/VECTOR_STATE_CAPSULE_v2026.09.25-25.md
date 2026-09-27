# VECTOR ∞ STATE CAPSULE — v2026.09.25-25

## Authoritative checkpoint
Promotion authority remains the Adversarial Router Lab. Immediate predecessor: v24 Conditioning-Set Governance & Hidden-Confounder Stress Lab. Offline/synthetic/shadow only.

## Cycle
Conditioning Admissibility Under Structural Uncertainty Lab.

## Verified synthetic evidence
- 7,000 role-uncertainty episodes across confounder, mediator, collider, and irrelevant candidate roles.
- Role posteriors deliberately mixed clear/moderate/ambiguous evidence and included an explicit UNKNOWN probability mass.
- Hard MAP policy coverage: 100.000%; wrong conditioning decision: 5.243%; unsafe conditioning of mediator/collider: 1.929%.
- Probability-gated policy coverage: 41.586%; abstention: 58.414%; wrong decision among authority-bearing decisions: 0.206%; unsafe conditioning among authority-bearing decisions: 0.034%.

### Structural consequence probes
- True confounder, no direct X→Y: false dependence unconditioned 100.000%; after correct conditioning 0.521%.
- True collider, X and Y otherwise independent: false dependence unconditioned 0.550%; after unsafe collider conditioning 100.000%.
- True mediator for TOTAL-effect target: effect detection unconditioned 100.000%; after unsafe mediator conditioning 0.527%.

### Gradual confounder→collider rotation, 3,000 streams × 200 steps
- Stale fixed-conditioning policy unsafe post-switch: 100.000%.
- Adaptive hard-MAP unsafe post-switch: 2.005%.
- Probability-gated unsafe post-switch: 0.005%.
- Probability-gated policy retained authority on 33.809% of the deliberately ambiguous t=85..115 transition window; otherwise it abstained.

### Malformed-posterior attack
- Non-finite, negative, and non-normalized structural-role posteriors rejected from conditioning authority: 100.0%.

- Deterministic checkpoint serialization restored byte-exact.
- State SHA-256: e2474ec70ec0725fbb48a84adf79ac88f7a67e5f84156b6f7f8ac54092763536
- Synthetic only; posterior generator, thresholds, graph coefficients, costs and transition shape are deliberately constructed and are not production parameters.

## Architecture refinement
- StructuralRolePosterior (SRP): candidate variables carry probabilities over confounder, mediator, collider, irrelevant, and unknown roles rather than one hard label.
- ProbabilisticConditioningGate (PCG): conditioning authority requires sufficient confounder probability plus bounded mediator/collider/unknown risk; ambiguous cases abstain.
- AdjustmentRiskBudget (ARB): expected structural harm from conditioning is budgeted separately from statistical confidence. Higher uncertainty lowers allowed conditioning authority.
- UnknownStructureAbstention (USA): unknown/invalid structural state preserves the local claim but blocks confidence amplification from adjustment.
- RolePosteriorDriftSentinel (RPDS): detects role-distribution change; old structural roles lose authority during gradual factor/graph rotation.
- Target semantics remain binding: the same variable can be admissible for a direct-effect question and inadmissible for a total-effect question.
- Structural uncertainty is propagated into DA-EIEC/CEG rather than collapsed before evidence aggregation.

## Research grounding
- 2026 probabilistic ancestral-graph work represents uncertainty as a distribution over ancestral graphs under latent confounding instead of one deterministic graph.
- 2025/2026 PAG research emphasizes that latent confounding often leaves causal orientations indeterminate and that adjustment must respect the equivalence class rather than assume one DAG.
- 2026 stationary-time-series work shows collider structure governs conditional-independence separation.
- Recent adjustment-set work reiterates that mediators/colliders can bias or change the estimand when indiscriminately adjusted.

## Deep Research
DEEP RESEARCH ACTUALLY INVOKED = NO; DEEP RESEARCH UNAVAILABLE.
Exact plugin-directory search for “Deep Research” returned Exa, Scite, Consensus, Tavily and Parallel Search but no exact first-party Deep Research capability.

## Plugins/skills/tools actually used
- Superpowers using-superpowers
- Superpowers brainstorming
- Superpowers verification-before-completion
- Exa Search skill + 3 Exa research workstreams
- Consensus academic search
- Scite literature search
- ordinary current web research
- isolated visible Python synthetic lab + artifact generation
- File Library / Google Drive persistence attempt

## Available but not materially invoked
- Codex Coordinator, Baton Pass, Akinator: installed but this cycle performed no repository mutation or handoff. Their repo workflows were not needed to generate evidence and were not invoked.

## Partially blocked
- real Icarus/VECTOR replay
- repository implementation + commit identity
- real-market calibration of structural-role posteriors
- forward-shadow/live evidence
- validated adjustment-risk costs
- causal identification beyond observational equivalence classes

## READY_TO_COMMIT
NO. No sibling/live/registry/execution/shared-schema mutation.

## Risks
- posterior probabilities may be miscalibrated
- graph-equivalence uncertainty can be wider than five role classes
- ambiguous-role abstention can reduce coverage materially
- a low collider probability can still carry high harm
- gradual structural changes can outrun the drift sentinel
- hidden variables can invalidate apparent role posteriors
- target-semantic mistakes remain dangerous

## Next
VECTOR Structural-Posterior Calibration & Decision-Theoretic Adjustment Lab.
Calibrate role probabilities under class imbalance and regime drift; replace hand-set probability gates with bounded-loss decisions; test posterior miscalibration, rare high-cost colliders, unknown-role mass, and selective-label feedback.

## Exact resume
1. Keep Adversarial Router Lab as promotion baseline.
2. Load v24-v25; do not restart.
3. Attempt exact first-party Deep Research first.
4. Stress posterior calibration and decision loss under rare/high-cost structural roles.
5. Preserve CHPD/CEF, DDE/DDS, DA-EIEC, CEG/CAA/CTC/CTL/LCB, horizon ownership and reversible MERGE.
6. Unknown or malformed structural state blocks conditioning authority but not local observation/outcome learning.
7. No repo/live/sibling mutation until READY_TO_COMMIT gates pass.
