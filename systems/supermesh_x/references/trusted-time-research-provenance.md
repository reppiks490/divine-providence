# v3.7 trusted-time research provenance

Public research was used only as a read-only design-validation layer. No private account content, credentials, proprietary repository payload, or internal secrets were sent to research providers.

## Claim-source map

| Design claim | Public source | Adoption in SuperMesh-X |
| --- | --- | --- |
| Expired signed metadata must not remain indefinitely trusted; freeze protection uses expiration checks against a fixed update-start time. | The Update Framework Specification v1.0.35, sections on `EXPIRES`, fixed update start time, and freeze attacks: https://theupdateframework.github.io/specification/v1.0.35/ | Expiring witness policies are checked against one fixed trusted-time sample per operation; ambiguity at the boundary fails closed. |
| A time authority should use a trustworthy source of time and expose trustworthy time values; time assertions may carry accuracy/uncertainty and replay defenses such as nonces. | RFC 3161, Internet X.509 PKI Time-Stamp Protocol: https://www.rfc-editor.org/rfc/rfc3161.html | `TrustedTimeSample` carries source provenance, explicit uncertainty, and optional evidence digest. SuperMesh requires the adapter to authenticate the time evidence before constructing the sample. |
| Historical proof can remain verifiable even after a signing/time credential later expires or is revoked, provided the evidence proves the relevant earlier state. | RFC 3161 motivation and verification model; TUF's separation of trusted current metadata from historical signed objects. | Historical witness signature verification stays available after current policy expiry, while new active trust decisions are blocked. |
| Purely local rollback floors cannot detect restoration of every local trusted file to an older valid image without an independent retained floor. | General rollback-protection principle also used by TUF version trust and SuperMesh v3.6 external compaction pins. | `minimum_lower_bound_unix` is an optional external time floor; local durable floor alone is not overstated as universal rollback proof. |

## Providers actually used

- Exa search and fetch for primary-source validation.
- Parallel Search for cross-checking source discovery.
- Tavily Search for independent search confirmation.
- Tavily Research was attempted but returned HTTP/status 432 because the provider plan usage limit was exceeded; it is recorded as degraded and no result from that endpoint is claimed.

Stale when: cited standards materially change, or v3.7's trusted-time behavior changes.
