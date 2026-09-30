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
    "BTCUSD": {"symbol": "BTCUSD", "venue": "NAMED_SPOT", "required_standard": ["1", "20", "60", "1D"], "ha": ["20"], "micro": None},
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


def _family_map(manifest_rows: list[dict[str, str]], probe_rows: list[dict[str, str]]) -> dict[str, str]:
    family: dict[str, str] = {}
    evidence: dict[str, str] = {}

    for row in manifest_rows:
        sha = row["raw_sha256"]
        archive_name = Path(row["archive_path"]).name
        claimed = row.get("representation_family") or "unknown"
        if archive_name == KNOWN_REGULAR_ARCHIVE or archive_name in DOCUMENTED_REGULAR_ARCHIVES:
            family[sha] = "regular_candles"
            evidence[sha] = "known/documented regular-candle archive"
        elif claimed not in {"", "unknown", "time_bars_unspecified", "tick_bars", "range_bars"}:
            family[sha] = claimed
            evidence[sha] = "explicit representation claim"

    # Exact-byte copies may inherit a proved family. Never infer across merely
    # similar rows or filenames.
    changed = True
    while changed:
        changed = False
        for row in manifest_rows:
            sha = row["raw_sha256"]
            if sha in family:
                continue
            dup_path = row.get("byte_duplicate_of") or ""
            if not dup_path:
                continue
            parent = next((x for x in manifest_rows if x["source_path"] == dup_path), None)
            if parent and parent["raw_sha256"] in family:
                family[sha] = family[parent["raw_sha256"]]
                evidence[sha] = "exact-byte family propagation"
                changed = True

    for row in probe_rows:
        proved = row.get("proved_family") or ""
        sha = row.get("raw_sha256") or ""
        if proved in {"regular_candles", "heikin_ashi"} and sha:
            old = family.get(sha)
            if old and old != proved:
                # A mathematical contradiction is surfaced instead of silently
                # choosing one label.
                family[sha] = f"CONFLICT:{old}:{proved}"
                evidence[sha] = "family conflict between source claim and transform proof"
            else:
                family[sha] = proved
                evidence[sha] = row.get("proof") or "transform proof"

    return family


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


def _status(rows: list[dict[str, str]], families: dict[str, str], symbol: str, claim: str, wanted_family: str) -> tuple[str, list[str]]:
    # Timeframe coverage is based on observed cadence, never filename text alone.
    matched = [r for r in rows if r["symbol"] == symbol and _cadence_matches(r, claim)]
    proved = [r for r in matched if families.get(r["raw_sha256"]) == wanted_family]
    if proved:
        return "PROVED_PRESENT", sorted({r["source_path"] for r in proved})
    if matched:
        return "PRESENT_REPRESENTATION_UNRESOLVED", sorted({r["source_path"] for r in matched})
    return "MISSING", []


def _sampling(rows: list[dict[str, str]], symbol: str, construction: str) -> tuple[str, list[str]]:
    matched = [r for r in rows if r["symbol"] == symbol and r.get("construction") == construction]
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
    families = _family_map(manifest_rows, probe_rows)
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
            status, sources = _status(manifest_rows, families, symbol, claim, "regular_candles")
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
            status, sources = _status(manifest_rows, families, symbol, claim, "heikin_ashi")
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
            status, settings = _sampling(manifest_rows, symbol, construction)
            row[f"{construction}_sampling"] = status
            row[f"{construction}_settings"] = " | ".join(settings)

        named = _named_contract_present(manifest_rows, symbol, spec["venue"]) if asset != "BTCUSD" else True
        row["named_contract_present"] = "YES" if named else "NO"
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
        "schema": "icarus.o14-coverage-matrix.v1",
        "matrix": matrix,
        "gaps": gaps,
        "gap_counts": {
            "total": len(gaps),
            "missing": sum(g["status"] == "MISSING" for g in gaps),
            "unresolved": sum(g["status"] != "MISSING" for g in gaps),
        },
        "rules": {
            "proved_present": "Requires a known/documented regular archive, exact-byte propagation, explicit family evidence, or deterministic standard/HA transform proof; time-based requirement matching uses observed cadence within 5%, never filename text alone.",
            "representation_unresolved": "Bytes exist but chart family is not safely established; do not count as satisfying a family-specific requirement.",
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
