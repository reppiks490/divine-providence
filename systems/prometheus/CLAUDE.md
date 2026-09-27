# Claude continuation instructions — PROMETHEUS

PROMETHEUS is a research-only sibling/meta-layer. Continue from the design spec and current implementation plan; do not merge it into NEXUS, AION, ARGUS, ATHENA, DAEDALUS or Icarus.

For every top-level run, preserve the plugin audit contract: consider every visible plugin, invoke every materially beneficial eligible plugin through the host, require Deep Research when available, and record explicit skip/failure reasons. Do not simulate real connector use inside local Python tests. Normalize each selected execution into descriptor-bound evidence, and treat contribution overlap as attribution bookkeeping rather than quality.

For sibling evidence, use the v0.2 read-only NEXUS adapter. Bind new bundles under the current NEXUS v1.15 path-independent contract pin (ADR 0004); the recovered v0.3 release identity replays only the recorded historical bundle. Reject contract/causal drift, preserve `CANDLE_PROXY`, `state_input`, and `RESEARCH_CANDIDATE_ONLY`, and never infer semantics absent from the authoritative payload.

A complete engineering-pass run may emit only `READY_FOR_DAEDALUS_REVIEW`; degraded/rejected/stale-lineage runs emit no packet and PROMETHEUS never represents DAEDALUS acceptance. Preserve v0.4 disagreement diagnosis as a conservative evidence label: role-specific differences may be intentional specialization and unknown causes stay irreducibly ambiguous. v0.5 adds a separate experiment-routing gate: stale/source-unhealthy evidence can defer replay, healthy specialization can abstain, ambiguity may only trigger a bounded uncertainty-reduction probe, and exact negative-result reuse is scoped to the immutable route/contract context. The unified v0.5 build keeps the provenance-attestation lineage alongside it: review packets must also bind a matching `ResearchProvenanceManifest` and a complete `ProvenanceLineageReport` (`prometheus_loop.provenance_lineage`, distinct from the stale-aware `prometheus_loop.lineage`), `REQUIRE_VERIFIED` attestation policy degrades runs without verified external receipts, and PROMETHEUS never claims to perform cryptographic verification itself.

Run `PYTHONPATH=src pytest -q` and `PYTHONPATH=src python -m compileall -q src tests` before claiming success.

**Stale when:** the host plugin contract, NEXUS release identity, or sibling authority boundaries change.
