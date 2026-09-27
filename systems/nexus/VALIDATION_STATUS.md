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
