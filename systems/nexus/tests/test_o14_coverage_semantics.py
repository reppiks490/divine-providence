from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script(name: str):
    path = Path(__file__).parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_standard_geometry_probe_does_not_assign_regular_view_family():
    mod = _load_script("o14_coverage_matrix.py")
    manifest = [{
        "raw_sha256": "a" * 64,
        "archive_path": "Csv files for different chart types.zip",
        "source_path": "x.zip!possible-profile/NQ1!, 20.csv",
        "byte_duplicate_of": "",
        "representation_family": "unknown",
        "price_geometry": "unknown",
        "symbol": "NQ1!",
        "venue": "CME",
        "observed_cadence_ns": str(20 * 60 * 1_000_000_000),
        "construction": "time_bar",
        "native_setting": "20",
    }]
    probe = [{
        "raw_sha256": "a" * 64,
        "proved_price_geometry": "standard_ohlc",
        "proof": "overlapping_ohlc_equals_known_standard_geometry",
    }]
    families, geometries = mod._identity_maps(manifest, probe)
    assert families.get("a" * 64) is None
    assert geometries["a" * 64] == "standard_ohlc"
    status, _ = mod._status(
        manifest, families, geometries, "NQ1!", "CME", "20",
        "regular_candles", "standard_ohlc",
    )
    assert status == "PRESENT_GEOMETRY_PROVED_VIEW_UNRESOLVED"


def test_documented_regular_archive_proves_view_and_standard_geometry():
    mod = _load_script("o14_coverage_matrix.py")
    manifest = [{
        "raw_sha256": "b" * 64,
        "archive_path": "Full csv candles only.zip",
        "source_path": "Full csv candles only.zip!NQ1!, 20.csv",
        "byte_duplicate_of": "",
        "representation_family": "regular_candles",
        "price_geometry": "standard_ohlc",
        "symbol": "NQ1!",
        "venue": "CME",
        "observed_cadence_ns": str(20 * 60 * 1_000_000_000),
        "construction": "time_bar",
        "native_setting": "20",
    }]
    families, geometries = mod._identity_maps(manifest, [])
    status, _ = mod._status(
        manifest, families, geometries, "NQ1!", "CME", "20",
        "regular_candles", "standard_ohlc",
    )
    assert status == "PROVED_PRESENT"


def test_cross_venue_same_symbol_does_not_fill_named_spot_cell():
    mod = _load_script("o14_coverage_matrix.py")
    rows = [{
        "raw_sha256": "c" * 64,
        "archive_path": "Full csv candles only.zip",
        "source_path": "Full csv candles only.zip!COINBASE_BTCUSD, 20.csv",
        "byte_duplicate_of": "",
        "representation_family": "regular_candles",
        "price_geometry": "standard_ohlc",
        "symbol": "BTCUSD",
        "venue": "COINBASE",
        "observed_cadence_ns": str(20 * 60 * 1_000_000_000),
        "construction": "time_bar",
        "native_setting": "20",
    }]
    families, geometries = mod._identity_maps(rows, [])
    status, _ = mod._status(
        rows, families, geometries, "BTCUSD", "BITSTAMP", "20",
        "regular_candles", "standard_ohlc",
    )
    assert status == "MISSING"


def test_ha_geometry_requires_recursive_open_identity():
    probe = _load_script("o14_representation_probe.py")
    standard = {}
    heikin = {}
    prev_ha_open = None
    prev_ha_close = None
    for i in range(220):
        ts = i
        so = 100.0 + i * 0.1
        sh = so + 2.0
        sl = so - 2.0
        sc = so + 0.5
        standard[ts] = (so, sh, sl, sc)
        hc = (so + sh + sl + sc) / 4.0
        ho = (so + sc) / 2.0 if prev_ha_open is None else (prev_ha_open + prev_ha_close) / 2.0
        hh = max(sh, ho, hc)
        hl = min(sl, ho, hc)
        heikin[ts] = (ho, hh, hl, hc)
        prev_ha_open, prev_ha_close = ho, hc

    good = probe._compare(standard, heikin)
    assert good["ha_close_high_low_score"] == 1.0
    assert good["ha_open_recurrence_score"] == 1.0
    assert good["ha_score"] == 1.0

    broken = dict(heikin)
    for ts in range(1, 220):
        ho, hh, hl, hc = broken[ts]
        broken[ts] = (ho + 0.25, hh, hl, hc)
    bad = probe._compare(standard, broken)
    assert bad["ha_close_high_low_score"] == 1.0
    assert bad["ha_open_recurrence_score"] < 0.5
    assert bad["ha_score"] < probe.PROOF_SCORE


def test_geometry_probe_requires_most_of_candidate_to_overlap():
    probe = _load_script("o14_representation_probe.py")
    standard = {i: (100.0, 102.0, 98.0, 101.0) for i in range(220)}
    candidate = {i: (100.0, 102.0, 98.0, 101.0) for i in range(1000)}
    result = probe._compare(standard, candidate)
    assert result["overlap"] == 220
    assert result["candidate_coverage"] == 0.22
    assert result["reference_coverage"] == 1.0
    assert result["standard_score"] == 0.0
    assert result["ha_score"] == 0.0
