# Adaptive Execution Planning

SuperMesh-X converts capability discovery into an explicit execution contract before invocation.

## Contract fields

Each plan records the requested capability, selected provider, ordered fallbacks, expected schema fingerprint, observed fingerprint, privacy classification, authority mode, preflight result, and whether the step is executable.

## Authority

Read-only capabilities can be eligible for automatic execution after preflight. Transactional brokerage actions and external writes require explicit authorization and are never promoted from research or analysis alone.

## Privacy

Raw `user_authorized_private` content cannot be routed to a public provider. `derived_private_feature` values may cross that boundary only when every transmitted field is explicitly allowlisted. Runtime credentials and secrets are never persisted into the plan object or its audit digest.

## Schema drift

If the observed provider schema fingerprint differs from the fingerprint pinned during planning, the step becomes non-executable and the preflight changes to `rediscover`. The Adaptive Capability Director must discover and validate the current surface before a new plan is compiled.

## Auditability

`plan_digest()` produces a deterministic SHA-256 digest over the persisted execution contract. The digest supports replay and comparison without embedding runtime secrets.
