# ATHENA SUPERVISORY FABRIC — BLUEPRINT

## Mission
ATHENA is the state-aware, uncertainty-aware supervisor above DAEDALUS, ARGUS, and Icarus. It does not replace them. It turns validated research and live telemetry into an advisory view of **what world the system is in, which validated experts fit that world, how uncertain that judgment is, what counterfactuals threaten it, and when to abstain**.

## Core capability stack

1. **Append-only event/state fabric** with event-time vs ingestion-time, source/representation lineage, plane labels, and source-local sequence numbers for repeated timestamps.
2. **Dynamic market state graph** with instruments, factors, volatility, rates, chart representations, validated candidates, ARGUS microstructure nodes, and Icarus strategy/execution agents. Edges are time-versioned and uncertainty-bearing.
3. **Latent world-state engine** beginning with interpretable HMM/semi-Markov/state-space baselines, then boosted transition models, then temporal deep models only if they beat baselines out of sample. Outputs state embedding, transition probabilities, duration, entropy, OOD and confidence.
4. **Uncertainty decomposition**: aleatoric, epistemic, distributional/OOD, expert disagreement. Add calibration, conformal risk controls, ensemble dispersion, residual-shift diagnostics.
5. **Contextual expert router** over DAEDALUS-approved candidates and ARGUS microstructure experts. Maintain competence surfaces by regime/state, horizon, costs, OOD sensitivity and recent shadow health.
6. **Counterfactual market digital twin** for volatility shocks, correlation breaks, latency, slippage, liquidity drought, stale/missing sources, expert failure, rapid state transitions, and cross-asset inversions. Synthetic evidence is stress evidence only.
7. **Scenario/shock library** with deterministic versioned scenarios and expected invariants.
8. **Active research scheduler** ranking what DAEDALUS should research next by expected information gain, evidence deficit, regime coverage gap and compute cost—without contaminating DAEDALUS holdouts.
9. **Mechanism/invariance graph** for causal skepticism across time, regimes, instruments, representations, proxy removal and lag perturbation. Never call association causal without identification assumptions.
10. **Whole-stack advisory risk governor** that can reduce risk or abstain based on OOD, uncertainty, disagreement, data quality, counterfactual fragility and execution health.
11. **Champion/challenger lifecycle** that coordinates shadow deployment and degradation without rewriting historical evidence.
12. **Observability/lineage plane** linking every advisory to source versions, expert versions, scenario versions and evidence manifests.

## Build phases

- **Phase 0 — contracts/firewalls:** schemas, lineage, data-plane separation, no ML. The starter code in this ZIP implements this foundation.
- **Phase 1 — state graph + interpretable transition baselines:** build graph snapshots; HMM/semi-Markov/state-space baselines; calibrated state probabilities.
- **Phase 2 — uncertainty + OOD:** conformal/calibration suite, ensemble epistemics, distribution shift, abstention policy.
- **Phase 3 — expert competence router:** state-conditioned expert surfaces, frozen routing experiments, shadow-only advisories.
- **Phase 4 — digital twin:** replay + deterministic shocks + learned transition simulation. Never certify edge on synthetic data.
- **Phase 5 — active research scheduler:** issue research requests to DAEDALUS without holdout access.
- **Phase 6 — Icarus advisory integration:** signed/versioned advisory contract only; Icarus remains execution authority.

## Release gates
Every phase requires invariant tests for plane separation, provenance, no live-order authority, deterministic replay, calibration, OOD behavior, abstention, and no DAEDALUS holdout leakage.
