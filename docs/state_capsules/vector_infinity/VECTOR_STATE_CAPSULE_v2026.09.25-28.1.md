# VECTOR ∞ STATE CAPSULE — v2026.09.25-28.1

## Capsule correction note
v28.1 supersedes the v28 capsule TEXT because Drive persistence captured the pre-patch bytes before the critical negative-result section was added. The experiment/state evidence is unchanged; state SHA remains the same. v28 remains preserved for audit history and is not overwritten.

## Authoritative checkpoint
Promotion authority remains the Adversarial Router Lab. Immediate predecessor: v27 Structural-Loss Uncertainty & Robust Decision Lab. Offline/synthetic/shadow only.

## Cycle
Ambiguity-Set Calibration & Robustness Budget Lab.

## Verified synthetic evidence
- Exchangeable calibration: 7,000 episodes.
- Exchangeable evaluation: 12,000 episodes.
- Shift-shadow recalibration window: 2,500 episodes.
- Shifted evaluation: 9,000 episodes.
- Posterior uncertainty and structural-loss uncertainty were deliberately coupled: larger posterior error increased loss uncertainty.

### Marginal vs joint ambiguity coverage
- Posterior marginal 90% calibration → test coverage 90.325%.
- Loss marginal 90% calibration → test coverage 90.033%.
- Requiring BOTH separately calibrated 90% sets → joint coverage only 84.067%.
- Joint conformal calibration of max-normalized posterior/loss error → joint coverage 90.183%.
- Joint conformal radius multiplier: 1.0867.

### Robustness/conservativeness frontier
- Narrow 70% set: joint coverage 57.325%, authority coverage 0.000%, mean loss 1.0849, false-security authority outside set 0.000%.
- Marginal 90%-each set: joint coverage 84.067%, authority 0.000%, mean loss 1.0849.
- Joint-conformal 90% set: joint coverage 90.183%, authority 0.000%, mean loss 1.0849, catastrophic loss>=10 0.000%.
- Wide 99% set: joint coverage 98.217%, authority 0.000%, mean loss 1.0849.
- A synthetic authority-floor budget of 30% was tracked separately from statistical coverage; exact breaches are serialized and are not production thresholds.

### Regime-shift attack
- Reusing stale exchangeable radii after error scale increased: joint coverage collapsed to 38.500%; authority 0.000%; false-security authority outside set 0.000%.
- Fresh 2,500-episode shadow recalibration: shifted joint coverage recovered to 89.844%; authority 0.000%; false-security authority outside set 0.000%.

### Integrity / restart
- Deterministic stop→serialize→restore→continue cumulative-loss stream matched continuous execution bit-for-bit: True.
- NaN, negative, and infinite ambiguity radii rejected from authority: 100.0%.
- State SHA-256: 2a7ba810886bd9176bb481658079cba82662edc4fd1a77ef1349729f5c595841.
- Synthetic only; calibration target, authority floor, data-generating errors, radii and loss model are constructed and not production parameters.


## Critical negative result
The ambiguity-calibration layer succeeded statistically, but the current robust decision mapping FAILED the usefulness gate:
- every tested ambiguity width (70%, marginal-90%, joint-conformal-90%, 99%) selected ABSTAIN on 100% of exchangeable evaluation cases;
- stale and freshly recalibrated shifted cases also remained at 100% abstention;
- therefore the current worst-case upper-bound action rule breaches the synthetic 30% authority floor in every condition and is REJECTED as an authority policy.
- This does NOT invalidate the joint-coverage calibration result. It separates two components: ambiguity-set calibration survives as a research candidate; the tested robust-action mapping does not.
- No promotion credit is awarded for zero catastrophic losses obtained by zero useful authority.

## Architecture refinement
- AmbiguityCalibrationLedger (ACL): every posterior/loss ambiguity radius carries calibration population, target coverage, sample size, epoch, horizon/context, freshness, selection exposure and empirical realized coverage.
- JointCoverageCalibrator (JCC): correlated uncertainty dimensions are calibrated jointly; separate marginal 90% guarantees are not misrepresented as 90% joint protection.
- RobustnessBudgetController (RBC): robust-set coverage and useful decision authority are simultaneous constraints. The tested v28 worst-case upper-bound decision mapping violated this invariant and is rejected; RBC itself remains a governance requirement.
- AmbiguityDriftSentinel (ADS): realized set-coverage decay triggers authority reduction and fresh shadow recalibration; stale radii cannot retain permanent authority after regime change.
- FalseSecurityMonitor (FSM): tracks authority-bearing decisions made when realized truth falls outside the declared ambiguity set.
- Ambiguity-set geometry/radius tuning consumes multiplicity and freshness debt; post-selection recalibration on fresh evidence is required before authority.
- Requested-but-unobserved future outcomes are never counted as coverage successes.

## Research grounding
- 2026 Conformal-DRO constructs data-dependent ambiguity sets with finite-sample coverage under exchangeability.
- 2026 work unifying conformal prediction and Wasserstein DRO emphasizes that ambiguity-radius validity depends on calibration and distribution assumptions, and that tail behavior affects conservativeness.
- 2025 inverse conformal risk-control work explicitly targets the robustness-versus-conservativeness frontier instead of selecting robustness levels heuristically.
- 2026 decision-aware conformal-set research requires independent post-selection recalibration because learning set geometry and calibrating it on the same data can under-cover.

## Deep Research
DEEP RESEARCH ACTUALLY INVOKED = NO; DEEP RESEARCH UNAVAILABLE.
Exact plugin-directory search for “Deep Research” again returned research providers but no exact first-party Deep Research capability.

## Plugins/skills/tools actually used
- Superpowers using-superpowers
- Superpowers brainstorming
- Superpowers verification-before-completion
- Exa Search skill + dedicated ambiguity-calibration research
- Consensus academic search
- Scite literature search
- ordinary current web research
- isolated visible Python synthetic lab + artifact generation
- File Library / Google Drive persistence attempt

## Available but not materially invoked
- Codex Coordinator, Baton Pass, Akinator are installed, but no repository mutation or handoff occurred.

## Partially blocked
- real Icarus/VECTOR replay
- repository implementation and commit identity
- empirical ambiguity calibration from real market/shadow data
- real tail-event and regime-shift coverage
- forward-shadow/live evidence
- validated authority-floor and robustness-budget costs

## READY_TO_COMMIT
NO. No sibling/live/registry/execution/shared-schema mutation.

## Risks
- exchangeability-based calibration can fail under regime shift
- joint calibration becomes difficult in high-dimensional uncertainty spaces
- small calibration sets can make tail radii unstable
- authority floors can be gamed if chosen after replay
- false-security monitoring is delayed by outcome latency
- recalibration itself can overfit if the same shadow window selects geometry and radius
- rare catastrophic regimes may be absent from calibration entirely

## Next
VECTOR Online Ambiguity Calibration & Coverage-Control Lab.
Move from episodic recalibration to sequential coverage control with delayed labels, nonstationarity, rare-tail events, and bounded update cadence. Compare stale fixed radii, rolling quantiles, online conformal-style updates, and drift-triggered resets while preserving an explicit robustness/authority budget.

## Exact resume
1. Keep Adversarial Router Lab as promotion baseline.
2. Load v27-v28; do not restart.
3. Attempt exact first-party Deep Research first.
4. Stress online/sequential ambiguity calibration under delayed labels and nonstationary error distributions.
5. Preserve CHPD/CEF, DDE/DDS, DA-EIEC, CEG/CAA/CTC/CTL/LCB, SRP/SPC/DTAC/SFC/PSS, SLUS/RAA/MRC-R/RAB/LCIG and reversible MERGE.
6. Unknown/malformed/stale ambiguity state blocks confidence amplification but not observation/outcome learning.
7. No repo/live/sibling mutation until READY_TO_COMMIT gates pass.
