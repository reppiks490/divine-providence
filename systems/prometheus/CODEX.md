# Codex continuation instructions — PROMETHEUS

Read `AGENTS.md` plus the Superpowers design/plans before editing. Work in an isolated branch/worktree. Use TDD.

The plugin boundary is host-mediated: local code records `HostPluginResult`; it does not invent ChatGPT connector calls. Every selected plugin must have an execution record and immutable descriptor-bound execution evidence. Deep Research is mandatory for top-level research runs when available. Plugin contribution classification is not a ranking or correctness score.

The v0.2 sibling boundary is also read-only: `NexusRunInput` validates and normalizes a pinned NEXUS v0.3 same-instant bundle, then delegates to the ordinary loop. Do not import sibling repos at runtime, repair mismatched decision times, upgrade ARGUS proxies, treat ATHENA inputs as conclusions, or fabricate DAEDALUS acceptance.

PROMETHEUS may emit only `READY_FOR_DAEDALUS_REVIEW`; never fabricate DAEDALUS acceptance. v0.4 review packets must carry a clean lineage manifest, and stale contract fingerprints suppress handoff. Conservative disagreement diagnosis must fall back to irreducible ambiguity when evidence is insufficient. v0.5 routing is separate from experiment outcome: stale/source-unhealthy evidence must block replay, intentional specialization may abstain, priority bands must not be treated as global scores, and negative-result reuse must remain route/contract-context-bound. The unified v0.5 build also requires every review packet to bind a matching `ResearchProvenanceManifest` plus a complete `ProvenanceLineageReport` (`prometheus_loop.provenance_lineage`); `REQUIRE_VERIFIED` plugin-attestation policy degrades runs lacking verified external attestation receipts, and PROMETHEUS never claims to have performed cryptographic verification itself.

Do not add production execution authority, broker dependencies, sibling-repo write paths, fabricated microstructure, or DAEDALUS holdout access.

**Stale when:** a supported direct host plugin SDK is introduced, the NEXUS release contract changes, or authority boundaries change.
