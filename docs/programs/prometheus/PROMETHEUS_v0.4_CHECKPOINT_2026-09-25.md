# PROMETHEUS v0.4 Verified Checkpoint — 2026-09-25

- Branch: `work/prometheus-v0.4-provenance`
- HEAD: `22c2aae066a4e74fcc331e60285ceeed10b86d1e`
- v0.3 baseline: `a00db63da838c91b0b100d48a717a36cbaedcde4`
- Tests: **79 passed in 0.20s** on the final post-commit gate
- Explicit production-authority negative test: **passed**
- Compile: **passed**
- Deterministic demo: **passed**
- Provenance manifest -> promotion packet binding: **passed**
- Production-authority source scan: **passed**
- Broker/credential scan: **passed**
- Runtime sibling-import scan: **passed**
- Tracked-bytecode scan: **passed**
- Git diff check: **passed**
- Working tree: **clean**
- Git bundle verification: **passed**

## v0.4 additions

1. Immutable content-addressed `ResearchProvenanceManifest`.
2. Exact binding of loop, experiment, candidate, selected plugin descriptor, plugin evidence, contribution, observation, source-contract, and parent-manifest identities.
3. Canonical ordering with duplicate rejection.
4. Artifact namespace validation to reject cross-type identity substitution.
5. Provenance-bound `ResearchPromotionPacket` with fail-closed stale/tampered lineage checks.
6. NEXUS contract snapshot identity carried as `nexus-contract:<sha256>` after validation.
7. Source-contract and parent-manifest lineage incorporated into deterministic loop identity.
8. Degraded/rejected/reused-negative paths remain unable to produce a provenance-backed DAEDALUS review packet.
9. `production_authorized=True` remains structurally rejected.

## Authority note

This is a research-only application provenance record. It is not a cryptographic signature from the ChatGPT host, a plugin provider, NEXUS, or DAEDALUS. DAEDALUS acceptance, protected validation, broker execution, and production promotion remain outside PROMETHEUS.

## Review note

The final code review was a self-review in this session because no independent subagent-review tool was available. The review found one important ambiguity (wrong artifact namespaces could previously be supplied to manifest fields); that issue was fixed test-first in commit `9b7f6e5`, and the final full suite remained green.

## Package digests

- Source ZIP SHA-256: `de2267af95543f1fefb0522332a370e7e2a6d0697b536367298fdde2624369db`
- Git bundle SHA-256: `68bca662d2310f2e89bfbbe1b314b9de1d40f56f52d6d0ff5515970ff7759faa`
