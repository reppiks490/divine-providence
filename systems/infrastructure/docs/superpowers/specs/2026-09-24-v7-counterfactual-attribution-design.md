# Infrastructure Supervisory Loop V7 — Counterfactual Attribution Design

Status: REVIEWED DESIGN CHECKPOINT — NOT IMPLEMENTED
Date: 2026-09-24

## Intent and success criteria

V7 constrains positive learning credit using counterfactual evidence. It does not add mutation authority. Success means coincidental recovery, contaminated controls, weak telemetry, or insufficient evidence cannot teach OutcomeMemory that an intervention caused improvement, while negative evidence remains learnable.

The invariant is: uncertainty may reduce learning credit; it may never manufacture mutation authority, telemetry confidence, canary promotion authority, or sibling-system authority.

## Existing verified chain

dependency graph → blast-radius governor → process-local mutation leases → staged-canary interface → promotion/rollback verification → proof integrity → conservative causal-learning eligibility.

V7 extends only the learning-evidence boundary.

## Non-goals

No distributed leases, production canary backend, dynamic topology discovery, cryptographic identity/signatures, Bayesian causal graph, reinforcement-learning policy authority, automatic control selection, or cross-sibling mutation authority.

Central Orchestration P0 Proof-Carrying Handoff Transport/recovery remains an external contract. V7 may emit transportable evidence later but does not own transport, recovery, signing, identity, replay, or orchestration policy.

## Data model

### Sample

Immutable `(timestamp, score, confidence)` observation. Timestamps are monotonic within a series. Scores use the existing normalized health range. Confidence is current observation quality only and is never raised by historical learning.

### AttributionObservation

Immutable record containing treated component, action fingerprint, intervention timestamp, pre/post windows, optional explicit control component and control windows, relevant mutation-event identifiers, relevant lease/failure-domain scopes, source confidence, and evidence timestamps.

Controls are supplied by an operator/adapter or an already-authorized matching layer. V7 never invents or silently substitutes a control.

### AttributionResult

Contains `observed_delta`, `counterfactual_delta`, `attributable_delta`, `attribution_confidence`, `evidence_method`, `contaminated`, ordered reason codes, and `evidence_hash`.

`attributable_delta = observed_delta - counterfactual_delta`.

Canonical evidence hashing uses deterministic JSON: UTF-8, sorted keys, compact separators, finite numeric values only, timestamps serialized in one documented representation, and the hash field omitted from its own preimage.

## Counterfactual estimation

V7 uses deterministic conservative methods in priority order.

1. **Explicit matched control.** If a valid uncontaminated control is supplied with sufficient aligned samples, its pre/post change is the counterfactual delta.
2. **Local pre-trend fallback.** If no control is supplied, sufficiently stable treated pre-history may project the untreated delta across the post window. The fallback receives lower maximum attribution confidence than an explicit valid control.
3. **Insufficient evidence.** Otherwise no counterfactual is produced and positive learning credit is denied.

No method selection is based on which method gives the action more credit.

## Window semantics

The intervention instant divides pre and post evidence. Pre samples must precede staging; post samples used for attribution must follow staging and fall within the bounded verification window. Samples outside the configured horizon are ignored. Missing or non-monotonic timestamps invalidate the affected evidence path.

The first implementation uses counts and durations from configuration rather than adaptive windows. Defaults are conservative and remain learning-only knobs; changing them cannot relax ActionGuard or topology policy.

## Contamination model

Evidence is contaminated if any of these apply during the relevant attribution window:

- the control is mutated;
- treated/control components overlap another relevant high-impact mutation;
- an active mutation event intersects a shared protected lease/failure-domain/redundancy scope;
- telemetry confidence falls below the attribution floor;
- samples are missing, non-monotonic, or temporally incompatible;
- control identity changes mid-window;
- proof integrity fails.

Contamination is monotonic for the result: once established, later favorable samples do not clear it. A new clean observation window is required.

## Attribution confidence

Confidence is evidence quality, not action confidence. The first implementation computes it from deterministic penalties applied to the minimum source confidence, sample sufficiency, temporal alignment, and method quality. It is clamped to `[0,1]` and cannot exceed the minimum current evidence confidence contributing to the result. The local-trend fallback has a lower configured ceiling than an explicit control.

Historical success, OutcomeMemory priors, action expected gain, or canary promotion never increase attribution confidence.

## Positive and negative learning rules

Positive gain is admitted only when all are true:

- upstream V6 result is causal-eligible;
- canary proof integrity is valid when a canary proof is required;
- evidence is uncontaminated;
- minimum evidence count/duration is satisfied;
- `attributable_delta > minimum_attributable_delta`;
- `attribution_confidence >= minimum_attribution_confidence`;
- a non-empty evidence hash is present.

If any condition fails, positive learned gain is zero. The action may still be journaled.

Negative attributable outcomes and execution failures remain eligible to reduce learned utility. Lack of positive causal evidence must never erase observed failure evidence.

## Failure posture

Attribution is fail-closed for positive learning and fail-open for target infrastructure. An exception, timeout, malformed observation, unavailable control, or estimator failure yields no positive credit and cannot crash the supervisor's observation loop or authorize a mutation.

## Integration boundary

`OutcomeMemory` consumes an attribution decision; it does not estimate counterfactuals. `ActionGuard`, `BlastRadiusGovernor`, leases, and canary promotion remain upstream and unchanged. Attribution code has no callback capable of mutating those authorization decisions.

The journal records the attribution method, reason codes, contamination state, confidence, evidence hash, and whether positive learning was admitted. Raw high-cardinality telemetry need not be embedded in the main journal; evidence retention can be adapter-specific while the hash preserves linkage.

## Compatibility and migration

Existing V6 actions without V7 attribution evidence remain executable under existing authorization rules but receive no new positive OutcomeMemory credit once V7 learning gating is enabled. This intentionally biases migration toward under-learning rather than grandfathering unproven positive history.

V6 stored history is not retroactively promoted to causally attributed history. Existing negative history may remain usable because V7 does not suppress failure evidence.

## Test matrix

1. Treated and explicit control recover equally → zero positive credit.
2. Treated improvement materially exceeds stable control → positive attribution.
3. Control mutated inside window → contaminated, zero positive credit.
4. Shared protected-scope mutation overlaps window → contaminated.
5. No control + stable sufficient pre-trend → conservative fallback eligible.
6. No control + insufficient/unstable history → insufficient evidence.
7. Low telemetry confidence → zero positive credit.
8. Non-monotonic or incompatible timestamps → zero positive credit.
9. Tampered canary proof → zero positive credit.
10. Negative attributable outcome → negative evidence remains learnable.
11. Attribution evidence cannot increase ActionGuard confidence.
12. Attribution evidence cannot override topology/authority denial.
13. Estimator exception → observation loop survives; no positive credit.
14. Favorable later sample cannot clear contamination in same result.
15. Canonical evidence serialization is stable across key ordering.
16. V6 positive result without V7 attribution → no positive credit after V7 gate enabled.

## Alternatives considered

**Post-action delta only:** rejected because environmental recovery can masquerade as intervention effect.

**Automatic nearest-neighbor control discovery in V7:** rejected because control selection itself is a substantial causal subsystem and can introduce hidden authority/selection bias.

**Full causal graph/Bayesian model now:** rejected as premature; it would combine topology learning, causal inference, and policy adaptation before the deterministic safety contract is proven.

## Security and safety invariants

- Attribution never grants mutation authority.
- Historical evidence never raises current telemetry confidence.
- Unknown/contaminated evidence cannot earn positive credit.
- Proof hashes are integrity links, not signatures or identity claims.
- Sibling-system ownership remains external and explicit.
- V3–V6 safety gates are not weakened or bypassed.

## Stale when

Revisit when distributed mutation coordination, a production canary backend, dynamic topology discovery, signed/attested proofs, automatic control matching, or a materially different learner is introduced.
