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
