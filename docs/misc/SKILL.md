---
name: supermesh-x
description: Use when a task benefits from cross-platform research, data acquisition, market/crypto intelligence, coding orchestration, repository coordination, study workflows, or multi-provider evidence fusion across ChatGPT, Codex, and Claude.
---

# SuperMesh-X

SuperMesh-X is a capability router and evidence-fusion skill. It does **not** replace provider plugins; it discovers available capabilities, selects the smallest useful provider set, expands when evidence is weak, normalizes results, cross-checks conflicts, and preserves provenance.

## Core rule

Route by **capability**, never by hard-coded provider name. A provider is an implementation detail. If one provider is unavailable, stale, incomplete, or quota-limited, select another registered provider with the same capability.

## Operating loop

1. Classify the request into one or more capability domains.
2. Discover available runtime tools, plugins, skills, connectors, browser/search access, local files, and public APIs.
3. Build a retrieval plan with a minimum lane and escalation lanes.
4. Retrieve from independent sources where corroboration materially improves accuracy.
5. Normalize identifiers, timestamps, units, symbols, schemas, and source metadata.
6. Detect conflicts, stale data, missing fields, duplicate evidence, leakage, and unsupported inferences.
7. Fuse evidence into a claim graph with confidence and provenance.
8. Execute code or repository work only through the runtime's authorized coding/orchestration tools.
9. Verify the requested outcome before claiming completion.
10. Preserve a compact handoff when the work crosses agents, sessions, or runtimes.

## Lazy-load references

Read only the references needed for the task:

- Broad/deep web research, crawling, academic research, search diversification: `references/research-mesh.md`
- Stocks, ETFs, futures, FX, rates, macro, fundamentals, factors, backtesting: `references/finance-quant.md`
- Crypto markets, wallets, contracts, on-chain data: `references/crypto-onchain.md`
- Coding, repositories, multi-agent ownership, handoffs: `references/coding-orchestration.md`
- YouTube, study, teaching, knowledge extraction: `references/learning-media.md`
- NVIDIA/GPU acceleration and skill discovery: `references/nvidia-compute.md`
- Dynamic providers, capability contracts, failover: `references/provider-registry.md`
- Verification, data quality, permissions, provenance: `references/verification-governance.md`
- System-level architecture: `references/architecture.md`
- Source-universe expansion: `references/source-expansion.md`
- Adaptive query compilation: `references/query-planner.md`
- Evidence-family fusion and contradiction handling: `references/evidence-fusion.md`
- Point-in-time and revision-aware research: `references/temporal-data.md`
- Live plugin/tool discovery and optional-provider expansion: `references/plugin-discovery.md`

## Capability escalation

Start narrow. Expand only when useful:

`single authoritative source → second independent source → specialist provider → broad search/crawl → primary-source verification → structured synthesis`

For research-heavy tasks, diversify by **source class**, not just query wording: official/primary, specialist database, scholarly, market/structured feed, reputable journalism, community discussion where appropriate, and user/private sources when authorized.

## Hard boundaries

- Never claim access to a provider that is not actually available and authenticated in the current runtime.
- Never treat search snippets as equivalent to primary-source evidence when primary verification is practical.
- Never merge conflicting observations silently; preserve disagreement and timestamps.
- Never use future-known data in historical backtests or claim point-in-time validity without an availability timestamp.
- Never let one plugin inherit another plugin's permissions.
- Never convert research authority into transaction/deployment/account-change authority.
- Respect provider terms, authentication, rate limits, robots policies, and user-granted permissions.
