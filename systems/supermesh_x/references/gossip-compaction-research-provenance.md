# v3.6 Gossip Compaction — Public Research Provenance

External research in this cycle was read-only. No private account data, credentials, proprietary repository contents, connected-email/finance contents, or internal SuperMesh state were sent to public providers.

| Adopted design claim | Public evidence used | Adoption / authority ruling |
| --- | --- | --- |
| Trusted state should reject lower previously-seen versions and signed snapshot metadata should bind the versions/hashes of state it represents. | The Update Framework specification: https://theupdateframework.github.io/specification/v1.0.35/ and https://github.com/theupdateframework/specification/blob/HEAD/tuf-spec.md | Adopted as a design analogy only. SuperMesh uses its own witness policy and does not import TUF authority or keys. |
| An independent witness can cosign a transparency checkpoint after checking consistency, reducing reliance on a single log view. | C2SP Transparency Log Witness Protocol: https://c2sp.org/tlog-witness | Adopted for evidence-authentication semantics only. Witness signatures remain explicitly non-authoritative for execution/writes/trading. |
| Crash consistency requires explicit ordering/durability primitives; rename alone is not a universal persistence guarantee. | Pillai et al., OSDI 2014, *All File Systems Are Not Created Equal*: https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai | Adopted as justification for fsync-before-publication and parent-directory fsync where the platform permits it. |
| A local monotonic record cannot detect restoration of every local trusted file to an older internally valid image without an independently retained trust floor. | Derived threat-model conclusion, consistent with TUF client-side trusted-version retention and rollback defense. | Made explicit in the API through optional external epoch/digest pins; no stronger local-only guarantee is claimed. |

Providers actually used for this research phase: Exa Search, Parallel Search, and Tavily Search. Tavily Research was attempted but returned a plan usage-limit error and is recorded as degraded/unavailable rather than successful.
