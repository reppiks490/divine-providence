# ADR 0001 — Host-mediated plugin-aware research loop

**Date:** 2026-09-24  
**Status:** accepted

## Context

The owner requires every new PROMETHEUS loop run to access every plugin that is materially beneficial to that run, with Deep Research explicitly required. The Python repository cannot directly execute ChatGPT-hosted plugins, and pretending otherwise would create false provenance.

## Decision

PROMETHEUS separates **plugin execution** from **plugin audit**. The ChatGPT host owns real connector invocation. The repository owns deterministic selection rules, typed host execution evidence, output/failure fingerprints, and enforcement that every selected plugin was actually attempted.

Deep Research is mandatory for top-level research runs when available. Irrelevant plugins are not called merely to inflate coverage; they remain visible as explicitly skipped decisions.

## Alternatives rejected

1. **Blindly call every installed plugin.** Rejected because unrelated plugins increase cost, permission surface and noise without marginal research value.
2. **Let the Python package fake or shell out to ChatGPT plugins.** Rejected because it would produce unverifiable provenance and couple the package to unavailable host internals.
3. **Treat plugin use as an undocumented chat convention.** Rejected because future loop runs and agents would not be able to prove compliance.

## Consequences

The audit is reproducible and testable offline, but real plugin availability and permissions remain host facts supplied at run time. A missing selected-plugin execution record is a hard error. A Deep Research availability/failure condition degrades or fails the run according to the design spec.

**Stale when:** a supported host API allows this repository to invoke ChatGPT plugins directly with auditable identities and least-privilege credentials.
