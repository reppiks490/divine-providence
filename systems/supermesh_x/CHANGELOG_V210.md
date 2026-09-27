# SuperMesh-X v2.1.0

## Authenticated key-rotation lifecycle
- Added explicit active/previous signing-key policy for distributed provider-health state.
- Previous keys are accepted only through a bounded epoch overlap.
- Revocation takes precedence over overlap; unlisted key IDs fail closed even if key material is locally present.
- Added deterministic secret-free rotation/revocation receipts.
- Preserves v2.0.0 HMAC/domain-separation/replay protections and all authority/privacy boundaries.
