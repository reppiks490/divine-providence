# PROMETHEUS agent rules

Read these before modifying code:

1. `docs/superpowers/specs/2026-09-24-prometheus-autonomous-systems-evolution-design.md`
2. `docs/superpowers/plans/2026-09-24-prometheus-v0.1-vertical-slice.md`
3. `docs/superpowers/plans/2026-09-24-prometheus-v0.2-sibling-bindings.md`
4. `docs/superpowers/plans/2026-09-25-prometheus-v0.3-plugin-evidence.md`
5. `docs/superpowers/plans/2026-09-25-prometheus-v0.4-lineage-diagnosis.md`
6. `docs/superpowers/specs/2026-09-25-prometheus-v0.4-provenance-attestation-design.md`
7. `docs/superpowers/plans/2026-09-25-prometheus-v0.4-provenance-attestation.md`
8. `docs/superpowers/specs/2026-09-25-prometheus-v0.5-external-attestation-lineage-design.md`
9. `docs/superpowers/plans/2026-09-25-prometheus-v0.5-external-attestation-lineage.md`
10. `docs/architecture/plugin-orchestration.md`
11. `docs/architecture/plugin-evidence-and-promotion.md`
12. `docs/architecture/sibling-bindings.md`
13. `docs/architecture/lineage-and-diagnosis.md`
14. `docs/architecture/experiment-routing.md`
15. `docs/changes/2026-09-26-prometheus-v0.5-unified-merge.md`
16. `docs/VALIDATION_STATUS.md`

Hard invariants:

- PROMETHEUS is research-only; never add a production authorization or broker/order path.
- NEXUS owns causal market fabric/replay; do not manufacture timing or availability evidence.
- The v0.2 NEXUS binding pins release snapshot `1119ef3d9b561dc89668a9768893a2b1ab09cd542ffd1d7a02dd73f5a81388a2` and must fail closed on drift.
- Do not import NEXUS or sibling repositories at runtime; use read-only payload contracts.
- ARGUS owns authenticated trade/depth semantics; candle proxies remain `CANDLE_PROXY`.
- ATHENA owns supervisory world state/risk/abstention; NEXUS `state_input` is not an ATHENA conclusion.
- AION owns durable sibling evidence memory.
- DAEDALUS owns statistical promotion; its NEXUS bridge remains `RESEARCH_CANDIDATE_ONLY`.
- Every top-level loop run inventories visible plugins and attempts every materially beneficial, policy-eligible plugin.
- Deep Research is required when available; failures/unavailability are explicit.
- A selected plugin without a host execution record is a failed run contract.
- Every selected execution must normalize to immutable descriptor-bound plugin evidence.
- Plugin contribution classes are attribution structure, not quality rankings.
- PROMETHEUS may emit only `READY_FOR_DAEDALUS_REVIEW`; DAEDALUS acceptance remains external.
- Promotion packets must be lineage-bound and are suppressed when required contract fingerprints are stale.
- Unknown disagreement causes must remain `IRREDUCIBLE_AMBIGUITY`; do not invent causal certainty.
- Replay eligibility is a separate research decision from experiment outcome; stale/source-unhealthy evidence can block replay without creating a rejection.
- Intentional specialization may terminate a research branch without forced consensus or replay.
- Route priority bands are ordinal research-policy labels, not global quality scores.
- Exact negative-result reuse must remain bound to the immutable routing context; contract/plugin changes must not inherit prior negatives.
- Every DAEDALUS review packet must bind one immutable `ResearchProvenanceManifest` whose current loop/candidate/experiment/plugin/observation/source-contract lineage matches exactly.
- Provenance manifests are content-addressed application records, not host/plugin cryptographic signatures; never upgrade them into attestation claims the host did not supply.
- Every DAEDALUS review packet carries BOTH bindings: the stale-aware `ResearchLineageManifest` (with a clean `StaleEvidenceReport` bound to it) and the `ResearchProvenanceManifest` plus a complete `ProvenanceLineageReport` whose tip is that manifest. Neither binding may substitute for the other.
- The two lineage concepts are separate modules: `prometheus_loop.lineage` (stale-aware research lineage / contract-fingerprint staleness) and `prometheus_loop.provenance_lineage` (provenance-manifest ancestry verification). Do not merge or alias them.
- `REQUIRE_VERIFIED` attestation policy degrades runs with missing, partial, or unverified selected-plugin coverage; the attestation policy is part of deterministic loop identity.
- Never guess missing sibling schemas or infer direction/regime/risk/confidence from generic factor sign.
- Use TDD for behavior changes.

**Stale when:** the authority map, pinned sibling contract, or host plugin execution model changes.
