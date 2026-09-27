# v3.0.0
- Ed25519 signed runtime-evidence envelopes with deterministic canonical serialization.
- Public-key trust store with explicit rotation/revocation and key-ID collision protection.
- Signed journal admission with run/fence/replay guards.
- Capability non-escalation: signatures authenticate evidence but never grant authority.
- Preserves v2.9 evidence journal and all earlier contracts.
