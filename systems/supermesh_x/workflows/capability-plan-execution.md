# Capability Plan Execution Workflow

1. Resolve the requested capability through the Adaptive Capability Director.
2. Rank compatible providers and preserve ordered fallbacks.
3. Compile an execution contract with schema fingerprints, source class, privacy checks, and authority requirements.
4. If a schema fingerprint changed, stop that step and rediscover the provider surface.
5. If raw private data would reach a public provider, block the step.
6. If the capability is a transactional or external write, require explicit authorization before invocation.
7. Execute only steps marked executable under the current runtime state.
8. Record provider outcome in capability-specific feedback.
9. Persist the plan digest and discovery/provenance references for audit and replay.
10. On failure, re-evaluate fallbacks through the Adaptive Capability Director rather than bypassing the contract.
