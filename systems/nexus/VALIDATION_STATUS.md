# Validation Status — NEXUS v0.1

Verified in the build environment on 2026-09-23:

- `PYTHONPATH=src pytest -q` -> **22 passed**
- `PYTHONPATH=src python -m compileall -q src` -> **passed**
- current materialized corpus catalog -> **476 physical CSV entries / 238 usable / 238 AppleDouble / 1,970,753 parsed rows**
- repeated catalog runs -> byte-identical JSON manifest SHA-256 `3a63534063728b76cb8e3048d18f4bc4bac911ec61ef90cdb6ed64057e4ff633`
- real NQ/ES/VIX/DXY/VXN adaptive-state smoke -> **passed**, see `artifacts/real_smoke.json`
- sibling verification in same environment:
  - ARGUS -> **4 passed**
  - ATHENA -> **3 passed**
  - AION -> **11 passed**
  - DAEDALUS -> **45 passed**

Not verified / not claimed:

- authoritative expected ~800+ corpus reconciliation
- true trade/depth ingestion or execution-quality calibration
- live feed adapters
- predictive edge or production readiness
- broker connectivity or order authority
- performance benchmark at the full expected corpus scale

The failed editable-install attempt was environmental: pip attempted to download build dependencies while network access was unavailable. Tests run directly against `src/` and passed; dependencies (`numpy`, `pandas`, `pytest`) were already present.

## Canonical superseding update — 2026-09-30

The older checkpoint above is retained as historical context but is no longer
the current corpus status.

- GitHub Actions NEXUS verification: **174/174 tests passed** on the current
  representation-safe code path.
- Historical corpus reconciliation is now reproducible from pinned commits:
  **10 ZIPs / 659 usable CSV archive members / 13,788,256 logical rows /
  542 distinct byte-exact contents**.
- Independent ZIP scanning and NEXUS produce identical sets of 542 content
  hashes: **0 independent-only / 0 NEXUS-only**.
- The DAEDALUS extracted-corpus checkpoint remains **803 physical CSV files /
  542 distinct contents**; the difference from 659 archive members is physical
  lineage/copy placement, not independent evidence.
- NEXUS advanced CSV loop semantics are now **v1.18**. Chart/view family and
  sampling construction are orthogonal identity axes. Tick/range claims cannot
  be interpreted as minute/hour intervals or as chart-family identity.
- Representation-sensitive modeling is fail-closed and uses
  `HierarchicalFactorEngine.build_from_manifests`: streams are fused within
  sampling construction, constructions within chart family, chart families
  within symbol, and only then across assets.
- Exact/logical duplicates receive no extra evidence weight; missing
  observations remain missing at the representation consensus layer.

This verifies engineering and corpus integrity properties only. It does not
prove predictive edge, profitability, live execution quality, broker
connectivity, or production authorization. Named-contract/roll identity,
micro-contract tapes, export-specific sessions, and unresolved chart-family
attestations remain separate evidence requirements.


### 2026-09-30 fourth-pass identity hardening

Price geometry is not treated as chart/view identity. Exact standard-OHLC or
Heikin-Ashi transform matches can prove geometry, but they cannot by themselves
distinguish an ordinary candlestick view from a TPO/footprint/profile view that
preserves that geometry. The canonical representation contract is therefore
four-axis: **chart/view family, price geometry, sampling domain, sampling
construction**. Family-specific modeling remains fail-closed without reviewed
view identity. Current GitHub Actions verification: **174/174 tests passed** and
`python -m compileall -q src tests scripts` passed.


### Final quadruple-check fusion order

The representation-safe model plane now balances correlated evidence in this
order: **raw streams -> sampling construction -> price geometry -> reviewed
chart/view family -> symbol -> cross-asset factor**. Transform math can prove
price geometry but cannot assign a TPO/footprint/profile/candlestick view family.
Same-symbol streams from different venues are not interchangeable. Historical
checkpoint reconciliation never auto-authorizes semantic coverage or production.
Current GitHub Actions baseline: **174/174 tests passed** plus compileall.
