from __future__ import annotations

import argparse
import csv
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from nexus.archive import ZipCorpusCatalog
from nexus.timeutil import timestamp_to_ns


KNOWN_STANDARD_ARCHIVE = "Full csv candles only.zip"
MIN_OVERLAP = 200
MIN_COVERAGE = 0.80
PROOF_SCORE = 0.999


def _indexes(header: list[str]) -> dict[str, int | None]:
    lower = [str(x).strip().lower() for x in header]
    return {
        name: next((i for i, value in enumerate(lower) if value == name), None)
        for name in ("time", "open", "high", "low", "close")
    }


def _read_ohlc(path: Path, member: str) -> tuple[dict[int, tuple[float, float, float, float]], int]:
    rows: dict[int, tuple[float, float, float, float]] = {}
    repeated = 0
    with zipfile.ZipFile(path) as zf:
        with zf.open(member, "r") as raw:
            text = (line.decode("utf-8-sig", errors="replace") for line in raw)
            reader = csv.reader(text)
            header = next(reader, [])
            idx = _indexes(header)
            if any(idx[k] is None for k in ("time", "open", "high", "low", "close")):
                return {}, 0
            for row in reader:
                try:
                    ti = int(idx["time"])
                    ns, _ = timestamp_to_ns(row[ti])
                    values = tuple(float(row[int(idx[k])]) for k in ("open", "high", "low", "close"))
                    if not all(math.isfinite(x) for x in values):
                        continue
                except (ValueError, TypeError, IndexError):
                    continue
                if ns in rows:
                    repeated += 1
                rows[ns] = values
    return rows, repeated


def _tol(values: Iterable[float]) -> float:
    scale = max((abs(float(x)) for x in values), default=1.0)
    return max(1e-9, scale * 1e-9)


def _same(a: float, b: float, values: Iterable[float]) -> bool:
    return abs(float(a) - float(b)) <= _tol(values)


def _compare(
    standard: dict[int, tuple[float, float, float, float]],
    candidate: dict[int, tuple[float, float, float, float]],
) -> dict:
    common = sorted(set(standard).intersection(candidate))
    denominator = max(1, min(len(standard), len(candidate)))
    coverage = len(common) / denominator
    if len(common) < MIN_OVERLAP or coverage < MIN_COVERAGE:
        return {
            "overlap": len(common),
            "coverage": coverage,
            "standard_score": 0.0,
            "ha_close_high_low_score": 0.0,
            "ha_open_recurrence_score": 0.0,
            "ha_score": 0.0,
        }

    standard_ok = 0
    ha_chl_ok = 0
    for ts in common:
        so, sh, sl, sc = standard[ts]
        co, ch, cl, cc = candidate[ts]
        all_values = (so, sh, sl, sc, co, ch, cl, cc)
        if (
            _same(so, co, all_values)
            and _same(sh, ch, all_values)
            and _same(sl, cl, all_values)
            and _same(sc, cc, all_values)
        ):
            standard_ok += 1

        expected_close = (so + sh + sl + sc) / 4.0
        expected_high = max(sh, co, cc)
        expected_low = min(sl, co, cc)
        if (
            _same(expected_close, cc, all_values)
            and _same(expected_high, ch, all_values)
            and _same(expected_low, cl, all_values)
        ):
            ha_chl_ok += 1

    # Heikin-Ashi open is recursive: current HA open equals the midpoint of
    # the previous HA open and HA close. Validate it on the candidate's own
    # consecutive rows so timestamp overlap gaps cannot create a false proof.
    candidate_times = sorted(candidate)
    ha_open_ok = 0
    ha_open_total = max(0, len(candidate_times) - 1)
    for prev_ts, ts in zip(candidate_times, candidate_times[1:]):
        prev_o, _, _, prev_c = candidate[prev_ts]
        co, ch, cl, cc = candidate[ts]
        expected_open = (prev_o + prev_c) / 2.0
        if _same(expected_open, co, (prev_o, prev_c, co, ch, cl, cc)):
            ha_open_ok += 1

    standard_score = standard_ok / len(common)
    ha_chl_score = ha_chl_ok / len(common)
    ha_open_score = (ha_open_ok / ha_open_total) if ha_open_total else 0.0
    return {
        "overlap": len(common),
        "coverage": coverage,
        "standard_score": standard_score,
        "ha_close_high_low_score": ha_chl_score,
        "ha_open_recurrence_score": ha_open_score,
        "ha_score": min(ha_chl_score, ha_open_score),
    }


def probe(root: Path) -> dict:
    manifests = [
        m for m in ZipCorpusCatalog(root).build()
        if m.row_count > 0 and "appledouble" not in set(m.quality_flags)
    ]
    by_archive: dict[str, list] = defaultdict(list)
    for manifest in manifests:
        by_archive[str(manifest.metadata.get("archive_path") or "")].append(manifest)

    standard_manifests = [
        m for m in manifests
        if Path(str(m.metadata.get("archive_path") or "")).name == KNOWN_STANDARD_ARCHIVE
        and {"open", "high", "low", "close"}.issubset({str(c).strip().lower() for c in m.columns})
    ]
    standards_by_symbol: dict[str, list] = defaultdict(list)
    for manifest in standard_manifests:
        standards_by_symbol[manifest.identity.symbol].append(manifest)

    cache: dict[str, tuple[dict[int, tuple[float, float, float, float]], int]] = {}

    def load(manifest):
        key = manifest.identity.source_path
        if key not in cache:
            archive_rel = str(manifest.metadata["archive_path"])
            cache[key] = _read_ohlc(root / archive_rel, str(manifest.metadata["archive_member"]))
        return cache[key]

    output = []
    for candidate in manifests:
        archive_name = Path(str(candidate.metadata.get("archive_path") or "")).name
        if archive_name == KNOWN_STANDARD_ARCHIVE:
            continue
        headers = {str(c).strip().lower() for c in candidate.columns}
        if not {"open", "high", "low", "close"}.issubset(headers):
            continue

        crows, crepeats = load(candidate)
        if not crows or crepeats:
            output.append({
                "stream_id": candidate.identity.stream_id,
                "source_path": candidate.identity.source_path,
                "symbol": candidate.identity.symbol,
                "archive_path": str(candidate.metadata.get("archive_path") or ""),
                "archive_member": str(candidate.metadata.get("archive_member") or ""),
                "raw_sha256": candidate.identity.raw_sha256,
                "proved_price_geometry": None,
                "proof": "blocked_repeated_or_unreadable_timestamps" if crepeats else "no_ohlc_rows",
                "reference_stream_id": None,
                "overlap": 0,
                "coverage": 0.0,
                "standard_score": 0.0,
                "ha_close_high_low_score": 0.0,
                "ha_open_recurrence_score": 0.0,
                "ha_score": 0.0,
                "production_authorized": False,
            })
            continue

        best_standard = None
        best_ha = None
        for reference in standards_by_symbol.get(candidate.identity.symbol, []):
            rrows, rrepeats = load(reference)
            if not rrows or rrepeats:
                continue
            scores = _compare(rrows, crows)
            record = (scores["standard_score"], scores["coverage"], scores["overlap"], reference, scores)
            if best_standard is None or record[:3] > best_standard[:3]:
                best_standard = record
            hrecord = (scores["ha_score"], scores["coverage"], scores["overlap"], reference, scores)
            if best_ha is None or hrecord[:3] > best_ha[:3]:
                best_ha = hrecord

        proved_price_geometry = None
        proof = "no_price_geometry_proof"
        chosen = best_standard
        if best_standard and best_standard[0] >= PROOF_SCORE:
            proved_price_geometry = "standard_ohlc"
            proof = "overlapping_ohlc_equals_known_standard_geometry"
            chosen = best_standard
        elif best_ha and best_ha[0] >= PROOF_SCORE:
            proved_price_geometry = "heikin_ashi"
            proof = "overlapping_ohlc_satisfies_heikin_ashi_geometry"
            chosen = best_ha
        elif best_ha and (best_standard is None or best_ha[0] > best_standard[0]):
            chosen = best_ha

        scores = chosen[4] if chosen else {
            "overlap": 0, "coverage": 0.0, "standard_score": 0.0,
            "ha_close_high_low_score": 0.0, "ha_open_recurrence_score": 0.0,
            "ha_score": 0.0
        }
        ref = chosen[3] if chosen else None
        output.append({
            "stream_id": candidate.identity.stream_id,
            "source_path": candidate.identity.source_path,
            "symbol": candidate.identity.symbol,
            "archive_path": str(candidate.metadata.get("archive_path") or ""),
            "archive_member": str(candidate.metadata.get("archive_member") or ""),
            "raw_sha256": candidate.identity.raw_sha256,
            "proved_price_geometry": proved_price_geometry,
            "proof": proof,
            "reference_stream_id": ref.identity.stream_id if ref else None,
            "reference_source_path": ref.identity.source_path if ref else None,
            "overlap": int(scores["overlap"]),
            "coverage": float(scores["coverage"]),
            "standard_score": float(scores["standard_score"]),
            "ha_close_high_low_score": float(scores["ha_close_high_low_score"]),
            "ha_open_recurrence_score": float(scores["ha_open_recurrence_score"]),
            "ha_score": float(scores["ha_score"]),
            "production_authorized": False,
        })

    counts = defaultdict(int)
    for row in output:
        counts[row["proved_price_geometry"] or "unresolved"] += 1
    return {
        "schema": "nexus.o14-representation-probe.v3",
        "known_standard_archive": KNOWN_STANDARD_ARCHIVE,
        "thresholds": {
            "minimum_overlap": MIN_OVERLAP,
            "minimum_coverage": MIN_COVERAGE,
            "proof_score": PROOF_SCORE,
        },
        "counts": dict(sorted(counts.items())),
        "rows": output,
        "limitations": [
            "Only exact overlapping standard OHLC equality or deterministic Heikin-Ashi close/high/low plus recursive-open identities create a price-geometry proof.",
            "Standard OHLC geometry does not prove an ordinary-candlestick view: TPO, footprint or profile views can preserve standard OHLC while remaining distinct chart/view families.",
            "Heikin-Ashi geometry likewise does not prove the absence of an additional footprint/profile view layer.",
            "This probe never assigns TPO, footprint, session-volume-profile, Renko or other view-family identity without explicit source evidence.",
            "A geometry proof does not establish session, timezone, contract-roll, data entitlement or execution authorization.",
        ],
        "production_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    result = probe(args.root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows = result["rows"]
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    print(json.dumps({"schema": result["schema"], "counts": result["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
