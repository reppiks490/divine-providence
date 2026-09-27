# Change record — PROMETHEUS v0.2 sibling bindings

**Date:** 2026-09-24  
**Actor:** OpenAI ChatGPT, at the user's direction  
**Request:** preserve a downloadable checkpoint, then continue PROMETHEUS into real sibling-contract integration while retaining the plugin and authority rules.

## Before

PROMETHEUS v0.1 operated on generic deterministic `ObservationEnvelope` fixtures. It had no real NEXUS-facing adapter and could not prove that a recovered NEXUS same-instant bundle was compatible with the research loop.

## Change

Added:

- a release-pinned NEXUS v0.3 bundle binding;
- validation of outer bundle authority and hash/shape invariants;
- conservative normalization for NEXUS, ARGUS, ATHENA, and DAEDALUS payloads;
- shared explicit factor/quality/OOD comparison dimensions;
- a thin `NexusRunInput` path into the existing loop;
- persistence of normalized observations in research memory; and
- deterministic `FailureCase` quarantine for contract drift and causal-instant mismatch.

## Now

PROMETHEUS can consume the recovered NEXUS v0.3 same-instant bundle fixture without runtime imports from NEXUS or sibling repos. Cross-projection inconsistencies can become SENTINEL disagreements; a clean bundle does not fabricate a disagreement.

ARGUS remains `CANDLE_PROXY`, ATHENA remains advisory/state-input only, DAEDALUS remains `RESEARCH_CANDIDATE_ONLY`, and production authorization remains false.

## Why

The next useful capability after the v0.1 orchestration skeleton is trustworthy evidence ingestion from the real Icarus substrate. Binding through NEXUS preserves causal timing and provenance while preventing PROMETHEUS from duplicating or overriding sibling ownership.

## Research/plugin provenance

This continuation used the installed Superpowers workflow, Akinator repository discipline, Baton Pass continuity guidance, Exa deep-research search, and Tavily research where they materially improved the implementation. No unavailable first-party Deep Research capability was falsely reported as invoked. The local Python package continues to model host plugin evidence rather than pretending to call ChatGPT plugins itself.

## Operational consequence

None. v0.2 is still an offline/read-only research package. It adds no broker connection, service deployment, migration, sibling write path, or production promotion interface.

## Rollback

Revert the v0.2 feature-branch commits. No external production state is mutated by this repository.

**Stale when:** NEXUS/sibling contract identities or same-instant payload semantics change, or live sibling service adapters are introduced.
