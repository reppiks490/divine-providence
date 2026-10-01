"""Research-only inventory of CSV members without inferring market semantics."""
from __future__ import annotations

import csv
import argparse
import hashlib
import io
import json
import re
import stat
from collections import Counter
from pathlib import Path
from zipfile import ZipFile, ZipInfo


MAX_MEMBER_BYTES = 512_000_000


def _sha_stream(stream) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1 << 20), b""):
        digest.update(block)
    return digest.hexdigest()


def _is_sidecar(name: str) -> bool:
    parts = name.replace("\\", "/").split("/")
    return "__MACOSX" in parts or parts[-1].startswith("._")



def _representation_claim(member_name: str, headers: list[str], archive_name: str | None = None) -> dict:
    """Return non-authoritative, orthogonal chart-family and sampling claims."""
    norm = re.sub(r"[^a-z0-9]+", " ", member_name.lower()).strip()
    family = "unknown"
    price_geometry = "unknown"
    reasons: list[str] = []
    confidence = 0.0

    explicit = (
        (r"\bheikin\s+ashi\b", "heikin_ashi"),
        (r"\brenko\b", "renko"),
        (r"\btime\s+price\s+opportunity\b|\btpo\b", "tpo"),
        (r"\bvolume\s+footprint\b|\bfootprint\b", "volume_footprint"),
        (r"\bsession\s+volume\s+profile\b|\bsvp\b", "session_volume_profile"),
        (r"\bvolume\s+profile\b", "volume_profile"),
        (r"\bcandlestick\b|\bcandles\b|\bregular\s+candles\b", "regular_candles"),
    )
    for pattern, value in explicit:
        if re.search(pattern, norm):
            family = value
            confidence = 0.98
            reasons.append(f"explicit_{value}_label")
            if value == "regular_candles":
                price_geometry = "standard_ohlc"
            elif value == "heikin_ashi":
                price_geometry = "heikin_ashi"
            elif value == "renko":
                price_geometry = "renko"
            break

    documented_regular_archives = {
        "csv first 60.zip",
        "first 60 half.zip",
        "csv 2nd 60.zip",
        "2nd 60 half.zip",
        "csv last 57.zip",
        "last 57 half.zip",
    }
    if family == "unknown" and str(archive_name or "").lower() in documented_regular_archives:
        family = "regular_candles"
        price_geometry = "standard_ohlc"
        confidence = 0.95
        reasons.append("documented_stock_candle_tide_archive")

    base = member_name.replace("\\", "/").rsplit("/", 1)[-1]
    stem = base[:-4] if base.lower().endswith(".csv") else base
    claim = stem.rsplit(",", 1)[1].strip() if "," in stem else ""
    m = re.fullmatch(r"(\d+)([SDWMTR]?)(?:\s+\d+)?", claim, re.I)
    sampling_domain = "unknown"
    construction = "unknown"
    setting = claim.upper() or None
    if m:
        unit = (m.group(2) or "MIN").upper()
        if unit == "T":
            sampling_domain, construction = "event", "tick"
            reasons.append("explicit_tick_suffix")
        elif unit == "R":
            sampling_domain, construction = "event", "range"
            reasons.append("explicit_range_suffix")
        else:
            sampling_domain, construction = "time", "time_bar"
            reasons.append("explicit_time_sampling_claim")

    hs = {str(x).strip().lower() for x in headers}
    tags: list[str] = []
    if {"mp poc", "mp vah", "mp val"} & hs or {"poc", "vah", "val"}.issubset(hs):
        tags.append("market_profile_fields")
    if any(("delta" in h) or ("bid" in h and "ask" in h) for h in hs):
        tags.append("footprint_fields")
    if any("volume profile" in h for h in hs):
        tags.append("volume_profile_fields")
    if tags:
        reasons.append("profile_or_orderflow_fields_present")

    return {
        "family": family,
        "price_geometry": price_geometry,
        "sampling_domain": sampling_domain,
        "construction": construction,
        "setting": setting,
        "schema_tags": sorted(set(tags)),
        "confidence": confidence,
        "reasons": reasons or ["insufficient_explicit_representation_evidence"],
        "authoritative": False,
    }


def _profile_member(archive: ZipFile, info: ZipInfo, ordinal: int, archive_hash: str, archive_name: str = "") -> dict:
    identity = hashlib.sha256(
        json.dumps([archive_hash, ordinal, info.filename], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    record = {
        "physical_source_id": identity,
        "member_ordinal": ordinal,
        "member_name": info.filename,
        "member_bytes": info.file_size,
        "member_sha256": None,
        "headers": [],
        "duplicate_header_names": [],
        "data_rows": None,
        "status": "unread",
        "source_identity_verified": False,
        "availability_verified": False,
        "execution_authorized": False,
        "representation_claim": {
            "family": "unknown",
            "price_geometry": "unknown",
            "sampling_domain": "unknown",
            "construction": "unknown",
            "setting": None,
            "schema_tags": [],
            "confidence": 0.0,
            "reasons": ["unparsed"],
            "authoritative": False,
        },
    }
    if info.file_size > MAX_MEMBER_BYTES:
        record["status"] = "oversize"
        return record
    if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
        record["status"] = "symlink"
        return record
    try:
        with archive.open(info) as raw:
            record["member_sha256"] = _sha_stream(raw)
        with archive.open(info) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader)
            record["headers"] = [{"position": index, "name": name} for index, name in enumerate(header)]
            counts = Counter(header)
            record["duplicate_header_names"] = sorted(name for name, count in counts.items() if count > 1)
            record["data_rows"] = sum(1 for _ in reader)
            record["representation_claim"] = _representation_claim(info.filename, header, archive_name)
            record["status"] = "parsed"
    except (UnicodeError, csv.Error, EOFError, OSError, StopIteration, RuntimeError, ValueError) as exc:
        record["status"] = "parse_error"
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def scan_archives(paths: list[Path]) -> dict:
    """Return physical-lineage records; exact hashes only share compute, never identity."""
    archives = []
    members = []
    for path in sorted({p.expanduser().resolve() for p in paths}):
        with path.open("rb") as raw:
            archive_hash = _sha_stream(raw)
        with ZipFile(path) as archive:
            ignored = 0
            start = len(members)
            for ordinal, info in enumerate(archive.infolist()):
                if info.is_dir() or not info.filename.lower().endswith(".csv") or _is_sidecar(info.filename):
                    ignored += 1
                    continue
                members.append({
                    "archive_path": str(path),
                    "archive_sha256": archive_hash,
                    **_profile_member(archive, info, ordinal, archive_hash, path.name),
                })
            archives.append({
                "path": str(path), "sha256": archive_hash,
                "physical_csv_members": len(members) - start,
                "ignored_entries": ignored,
            })
    hashes = Counter(row["member_sha256"] for row in members if row["member_sha256"])
    return {
        "schema": "aion-parallax-inventory-v4",
        "research_only": True,
        "source_identity_verified": False,
        "availability_verified": False,
        "execution_authorized": False,
        "archives": archives,
        "members": members,
        "counts": {
            "physical_csv_members": len(members),
            "parsed_csv_members": sum(row["status"] == "parsed" for row in members),
            "unique_byte_contents": len(hashes),
            "records_in_exact_duplicate_groups": sum(hashes[row["member_sha256"]] > 1 for row in members if row["member_sha256"]),
            "logical_data_rows": sum(row["data_rows"] or 0 for row in members),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research-only Parallax CSV archive inventory")
    parser.add_argument("archives", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = scan_archives(args.archives)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
