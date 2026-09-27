# Research notes

Cycle 020 checked exact first-party Deep Research availability; it was not exposed/callable. Research continued fail-open with Exa/web.

High-signal references used for design validation:
- TUF security and metadata guidance: explicit hashes/version metadata, threshold roles, rollback/mix-and-match defenses, and externally pinned trust state.
- Sigstore verification guidance: verify signer identity, root of trust, signature, and transparency-log inclusion rather than treating signature presence alone as sufficient.

The adapter does not implement TUF or Sigstore wholesale. These sources informed the narrower invariants: explicit backend identity, pinned policy/artifact digests, and no silent downgrade.
