# SuperMesh-X v2.0.0

- Added authenticated distributed provider-health snapshots using HMAC-SHA256.
- Added explicit domain separation and key IDs for safe key rotation.
- Added epoch rollback and monotonic-sequence replay rejection.
- Added constant-time tag verification and conservative malformed-state rejection.
- Authentication remains routing-integrity only and cannot grant execution authority.
- Added smoke and regression coverage while preserving legacy merge/quota behavior.
