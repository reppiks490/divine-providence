"""Real owned corpus and official announcement ingestion; no invented evidence."""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import subprocess
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

from .common import digest, now, PROTOCOL

FEEDS = {
    "federal_reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "ecb": "https://www.ecb.europa.eu/rss/press.html",
    "sec": "https://www.sec.gov/news/pressreleases.rss",
}
MAX_MEMBER_BYTES = 12_000_000
MAX_ARCHIVE_BYTES = 250_000_000
MAX_FEED_BYTES = 1_000_000
MAX_DECOMPRESSED_BYTES = 2_000_000_000


def fetch(url, limit, opener=urlopen):
    if urlsplit(url).scheme != "https":
        raise ValueError("Sources require HTTPS")
    req = Request(url, headers={"User-Agent": "ICARUS-research/1.0 github.com/reppiks490/divine-providence"})
    with opener(req, timeout=25) as response:
        if urlsplit(response.geturl()).scheme != "https":
            raise ValueError("Source redirected outside HTTPS")
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Source response exceeds bounded limit")
    return raw


def announcements(fetcher=fetch):
    events, receipts = [], []
    for name, url in FEEDS.items():
        observed = now()
        try:
            raw = fetcher(url, MAX_FEED_BYTES)
            if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
                raise ValueError("Feed XML declarations are not allowed")
            xml = ET.fromstring(raw)
            count = 0
            for item in xml.findall("./channel/item")[:30]:
                title, link = (item.findtext(k, "").strip() for k in ("title", "link"))
                if not title or not link or urlsplit(link).scheme != "https":
                    continue
                event = {"source": name, "source_url": url, "title": title[:500], "url": link[:2000],
                         "published_at_source": item.findtext("pubDate", "")[:100],
                         "first_observed_at": observed, "price_effect": "untested",
                         "availability_rule": "usable only from first observation; no retrospective event backtest"}
                event["id"] = digest({k: event[k] for k in ("source", "title", "url", "published_at_source")})
                events.append(event)
                count += 1
            if not count:
                raise ValueError("Feed contains no usable announcements")
            receipts.append({"source": name, "url": url, "observed_at": observed, "state": "observed",
                             "sha256": hashlib.sha256(raw).hexdigest(), "events": count})
        except Exception as exc:
            receipts.append({"source": name, "url": url, "observed_at": observed,
                             "state": "unavailable", "diagnostic": type(exc).__name__})
    return events, receipts


def safe_member(info):
    # On Windows ZipInfo normalizes backslashes in ``filename`` before callers
    # see it. Retain the raw archive name when checking for unsafe separators.
    raw_name = getattr(info, "orig_filename", info.filename)
    path = PurePosixPath(raw_name)
    return (not info.is_dir() and not path.is_absolute() and ".." not in path.parts
            and "\\" not in raw_name and "__MACOSX" not in path.parts
            and not path.name.startswith("._") and path.suffix.lower() == ".csv"
            and 0 < info.file_size <= MAX_MEMBER_BYTES and not info.flag_bits & 1
            and (info.external_attr >> 16) & 0o170000 != 0o120000)


def catalogue(roots):
    """Read full members, deduplicate bytes, and keep locators; never extract paths."""
    sources, receipts, seen = [], [], set()
    decompressed = 0
    for root in roots:
        root = Path(root).resolve()
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                  check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root,
                                check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        if not remote.startswith("https://github.com/reppiks490/"):
            raise ValueError("Corpus must be an owned public GitHub source")
        counts = {"archives": 0, "usable": 0, "deferred": 0, "duplicates": 0}
        total = 0
        for archive in sorted(root.rglob("*.zip")):
            if archive.is_symlink() or archive.stat().st_size > MAX_ARCHIVE_BYTES:
                raise ValueError("Invalid archive size or path")
            total += archive.stat().st_size
            if total > MAX_ARCHIVE_BYTES:
                raise ValueError("Corpus archive budget exceeded")
            counts["archives"] += 1
            with zipfile.ZipFile(archive) as z:
                if len(z.infolist()) > 5000:
                    raise ValueError("Archive member budget exceeded")
                for info in z.infolist():
                    if not safe_member(info):
                        continue
                    decompressed += info.file_size
                    if decompressed > MAX_DECOMPRESSED_BYTES:
                        raise ValueError("Corpus decompression budget exceeded")
                    raw = z.read(info)
                    if len(raw) != info.file_size:
                        raise ValueError("Archive member size mismatch")
                    # CSV parsing/quality is owned by DAEDALUS. Newline count is
                    # only a conservative budget filter, never scientific evidence.
                    rows = len(raw.splitlines()) - 1
                    if not PROTOCOL["source_rows"][0] <= rows <= PROTOCOL["source_rows"][1]:
                        counts["deferred"] += 1
                        continue
                    sha = hashlib.sha256(raw).hexdigest()
                    if sha in seen:
                        counts["duplicates"] += 1
                        continue
                    seen.add(sha)
                    counts["usable"] += 1
                    sources.append({"sha256": sha, "repository_url": remote.removesuffix(".git"),
                                    "revision": revision, "archive": str(archive.relative_to(root)),
                                    "member": info.filename, "rows_budget_estimate": rows,
                                    "bytes": len(raw), "label": PurePosixPath(info.filename).name,
                                    "identity_status": "filename_hint_unverified", "price_basis": "CANDLE_PROXY",
                                    "_archive_path": str(archive)})
        receipts.append({"repository_url": remote.removesuffix(".git"), "revision": revision, **counts})
    return sorted(sources, key=lambda s: s["sha256"]), receipts


def materialize(source, destination):
    with zipfile.ZipFile(source["_archive_path"]) as z:
        info = z.getinfo(source["member"])
        if not safe_member(info):
            raise ValueError("Invalid selected archive member")
        raw = z.read(info)
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise ValueError("Source changed since discovery")
    Path(destination).write_bytes(raw)
