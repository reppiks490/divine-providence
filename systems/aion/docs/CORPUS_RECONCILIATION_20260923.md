# PARALLAX corpus reconciliation (CA, 2026-09-23)

This is a physical inventory, not a proof of independent signals, source
identity, decision-time availability, market-data rights, or profitability.

`aion.parallax_manifest` scanned the nine ZIPs in the local
`multi-level-csv` checkout at `Icarus-ml-d9d4db8/history/unzipped/_repo`
and the separate `Downloads/Csv indexes.zip`. It found:

| Measure | Result |
| --- | ---: |
| Archive members that are CSV data (excluding sidecars) | 659 |
| Parsed CSV members | 659 |
| Distinct byte-exact SHA-256 contents | 542 |
| Members belonging to an exact-byte duplicate group | 230 |
| Members with repeated raw header names | 183 |
| Logical data records parsed by `csv.reader` | 13,788,256 |

The earlier handoff's approximately 13,787,630 rows differs by 626. The
physical member and hash counts agree exactly; the row-count discrepancy is
still uninvestigated and must not be described as a verified equality. The
33-file index archive contributes 1,199,340 logical rows, matching its
earlier estimate exactly.

The DAEDALUS six-root extracted catalog has 803 physical files and 542
distinct SHA-256 contents. Comparing complete SHA sets gives **zero ZIP-only
and zero extracted-only hashes**. All 144 files in the extra `Downloads/Csv`
root have byte content present in the other extracted roots. They are still
separate physical records; no source was deleted or silently collapsed.

The complete archive/member-level manifest is generated locally at
`artifacts/parallax-ten-archives.json` and intentionally ignored by Git.
It contains absolute owner paths. The inventory preserves archive/member
ordinal, original header positions, parse status and member hash. It does
not establish contract, chart transform, event/availability clock, provider,
or execution-safe status. Stock candidate CSVs remain context, not NQ
futures execution tape. PARALLAX analogs and AION real-data replay remain
disabled until these identities are reviewed.


## Representation-aware interpretation

The corpus is intentionally multi-view. Physical members must not be interpreted
as independent market votes merely because they are separate CSVs.

**Chart family and sampling construction are orthogonal dimensions.** A stream
may be regular candles sampled by time, ticks or range; Renko may use range-like
completion; Heikin Ashi may be time- or event-sampled. Therefore a `1000T`
suffix establishes tick sampling only. It does not, by itself, establish the
chart family.

Inventory v3 records a non-authoritative `representation_claim` with separate
`family`, `sampling_domain`, `construction`, and native `setting`.
Profile/order-flow-like headers are schema tags only; they do not silently prove
chart construction or feed semantics. Exact-byte duplicates preserve lineage
but receive no extra evidence weight.

Downstream rule: causally align native representation clocks; fuse streams
inside sampling construction; fuse constructions inside price geometry; fuse
price geometries inside reviewed chart/view family; fuse chart/view families to
a symbol-level state; only then perform cross-asset weighting. Tick/range/Renko/profile streams must never be coerced to fictional
fixed-minute cadence.



## Inventory schema v3 — orthogonal representation identity

PARALLAX now records chart/view family separately from sampling construction.

- **Chart family:** regular candles, Heikin Ashi, Renko, TPO, volume
  footprint/profile, session volume profile, or unresolved.
- **Sampling domain/construction:** time/time-bar, event/tick, event/range, or
  unresolved.

A `1000T` or `10R` suffix proves only a tick/range sampling claim. It does
not by itself identify the chart family. Conversely, a Renko/HA/profile family
label does not authorize a fixed clock. The six documented equity-candidate
archives are recorded as regular-candle views with TIDE/market-profile fields
as schema overlays, not as separate profile chart families.

Downstream fusion therefore uses:
`stream -> sampling construction -> price geometry -> chart/view family -> symbol -> cross-asset`.
Unresolved chart family or sampling construction remains fail-closed for
representation-sensitive fusion. Exact duplicates preserve lineage but add no
evidence weight.


### Price geometry is a separate axis

Inventory v4 also separates **price geometry** from chart/view family and
sampling construction. A stream may have standard OHLC geometry while carrying
a TPO/footprint/profile view, or Heikin-Ashi geometry while still requiring
separate evidence about the surrounding chart/view configuration.

Accordingly, deterministic OHLC comparisons may prove
`standard_ohlc` or `heikin_ashi` geometry, but they do not by themselves
prove a complete view-family identity. The identity axes are now:

`instrument -> view family -> price geometry -> sampling construction/native setting -> session/clock provenance`.

This keeps mathematical transform evidence useful without letting it silently
stand in for export-specific chart/session provenance.
