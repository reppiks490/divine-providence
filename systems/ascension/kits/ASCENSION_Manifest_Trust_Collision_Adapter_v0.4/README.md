# ASCENSION Manifest Trust → Collision Adapter v0.4

**Lifecycle:** CANDIDATE  
**Authority:** read-only ASCENSION capability; no sibling adoption or authority is implied.

v0.4 composes an explicit, pinned chain:

1. Evaluator Fabric v0.4 attestation trust
2. Evaluator Fabric v0.8 strict RFC 9162 index-bound inclusion
3. Evaluator Fabric v0.7 compact consistency + signed witness observations
4. Collision Detector v0.3 semantic/structural collision analysis

Compared with v0.3, this release removes v0.6 side-directed inclusion from the active path, pins an explicit inclusion-evidence schema, binds the manifest's domain-separated Merkle leaf hash into provenance, records inclusion/transition result digests, and verifies the exact embedded dependency source bytes against build-time SHA-256 pins before accepting a manifest.

## Safety model

ASCENSION analysis fails closed when trust/transparency/contract/integrity evidence fails. `safe_for_siblings=true` means the failure does not authorize mutation or interruption of sibling runtime. The adapter never writes sibling state.

## Important claim boundary

Local/synthetic verification is extensive, but no authoritative signed real sibling manifest has passed the Transfer gate. Therefore v0.4 remains CANDIDATE and is not `VERIFIED` or `ADOPTED_EXTERNALLY`.

## Rollback

Adapter v0.3 and Collision Detector v0.2.1 remain independent rollback checkpoints.
