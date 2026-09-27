# H5 — SIBLING INTEGRATION FABRIC

## Verified heads
AION `reppiks490/aion-parallax-research` = 12a7cb8ef99e84ce50b766db0aea1592b3906f80
DAEDALUS `reppiks490/daedalus-research-os` = 74ad94149b02ddd3f69d535ee5fdc00c1fdbe096
ICARUS `reppiks490/Icarus` = 007e70189945b8e112904cf92b2b1a12e43792d6

## Boundary rule
Serialized/versioned packets only. HELIOS integration runtime must not directly import `aion.*`, `daedalus.*`, `icarus_bridge.*`, or `icarus_engine.*`. Reject sibling packets where production_authorized or execution_authorized is true.

## AION
Verified seam: `aion/federation.py` exports `aion-evidence-v1` packets containing asof_ns, frame_hash, source_hashes, synthetic, quality, production_authorized=False, execution_authorized=False. Recommended minimal producer addition: `helios` view with packet_type `historical_evidence`. Preserve symbolic AION evidence semantics; never reinterpret its numeric tier as a universal cross-system level. Reject AION frame with asof_ns > HELIOS decision time.

## DAEDALUS
Verified internal objects: SourceIdentity, ValidationResult, ProtectedHoldoutResult, PromotionDecision, HoldoutAssessment. ExperimentRegistry is mutable operational state, so it cannot be the immutable evidence identity. Add frozen neutral export `daedalus-validation-v1` / `scientific_validation`, carrying source identity, validation, protected holdout, holdout protocol, promotion dimensions, source commit, exported time and packet hash; always production_authorized=False and execution_authorized=False. Promotion means research gate passed, never trading permission.

## ICARUS
Verified safe public/read surfaces: GET /healthz and GET /status/public. H5 allowlist: GET only; loopback hosts 127.0.0.1/localhost/::1; no redirects; no arbitrary URLs; no admin/webhook secrets. Reject `/webhook`, `/admin/*`, and authenticated state-changing/research routes. Do not import AdvisoryLedger, validate_patch, ExecutionEngine, Alert or Broker. Serialized research_candidate artifacts may be ingested only as evidence when execution_authorized=False. Outbound HELIOS→ICARUS advisory remains CONTRACT_ONLY until a dedicated reviewed endpoint exists.

## Contract drift
Unknown sibling commit degrades VERIFIED_AVAILABLE to VERIFIED_DEGRADED until compatibility is re-run. Historical readiness is not rewritten.

## Neutral IntegrationEvidence
Store producer system, source packet hash, knowledge time, evidence class, synthetic flag, quality flags, upstream evidence refs and payload ref. Derived sibling evidence retains lineage: a DAEDALUS result based on AION evidence is not fully independent of its AION parent.

## End-to-end world
AION frame -> HELIOS evidence -> H2 hypotheses -> H3 requests validation -> DAEDALUS result derived from AION -> dependence retained -> ICARUS public status observed -> no order payload -> restart -> identical integration evidence IDs.
