# ATHENA World Model & Supervisory Intelligence Fabric

## Purpose

ATHENA is the recommended system-level complement to DAEDALUS Research OS and Icarus.

It is **not another signal generator, strategy, backtester, or model foundry**. DAEDALUS already owns research discovery and evidence validation; Icarus owns trading logic/execution. ATHENA should sit above and beside both systems as an independent supervisory intelligence fabric.

Its job is to answer a different class of questions:

- What market state are we actually in now?
- Which previously validated models are appropriate for this state?
- How uncertain is that assessment?
- What happens under plausible counterfactual states, shocks, latency, slippage, and liquidity conditions?
- Are DAEDALUS candidates decaying, becoming out-of-distribution, or entering a state in which they were never validated?
- Should the system increase confidence, reduce exposure, abstain, or request new research?
- Which new research experiment has the highest expected information value per unit of compute and protected evidence?

The objective is not to make historical PnL larger. The objective is to make the entire research-to-execution stack **state-aware, uncertainty-aware, counterfactual, auditable, and capable of abstention**.

## Preferred placement

```text
<workspace-root>/
  Icarus/                       # execution/trading system
  Icarus-engine/                # existing engine repo
  multi-level-csv/              # authoritative historical corpus
  daedalus-research-os/         # research/discovery/validation
  athena-supervisory-fabric/    # NEW sibling system
```

Do not implement ATHENA inside DAEDALUS or Icarus initially. Isolation is a feature: it protects DAEDALUS's research protocol and Icarus's production path.

## System boundaries

### DAEDALUS owns

- immutable source catalog and chart-representation provenance
- causal feature construction
- development-only hypothesis discovery
- model-family comparison
- frozen development ensembles
- purged/embargoed validation
- protected-holdout ledger and budget
- adversarial robustness testing
- local/global FDR
- research promotion gates
- experiment memory/graveyard
- shadow evidence collection
- research-only candidate manifests

### Icarus owns

- production-safe market inputs
- strategy/decision logic approved for production
- broker/execution integration
- position and order state
- execution telemetry
- realized fills, slippage, latency, and operational health
- production risk enforcement

### ATHENA owns

- cross-system state representation
- market/world-state graph
- distribution-shift and state-transition intelligence
- uncertainty decomposition and calibration
- contextual model suitability/routing
- counterfactual digital-twin simulation
- scenario/shock library
- active research scheduling / value-of-information ranking
- global advisory risk envelope and abstention logic
- whole-stack lineage/observability
- champion/challenger coordination

ATHENA must not silently inherit ownership of DAEDALUS holdout selection or Icarus order placement.

# 1. Event-sourced market-state fabric

Build a canonical, append-only event/state layer that can consume:

- execution-safe OHLCV/tick streams
- alternate chart representations
- cross-asset series
- DAEDALUS candidate predictions and uncertainty
- DAEDALUS regime/drift outputs
- Icarus intended actions
- Icarus fills and positions
- realized latency/slippage
- risk state
- optional macro/calendar/event context when a clean source exists

Every state snapshot must carry:

- event time
- ingestion time
- source fingerprint/version
- representation identity
- feature/model version
- data-quality flags
- lineage pointer

Never destroy repeated timestamps merely to create a unique time index. If ordering within identical timestamps is needed, create an explicit source-local sequence number.

# 2. Market State Graph

Represent the market as a dynamic graph instead of a flat indicator vector.

Example node classes:

- instruments
- sectors/factors
- volatility surfaces/proxies
- rates/yields
- currencies
- commodities
- chart representations
- validated DAEDALUS candidates
- Icarus strategy/execution agents

Example edges:

- rolling dependence
- lagged dependence
- conditional dependence
- divergence/convergence
- lead/lag stability
- regime-specific dependence
- shared volatility exposure
- common factor exposure

Edges must be time-versioned and uncertainty-bearing. Do not treat correlation as causation.

The state graph's purpose is to give ATHENA a structural representation of *how the system and market are connected now*.

# 3. World model / transition model

ATHENA should model transitions in a latent market state, not just next-bar direction.

Minimum outputs:

```text
current_state_id
state_embedding
P(next_state | current_state, context)
expected_state_duration
transition_entropy
OOD_score
state_confidence
```

Begin with interpretable baselines before deep sequence models:

1. Hidden/semi-Markov state model baseline
2. state-space / Kalman-family baseline where appropriate
3. gradient-boosted transition classifier
4. only then add temporal deep models if they produce verified incremental value

Deep models must compete against simple baselines under the same walk-forward and shadow protocol. Complexity receives no automatic promotion credit.

# 4. Uncertainty engine

Separate at least four concepts:

- **aleatoric uncertainty**: irreducible market randomness
- **epistemic uncertainty**: model ignorance / limited evidence
- **distributional uncertainty**: current state differs from training/support
- **system disagreement**: validated experts disagree

Candidate techniques:

- ensemble dispersion
- calibration curves / Brier decomposition
- conformal prediction intervals or conformal risk controls
- distance-to-training-distribution metrics
- residual shift detection
- representation disagreement

ATHENA's most important output may sometimes be **ABSTAIN**, not BUY/SELL.

# 5. Contextual expert router

Treat validated models/strategies as experts rather than forcing one universal champion.

For each expert maintain a state-conditioned competence profile:

```text
expert_id
supported_state_regions
unsupported_state_regions
calibration_by_state
expected_horizon
cost_sensitivity
turnover profile
recent shadow health
OOD sensitivity
failure modes
```

Router outputs should be advisory initially:

```text
expert_suitability_weights
ensemble_disagreement
routing_confidence
abstain_flag
reason_codes
```

The routing policy must be trained/frozen without leaking future production outcomes into historical claims.

# 6. Counterfactual Market Digital Twin

This is the highest-value capability missing from the current stack.

The digital twin should replay or synthesize plausible state evolutions while preserving realistic execution mechanics.

It must support questions such as:

- What if volatility doubles within N bars?
- What if NQ remains unchanged but VXN/TNX/DXY move into a historically rare configuration?
- What if signal latency increases by 250 ms / one bar?
- What if slippage doubles?
- What if liquidity thins while the model remains directionally correct?
- What if the current state transitions to each high-probability successor state?
- What if the apparent cross-asset relationship disappears?
- What if one expert goes offline or its calibration degrades?

The digital twin is not allowed to certify an edge by synthetic data alone. Synthetic/counterfactual results are **stress evidence**, not protected empirical evidence.

# 7. Scenario and shock library

Create deterministic, versioned stress scenarios:

- volatility shock
- gap/open discontinuity
- correlation breakdown
- cross-asset inversion
- liquidity drought
- spread/slippage expansion
- stale data
- delayed data
- missing source
- model disagreement spike
- rapid regime transition
- volatility compression -> expansion
- trend -> chop transition
- macro-factor shock

Each scenario should define invariants and expected system behavior. Example: a stale execution-safe price stream should force an advisory abstention regardless of model confidence.

# 8. Active Research Scheduler

ATHENA should help DAEDALUS decide *what to research next* without contaminating DAEDALUS's protected evidence.

Rank prospective research tasks by expected information value, for example:

```text
priority = expected_information_gain
           * strategic_relevance
           * regime_coverage_gap
           * evidence_deficit
           / estimated_compute_cost
```

Inputs can include:

- unrepresented market states
- recurrent live/shadow failure modes
- drift alerts
- expert disagreement regions
- sparse regime evidence
- chart representations not yet catalogued/validated
- candidates with promising development evidence but no holdout budget yet

**Critical firewall:** ATHENA may request research, but it must not feed protected-holdout outcomes back into the development feature/model search in a way that invalidates the holdout.

# 9. Causal skepticism / intervention graph

Build a separate mechanism graph describing hypotheses about stable relationships. Do not call them causal unless identification assumptions are defensible.

Use it to test invariance:

- across time
- across regimes
- across instruments
- across representations
- under proxy removal
- under lag perturbation

The goal is to identify relationships that are less likely to be accidental historical associations.

# 10. Whole-stack risk and abstention governor

ATHENA should produce an advisory risk envelope, not orders.

Possible output contract:

```json
{
  "state_id": "...",
  "state_confidence": 0.0,
  "ood_score": 0.0,
  "expert_weights": {},
  "uncertainty": {},
  "risk_multiplier": 0.0,
  "max_allowed_exposure": null,
  "abstain": true,
  "reason_codes": [],
  "counterfactual_risk": {},
  "evidence_version": "..."
}
```

Icarus remains the authority that applies or rejects this advisory contract until a future integration review explicitly changes ownership.

# 11. Feedback firewall

This is mandatory.

Separate the following data planes:

```text
RESEARCH PLANE
  DAEDALUS development data
  protected holdout ledger
  research experiments

SHADOW PLANE
  forward predictions
  non-production observation

PRODUCTION PLANE
  Icarus decisions/fills/positions
  operational telemetry
```

ATHENA may observe all three, but any model retraining or research request must record which plane supplied the information. Protected evidence must never silently become development data for the same claim.

# 12. Champion/challenger lifecycle

Every state model, router, uncertainty estimator, or scenario policy should have:

- immutable version
- training dataset lineage
- validation evidence
- shadow period
- promotion decision
- rollback target
- retirement reason

ATHENA itself should use the same scientific skepticism DAEDALUS applies to market models.

# 13. Observability and evidence graph

Every recommendation should be reconstructable:

```text
raw inputs
 -> state snapshot
 -> state model version
 -> candidate versions
 -> uncertainty estimators
 -> router version
 -> counterfactual scenarios
 -> advisory output
 -> Icarus response
 -> realized outcome
```

Store a hash/version for every step. A human or future AI should be able to answer, "Why did the stack believe this at this time?"

# 14. Suggested architecture

```text
                        +-------------------------+
                        |     ATHENA CONTROL      |
                        |       PLANE             |
                        +-----------+-------------+
                                    |
       +----------------------------+----------------------------+
       |                            |                            |
+------v------+              +------v------+              +------v------+
| Market      |              | World Model |              | Uncertainty |
| State Graph |              | / Digital   |              | + OOD       |
|             |              | Twin        |              | Engine      |
+------+------+              +------+------+              +------+------+ 
       |                            |                            |
       +----------------------------+----------------------------+
                                    |
                            +-------v--------+
                            | Expert Router  |
                            | + Abstention   |
                            +-------+--------+
                                    |
                     advisory only  |
             +----------------------+----------------------+
             |                                             |
      +------v------+                               +------v------+
      | DAEDALUS    |                               | ICARUS      |
      | Research OS |                               | Execution   |
      +-------------+                               +-------------+
```

# 15. Implementation phases

## Phase 0 — contracts and firewalls

Before ML:

- define schemas for DAEDALUS -> ATHENA and Icarus -> ATHENA
- define advisory-only ATHENA -> Icarus output
- define event/state versioning
- define data-plane labels
- define contamination rules
- define replay determinism requirements

Exit criterion: contract tests pass without either existing repo importing ATHENA.

## Phase 1 — observability/state store

- append-only event store
- deterministic state snapshots
- provenance graph
- data quality flags
- replay engine

Exit criterion: same event log produces byte-identical state snapshot hashes.

## Phase 2 — baseline state model

- interpretable state/clustering baseline
- state transition probabilities
- OOD detector
- uncertainty calibration

Exit criterion: walk-forward + shadow evidence beats naive baselines on predeclared metrics.

## Phase 3 — contextual router

- competence profiles for validated DAEDALUS/Icarus experts
- state-conditioned advisory weights
- abstention
- disagreement diagnostics

Exit criterion: router is no worse than equal-weight baseline under protected/shadow tests and meaningfully improves at least one predeclared robustness metric without worsening hard risk constraints.

## Phase 4 — digital twin

- deterministic scenario engine
- execution friction model
- state-transition counterfactuals
- shock library

Exit criterion: historical replay reproduces known outcomes within defined tolerances; synthetic scenarios are labeled stress-only.

## Phase 5 — active research scheduler

- research backlog
- information-value scoring
- compute budget
- DAEDALUS request API

Exit criterion: scheduler never spends protected evidence directly and every requested experiment has provenance/reason codes.

## Phase 6 — shadow integration

ATHENA observes real-time/shadow DAEDALUS/Icarus outputs and emits advisory state/risk/routing messages only.

No live order authority.

# 16. Tests that are mandatory

- deterministic replay test
- event-ordering test
- repeated-timestamp preservation test
- source-lineage integrity test
- research/shadow/production plane firewall test
- protected-holdout contamination test
- state-model walk-forward test
- OOD abstention test
- model disagreement abstention test
- stale-data abstention test
- missing-source degradation test
- counterfactual determinism test
- scenario-label test (synthetic != empirical evidence)
- router equal-weight baseline test
- expert retirement/rollback test
- advisory contract schema test
- Icarus no-direct-order-authority test

# 17. What would make ATHENA genuinely valuable

The benefit is not simply more models. The benefit is that DAEDALUS and Icarus become parts of a larger adaptive system with explicit epistemic limits.

DAEDALUS answers: **What survived rigorous research?**

Icarus answers: **What can be executed safely?**

ATHENA answers: **Which validated capability is appropriate now, how uncertain are we, what breaks it, and when should the entire stack refuse to act?**

That is the missing system-level capability.
