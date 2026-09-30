from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


EXECUTION = {
    "NQ": {"symbol": "NQ1!", "venue": "CME", "required_standard": ["1", "5", "20", "60", "240", "1D"], "ha": ["20"], "micro": "MNQ"},
    "ES": {"symbol": "ES1!", "venue": "CME", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": "MES"},
    "YM": {"symbol": "YM1!", "venue": "CBOT", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": "MYM"},
    "GC": {"symbol": "GC1!", "venue": "COMEX", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": "MGC"},
    "SI": {"symbol": "SI1!", "venue": "COMEX", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": "SIL"},
    "PL": {"symbol": "PL1!", "venue": "NYMEX", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": "PLM"},
    "PA": {"symbol": "PA1!", "venue": "NYMEX", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": "PAM"},
    "BTCF": {"symbol": "BTC1!", "venue": "CME", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": None},
    "BTCUSD": {"symbol": "BTCUSD", "venue": "BITSTAMP", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": None},
}

MICRO_REQUIRED = ["1", "20", "1D"]
KNOWN_REGULAR_ARCHIVE = "Full csv candles only.zip"
DOCUMENTED_REGULAR_ARCHIVES = {
    "Csv first 60.zip",
    "First 60 half.zip",
    "Csv 2nd 60.zip",
    "2nd 60 half.zip",
    "Csv last 57.zip",
    "Last 57 half.zip",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _identity_maps(
    manifest_rows: list[dict[str, str]], probe_rows: list[dict[str, str]]
) -> tuple[dict[str, str], dict[str, str]]:
    """Build separate chart-family and price-geometry maps.

    Transform math may prove price geometry, never chart/view family. Exact-byte
    copies may inherit either identity because they are the same bytes.
    """
    family: dict[str, str] = {}
    geometry: dict[str, str] = {}

    for row in manifest_rows:
        sha = row["raw_sha256"]
        archive_name = Path(row["archive_path"]).name
        claimed_family = row.get("representation_family") or "unknown"
        claimed_geometry = row.get("price_geometry") or "unknown"

        if archive_name == KNOWN_REGULAR_ARCHIVE or archive_name in DOCUMENTED_REGULAR_ARCHIVES:
            family[sha] = "regular_candles"
            geometry[sha] = "standard_ohlc"
        else:
            if claimed_family not in {"", "unknown", "time_bars_unspecified", "tick_bars", "range_bars"}:
                family[sha] = claimed_family
            if claimed_geometry not in {"", "unknown"}:
                geometry[sha] = claimed_geometry

    changed = True
    while changed:
        changed = False
        by_path = {x["source_path"]: x for x in manifest_rows}
        for row in manifest_rows:
            sha = row["raw_sha256"]
            dup_path = row.get("byte_duplicate_of") or ""
            parent = by_path.get(dup_path) if dup_path else None
            if not parent:
                continue
            parent_sha = parent["raw_sha256"]
            if sha not in family and parent_sha in family:
                family[sha] = family[parent_sha]
                changed = True
            if sha not in geometry and parent_sha in geometry:
                geometry[sha] = geometry[parent_sha]
                changed = True

    for row in probe_rows:
        proved = row.get("proved_price_geometry") or ""
        sha = row.get("raw_sha256") or ""
        if proved in {"standard_ohlc", "heikin_ashi"} and sha:
            old = geometry.get(sha)
            if old and old != proved:
                geometry[sha] = f"CONFLICT:{old}:{proved}"
            else:
                geometry[sha] = proved

    return family, geometry


def _expected_cadence_ns(claim: str) -> int | None:
    if claim == "1D":
        return 86_400 * 1_000_000_000
    if claim.endswith("S") and claim[:-1].isdigit():
        return int(claim[:-1]) * 1_000_000_000
    if claim.isdigit():
        return int(claim) * 60 * 1_000_000_000
    return None


def _cadence_matches(row: dict[str, str], claim: str) -> bool:
    expected = _expected_cadence_ns(claim)
    try:
        observed = int(row.get("observed_cadence_ns") or 0)
    except ValueError:
        return False
    if not expected or observed <= 0:
        return False
    return abs(observed / expected - 1.0) <= 0.05


def _status(
    rows: list[dict[str, str]],
    families: dict[str, str],
    geometries: dict[str, str],
    symbol: str,
    venue: str,
    claim: str,
    wanted_family: str,
    wanted_geometry: str,
) -> tuple[str, list[str]]:
    # Timeframe coverage is based on observed cadence and exact venue identity,
    # never filename text or same-symbol prints from a different venue.
    matched = [
        r for r in rows
        if r["symbol"] == symbol
        and (r.get("venue") or "").upper() == venue.upper()
        and _cadence_matches(r, claim)
    ]
    both = [
        r for r in matched
        if families.get(r["raw_sha256"]) == wanted_family
        and geometries.get(r["raw_sha256"]) == wanted_geometry
    ]
    if both:
        return "PROVED_PRESENT", sorted({r["source_path"] for r in both})

    geometry_only = [
        r for r in matched
        if geometries.get(r["raw_sha256"]) == wanted_geometry
        and families.get(r["raw_sha256"]) != wanted_family
    ]
    if geometry_only:
        return "PRESENT_GEOMETRY_PROVED_VIEW_UNRESOLVED", sorted(
            {r["source_path"] for r in geometry_only}
        )

    family_only = [
        r for r in matched
        if families.get(r["raw_sha256"]) == wanted_family
        and geometries.get(r["raw_sha256"]) != wanted_geometry
    ]
    if family_only:
        return "PRESENT_VIEW_PROVED_GEOMETRY_UNRESOLVED", sorted(
            {r["source_path"] for r in family_only}
        )

    if matched:
        return "PRESENT_REPRESENTATION_UNRESOLVED", sorted(
            {r["source_path"] for r in matched}
        )
    return "MISSING", []


def _sampling(rows: list[dict[str, str]], symbol: str, venue: str, construction: str) -> tuple[str, list[str]]:
    matched = [
        r for r in rows
        if r["symbol"] == symbol
        and (r.get("venue") or "").upper() == venue.upper()
        and r.get("construction") == construction
    ]
    if matched:
        return "PRESENT_NATIVE_SAMPLING", sorted({r["native_setting"] for r in matched if r.get("native_setting")})
    return "NOT_EXPLICITLY_IDENTIFIED", []


def _named_contract_present(rows: list[dict[str, str]], base_symbol: str, venue: str) -> bool:
    root = base_symbol.rstrip("1!")
    for r in rows:
        sym = r["symbol"]
        if sym == base_symbol or (r.get("venue") or "").upper() != venue.upper():
            continue
        if sym.startswith(root) and not sym.endswith("1!"):
            return True
    return False


def build(manifest_rows: list[dict[str, str]], probe_rows: list[dict[str, str]]) -> dict:
    families, geometries = _identity_maps(manifest_rows, probe_rows)
    matrix = []
    gaps = []

    for asset, spec in EXECUTION.items():
        symbol = spec["symbol"]
        row = {
            "asset": asset,
            "symbol": symbol,
            "venue": spec["venue"],
        }
        for claim in sorted(set(spec["required_standard"] + ["240"])):
            status, sources = _status(
                manifest_rows, families, geometries, symbol, spec["venue"], claim,
                "regular_candles", "standard_ohlc"
            )
            key = f"standard_{claim}"
            row[key] = status
            row[f"{key}_basis"] = "observed_cadence_not_filename_claim"
            row[f"{key}_sources"] = " | ".join(sources)
            if claim in spec["required_standard"] and status != "PROVED_PRESENT":
                gaps.append({
                    "asset": asset,
                    "requirement": f"regular_candles:{claim}",
                    "status": status,
                    "priority": "P0" if asset == "NQ" else "P1",
                })

        for claim in spec["ha"]:
            status, sources = _status(
                manifest_rows, families, geometries, symbol, spec["venue"], claim,
                "heikin_ashi", "heikin_ashi"
            )
            row[f"ha_{claim}"] = status
            row[f"ha_{claim}_basis"] = "observed_cadence_not_filename_claim"
            row[f"ha_{claim}_sources"] = " | ".join(sources)
            if status != "PROVED_PRESENT":
                gaps.append({
                    "asset": asset,
                    "requirement": f"heikin_ashi:{claim}",
                    "status": status,
                    "priority": "P0" if asset == "NQ" else "P1",
                })

        for construction in ("tick", "range"):
            status, settings = _sampling(manifest_rows, symbol, spec["venue"], construction)
            row[f"{construction}_sampling"] = status
            row[f"{construction}_settings"] = " | ".join(settings)

        if asset == "BTCUSD":
            row["named_contract_present"] = "N/A"
            row["spot_venue_present"] = (
                "YES" if any(
                    r["symbol"] == symbol
                    and (r.get("venue") or "").upper() == spec["venue"].upper()
                    for r in manifest_rows
                ) else "NO"
            )
        else:
            named = _named_contract_present(manifest_rows, symbol, spec["venue"])
            row["named_contract_present"] = "YES" if named else "NO"
            row["spot_venue_present"] = "N/A"
            if not named:
                gaps.append({
                    "asset": asset,
                    "requirement": "named_front_next_contract_and_roll_metadata",
                    "status": "MISSING",
                    "priority": "P1",
                })

        row["historical_session_metadata"] = "UNRESOLVED_IN_ARCHIVE_METADATA"
        if asset != "BTCUSD":
            gaps.append({
                "asset": asset,
                "requirement": "session_and_roll_provenance",
                "status": "UNRESOLVED",
                "priority": "P1",
            })

        micro = spec.get("micro")
        if micro:
            micro_present = any(
                (r["symbol"] == micro or r["symbol"].startswith(micro))
                and (r.get("venue") or "").upper() == spec["venue"].upper()
                for r in manifest_rows
            )
            row["micro"] = micro
            row["micro_present"] = "YES" if micro_present else "NO"
            if not micro_present:
                gaps.append({
                    "asset": asset,
                    "requirement": f"micro_contract:{micro}",
                    "status": "MISSING",
                    "priority": "P1",
                })
        else:
            row["micro"] = ""
            row["micro_present"] = "N/A"

        matrix.append(row)

    return {
        "schema": "icarus.o14-coverage-matrix.v3",
        "matrix": matrix,
        "gaps": gaps,
        "gap_counts": {
            "total": len(gaps),
            "missing": sum(g["status"] == "MISSING" for g in gaps),
            "unresolved": sum(g["status"] != "MISSING" for g in gaps),
        },
        "rules": {
            "proved_present": "Requires exact symbol+venue, the requested chart/view family and price geometry, plus observed cadence within 5%; deterministic OHLC transform math proves geometry only, never view family.",
            "representation_unresolved": "Bytes may exist and geometry may be mathematically proved, but a family-specific O14 requirement stays open unless chart/view family is independently evidenced.",
            "bulk_reexport_required": False,
        },
        "production_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    manifest_rows = _read_csv(args.manifest)
    probe_rows = _read_csv(args.probe) if args.probe.exists() else []
    result = build(manifest_rows, probe_rows)

    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = result["matrix"]
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        if rows:
            fields = []
            for row in rows:
                for key in row:
                    if key not in fields:
                        fields.append(key)
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    print(json.dumps({"schema": result["schema"], "gap_counts": result["gap_counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
