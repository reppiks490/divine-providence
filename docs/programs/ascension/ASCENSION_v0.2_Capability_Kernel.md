# ASCENSION ∞ — Capability Kernel v0.2

## Purpose

ASCENSION ∞ is a **non-authoritative capability amplifier** for a multi-agent ecosystem. It does not own sibling systems, overwrite their state, or silently alter their behavior. Its job is to discover, validate, package, and hand off reusable capability improvements that other systems may adopt through explicit contracts.

This kernel converts the loop from a recurring prompt into a repeatable capability-development process.

---

## 1. Core Operating Model

Every ASCENSION cycle executes the same nine-stage pipeline:

1. **OBSERVE** — read the latest ASCENSION checkpoint, failures, measurements, rejected hypotheses, and known ecosystem constraints.
2. **MAP** — identify the highest-leverage capability gap and map dependencies, owners, collision risks, and potential beneficiaries.
3. **SYNTHESIZE** — generate multiple candidate improvements, favoring orthogonal improvements with reuse across multiple systems.
4. **ISOLATE** — place unproven ideas in shadow mode; define explicit interfaces and prohibit direct mutation of sibling authority/state.
5. **TEST** — build measurable acceptance tests, negative tests, regression tests, and adversarial failure cases.
6. **COMPARE** — evaluate challenger vs baseline using a multidimensional evidence vector rather than a single gameable score.
7. **PACKAGE** — emit a Capability Packet with contracts, evidence, rollback plan, tests, limitations, and adoption instructions.
8. **HANDOFF** — expose the packet as PROPOSED or VERIFIED; another system must explicitly adopt it before it becomes part of that system.
9. **LEARN** — write an Experience Capsule recording outcome, failure modes, confidence changes, and the next best experiment.

No cycle may skip directly from idea to adoption.

---

## 2. Capability Kernel Modules

### A. Opportunity Miner
Searches prior cycles for bottlenecks, repeated manual work, duplicated logic, blind spots, weak verification, costly context reconstruction, fragile interfaces, or missing reusable primitives.

Output:
- ranked capability gaps
- expected beneficiaries
- why now
- measurable success conditions

### B. Boundary & Dependency Mapper
Builds a temporary map of:
- system that owns the relevant responsibility
- systems that could consume the improvement
- inputs/outputs
- prohibited mutations
- version dependencies
- collision and duplication risks

Hard rule: **ownership remains with the sibling system.**

### C. Candidate Forge
Creates 2–5 materially different candidate designs when the problem is non-trivial.

Candidates must differ in mechanism, not merely wording.

### D. Experiment Forge
Turns candidates into isolated experiments with:
- baseline
- challenger
- test dataset or synthetic cases
- invariants
- negative controls
- failure injection
- acceptance thresholds
- rollback trigger

### E. Evaluator Mesh
Evaluates each candidate along separate axes:
- correctness
- reproducibility
- transferability
- integration cost
- latency/cost burden
- observability
- rollback safety
- non-interference
- evidence quality
- expected reuse breadth

ASCENSION must not collapse these into one “magic” score for promotion. Promotion requires all hard gates plus a Pareto-improving evidence profile.

### F. Capability Registry
Maintains lifecycle state:

`IDEA -> SHADOW -> CANDIDATE -> VERIFIED -> OFFERED -> ADOPTED_EXTERNALLY -> DEPRECATED`

ASCENSION controls only states through `OFFERED`.
`ADOPTED_EXTERNALLY` must be confirmed by the consuming system or actual implementation evidence.

### G. Adoption Gateway
Defines a versioned handshake for other systems:

- capability_id
- interface_version
- required_inputs
- emitted_outputs
- assumptions
- invariants
- compatibility
- tests
- rollback
- evidence
- authority_boundary

No implicit integration is allowed.

### H. Regression Sentinel
Every verified Capability Packet carries a regression suite. If later evidence violates an invariant, the packet is downgraded or quarantined rather than silently retained.

### I. Compounding Planner
Selects the next experiment based on **marginal reusable leverage**:
- number of systems that could benefit
- depth of improvement
- confidence
- reuse probability
- integration friction
- non-interference risk

This is a prioritization signal only, not proof of value.

---

## 3. Promotion Gates

A capability cannot be marked VERIFIED unless it passes every hard gate:

1. **Evidence Gate** — measurable evidence exists.
2. **Reproduction Gate** — result can be repeated or independently checked.
3. **Boundary Gate** — does not seize authority from another system.
4. **Non-Interference Gate** — does not break unrelated consumers under defined tests.
5. **Rollback Gate** — explicit rollback or fail-open path exists.
6. **Observability Gate** — failures can be detected.
7. **Contract Gate** — versioned inputs/outputs and assumptions are documented.
8. **Transfer Gate** — at least one realistic consumer can use it without hidden shared state.
9. **Regression Gate** — a durable regression test accompanies the packet.

If any gate fails, status remains SHADOW or CANDIDATE.

---

## 4. Capability Packet

Every durable improvement is represented by a Capability Packet.

Minimum fields:

- `capability_id`
- `name`
- `version`
- `cycle_id`
- `status`
- `problem`
- `hypothesis`
- `beneficiaries`
- `authority_exclusions`
- `dependencies`
- `interfaces`
- `evidence`
- `evaluation_vector`
- `acceptance_tests`
- `negative_tests`
- `regression_tests`
- `failure_modes`
- `rollback`
- `observability`
- `compatibility`
- `artifacts`
- `revalidation`
- `next_experiment`

The companion JSON Schema is included as `ascension_capability_packet.schema.json`.

---

## 5. Experience Capsule

ASCENSION’s “self-learning” mechanism is explicit and inspectable. It does not imply model-weight training.

Each cycle writes:

- observation
- prior belief
- intervention
- measured outcome
- evidence quality
- confidence delta
- failure or surprise
- reusable lesson
- invalidated assumption
- retry condition
- expiration/revalidation condition

The next cycle must consume these capsules before choosing work.

This prevents “learning” from becoming vague narrative memory.

---

## 6. Anti-Confusion Protocol

ASCENSION outputs use six mutually exclusive labels:

### VERIFIED
Claims supported by completed tests/evidence.

### BUILT
Artifacts actually created in the current environment.

### PROPOSED
Designs not yet verified.

### REJECTED
Alternatives intentionally discarded and why.

### RISKS
Known uncertainty, boundary, or failure concerns.

### NEXT
Exactly one highest-leverage next experiment, plus optional backup candidates.

A proposal is never described as built. A built artifact is never described as integrated unless actual integration occurred.

---

## 7. Non-Duplication Rule

Before building a capability, ASCENSION asks:

1. Is another system already responsible for this?
2. Is the improvement a reusable primitive rather than a competing replacement?
3. Can it be delivered as an interface, evaluator, protocol, or optional module?
4. Does adoption require the owning system’s explicit action?
5. Could ASCENSION fail without impairing the sibling system?

If the answer to #5 is no, the design is rejected or redesigned.

---

## 8. Strategic Search Rule

For each cycle, ASCENSION compares candidate work using this conceptual leverage model:

`Potential = Breadth × Expected Improvement × Reuse × Confidence`

tempered by:

`Friction = Integration Cost × Interference Risk × Verification Cost`

The planner prefers large `Potential / Friction`, but promotion still depends on the hard evidence gates above.

This protects the series from chasing impressive-sounding but weakly testable ideas.

---

## 9. Initial Capability Roadmap

The next strongest layers, in order, are:

1. **Evaluator Fabric** — shared test protocol for capability packets across heterogeneous systems.
2. **Collision Detector** — detects overlapping responsibilities and incompatible contracts before handoff.
3. **Context Distillation Engine** — compresses checkpoints into loss-aware, testable state summaries.
4. **Capability Dependency Graph** — tracks which improvements depend on which contracts and evidence.
5. **Failure-Injection Harness** — deliberately breaks assumptions to validate fail-open behavior.
6. **Reuse Compiler** — converts a verified primitive into consumer-specific adapter specifications.
7. **Evidence Aging / Revalidation** — automatically marks stale capabilities for re-test based on changed dependencies.

These are ASCENSION-owned support capabilities, not replacements for sibling systems.

---

## 10. Current Checkpoint

### VERIFIED
- Architectural authority boundaries are explicitly defined.
- Promotion requires measurable evidence, rollback, non-interference, and versioned contracts.
- “Self-learning” is defined as iterative adaptation from recorded outcomes rather than hidden weight updates.

### BUILT
- Capability Kernel v0.2 specification.
- Capability Packet JSON Schema.
- Nine-stage cycle.
- Capability lifecycle.
- Promotion-gate system.
- Experience Capsule design.
- Anti-confusion protocol.
- Initial capability roadmap.

### PROPOSED
- Evaluator Fabric v0.1 as the next build increment.
- Collision Detector and dependency graph as subsequent increments.

### REJECTED
- Single scalar “intelligence score” for capability promotion.
- Silent cross-system integration.
- Direct mutation of sibling system state.
- Unverified capability promotion based on plausibility alone.

### RISKS
- A loop can still drift if checkpoints are not durable.
- Metrics can be gamed if tests are narrow.
- Cross-system contracts can become stale as sibling interfaces evolve.
- “Reusable” capabilities may impose hidden integration cost if adapters are underspecified.

### NEXT
Build **Evaluator Fabric v0.1**: a standardized test/evidence harness that can evaluate heterogeneous capability packets without assuming their domain, then attach regression and adversarial test bundles to every verified packet.
