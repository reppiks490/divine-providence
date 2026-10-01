"""Read-only CCTP V2 attestation visibility observations for research.

Receipt times are local observation times, never historical attestation times.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 10
HOSTS = {
    "mainnet": "https://iris-api.circle.com",
    "sandbox": "https://iris-api-sandbox.circle.com",
}
GENESIS = "0" * 64
TX_RE = re.compile(r"0x[0-9a-fA-F]{64}\Z")
# A single CCTP V2 attestation signature is 65 bytes (r, s, v).
# Longer strings may contain multiple concatenated signatures.
ATTESTATION_RE = re.compile(r"0x(?:[0-9a-fA-F]{130})+\Z")


def validate_query(domain: int, transaction_hash: str) -> tuple[int, str]:
    if type(domain) is not int or not 0 <= domain <= 2**32 - 1:
        raise ValueError("source domain must be an integer in [0, 2^32-1]")
    if not isinstance(transaction_hash, str) or not TX_RE.fullmatch(transaction_hash):
        raise ValueError("transaction hash must be 0x followed by 64 hex digits")
    return domain, transaction_hash.lower()


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("expected an ISO 8601 timestamp with timezone") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must have a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _identity(environment: str, domain: int, tx: str, received_at: str,
              http_status: int, synthetic: bool, raw_digest: str) -> str:
    values = [environment, domain, tx, received_at, http_status, int(synthetic), raw_digest]
    return _digest(json.dumps(values, separators=(",", ":")).encode("utf-8"))


def _connection(path: str | Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        environment TEXT NOT NULL,
        source_domain INTEGER NOT NULL,
        transaction_hash TEXT NOT NULL,
        received_at TEXT NOT NULL,
        http_status INTEGER NOT NULL,
        synthetic INTEGER NOT NULL,
        raw_response BLOB NOT NULL,
        raw_sha256 TEXT NOT NULL,
        identity_sha256 TEXT NOT NULL UNIQUE,
        prev_sha256 TEXT NOT NULL,
        row_sha256 TEXT NOT NULL
    )""")
    db.execute("""CREATE TRIGGER IF NOT EXISTS snapshots_no_update
        BEFORE UPDATE ON snapshots BEGIN SELECT RAISE(ABORT, 'snapshots are append-only'); END""")
    db.execute("""CREATE TRIGGER IF NOT EXISTS snapshots_no_delete
        BEFORE DELETE ON snapshots BEGIN SELECT RAISE(ABORT, 'snapshots are append-only'); END""")
    return db


def _verify_rows(db: sqlite3.Connection) -> int:
    previous = GENESIS
    count = 0
    for row in db.execute("SELECT * FROM snapshots ORDER BY seq"):
        count += 1
        if row["seq"] != count or row["prev_sha256"] != previous:
            raise ValueError(f"snapshot chain broken at row {count}")
        try:
            domain, tx = validate_query(row["source_domain"], row["transaction_hash"])
            stamp = _utc(row["received_at"])
        except ValueError as exc:
            raise ValueError(f"invalid snapshot metadata at row {count}") from exc
        if (row["environment"] not in HOSTS or tx != row["transaction_hash"]
                or stamp != row["received_at"] or row["synthetic"] not in (0, 1)
                or type(row["http_status"]) is not int or not 100 <= row["http_status"] <= 599):
            raise ValueError(f"invalid snapshot metadata at row {count}")
        raw_hash = _digest(row["raw_response"])
        identity = _identity(row["environment"], domain, tx, stamp,
                             row["http_status"], bool(row["synthetic"]), raw_hash)
        expected = _digest(f"{previous}:{identity}".encode("ascii"))
        if (raw_hash != row["raw_sha256"] or identity != row["identity_sha256"]
                or expected != row["row_sha256"]):
            raise ValueError(f"snapshot content tampered at row {count}")
        previous = expected
    return count


def verify(path: str | Path) -> dict:
    if not Path(path).is_file():
        raise FileNotFoundError(f"snapshot database does not exist: {path}")
    with closing(_connection(path)) as db, db:
        count = _verify_rows(db)
        final = db.execute("SELECT row_sha256 FROM snapshots ORDER BY seq DESC LIMIT 1").fetchone()
    return {"ok": True, "rows": count, "head_sha256": final[0] if final else GENESIS}


def append_snapshot(path: str | Path, *, environment: str, source_domain: int,
                    transaction_hash: str, received_at: str, http_status: int,
                    raw_response: bytes, synthetic: bool = True) -> dict:
    """Append a synthetic fixture; caller-supplied bytes cannot claim HTTP provenance."""
    if synthetic is not True:
        raise ValueError("caller-supplied snapshots must be synthetic")
    return _append_snapshot(path, environment=environment, source_domain=source_domain,
                            transaction_hash=transaction_hash, received_at=received_at,
                            http_status=http_status, raw_response=raw_response, synthetic=True)


def _append_snapshot(path: str | Path, *, environment: str, source_domain: int,
                     transaction_hash: str, received_at: str, http_status: int,
                     raw_response: bytes, synthetic: bool) -> dict:
    domain, tx = validate_query(source_domain, transaction_hash)
    if environment not in HOSTS or type(http_status) is not int or not 100 <= http_status <= 599:
        raise ValueError("invalid environment or HTTP status")
    if type(synthetic) is not bool or not isinstance(raw_response, bytes) or len(raw_response) > MAX_RESPONSE_BYTES:
        raise ValueError("invalid synthetic flag or response bytes")
    stamp = _utc(received_at)
    raw_hash = _digest(raw_response)
    identity = _identity(environment, domain, tx, stamp, http_status, synthetic, raw_hash)
    with closing(_connection(path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        _verify_rows(db)
        existing = db.execute("SELECT seq, row_sha256 FROM snapshots WHERE identity_sha256=?", (identity,)).fetchone()
        if existing:
            return {"seq": existing["seq"], "row_sha256": existing["row_sha256"], "duplicate": True}
        head = db.execute("SELECT row_sha256 FROM snapshots ORDER BY seq DESC LIMIT 1").fetchone()
        previous = head[0] if head else GENESIS
        row_hash = _digest(f"{previous}:{identity}".encode("ascii"))
        cursor = db.execute("""INSERT INTO snapshots
            (environment, source_domain, transaction_hash, received_at, http_status,
             synthetic, raw_response, raw_sha256, identity_sha256, prev_sha256, row_sha256)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (environment, domain, tx, stamp, http_status, int(synthetic),
             raw_response, raw_hash, identity, previous, row_hash))
        return {"seq": cursor.lastrowid, "row_sha256": row_hash, "duplicate": False}


def fetch(path: str | Path, *, environment: str, source_domain: int,
          transaction_hash: str) -> dict:
    domain, tx = validate_query(source_domain, transaction_hash)
    if environment not in HOSTS:
        raise ValueError("environment must be mainnet or sandbox")
    url = f"{HOSTS[environment]}/v2/messages/{domain}?transactionHash={tx}"
    request = Request(url, headers={"Accept": "application/json", "Accept-Encoding": "identity"}, method="GET")
    try:
        response = urlopen(request, timeout=TIMEOUT_SECONDS)
    except HTTPError as exc:
        response = exc
    with response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        received = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        status = response.status
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("Circle response exceeds size limit; snapshot not recorded")
    return _append_snapshot(path, environment=environment, source_domain=domain,
                            transaction_hash=tx, received_at=received,
                            http_status=status, raw_response=raw, synthetic=False)


def _status(row: sqlite3.Row) -> dict:
    if row["http_status"] != 200:
        return {"state": "http_error", "messages": []}
    try:
        def distinct_keys(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result

        payload = json.loads(row["raw_response"].decode("utf-8"), object_pairs_hook=distinct_keys)
        if not isinstance(payload, dict) or not isinstance(payload.get("messages"), list):
            raise ValueError("missing messages")
        source = payload.get("sourceTxHash")
        if not isinstance(source, str) or source.lower() != row["transaction_hash"]:
            raise ValueError("wrong source transaction")
        messages = []
        seen = set()
        for message in payload["messages"]:
            if not isinstance(message, dict) or message.get("cctpVersion") != 2:
                raise ValueError("not a CCTP V2 message")
            nonce = message.get("eventNonce")
            if not isinstance(nonce, str) or not nonce or nonce in seen:
                raise ValueError("missing or duplicate event nonce")
            seen.add(nonce)
            decoded = message.get("decodedMessage")
            if decoded is not None and (not isinstance(decoded, dict)
                                        or decoded.get("sourceDomain") != str(row["source_domain"])):
                raise ValueError("wrong decoded source domain")
            status = message.get("status")
            if not isinstance(status, str):
                raise ValueError("missing message status")
            if status == "complete":
                attestation = message.get("attestation")
                if not isinstance(attestation, str) or not ATTESTATION_RE.fullmatch(attestation):
                    raise ValueError("complete without attestation bytes")
                state = "attestation_available"
            elif status == "pending_confirmations":
                state = "pending"
            else:
                state = "unknown"
            messages.append({"event_nonce": nonce, "provider_status": status,
                             "state": state, "destination_mint_proven": False})
        return {"state": "observed" if messages else "no_messages", "messages": messages}
    except (UnicodeError, ValueError, TypeError, KeyError):
        return {"state": "invalid_response", "messages": []}


def timeline(path: str | Path, *, environment: str, source_domain: int,
             transaction_hash: str, as_of: str | None = None) -> list[dict]:
    domain, tx = validate_query(source_domain, transaction_hash)
    if environment not in HOSTS:
        raise ValueError("environment must be mainnet or sandbox")
    if not Path(path).is_file():
        raise FileNotFoundError(f"snapshot database does not exist: {path}")
    cutoff = _utc(as_of) if as_of is not None else None
    with closing(_connection(path)) as db, db:
        _verify_rows(db)
        rows = db.execute("""SELECT * FROM snapshots WHERE environment=?
            AND source_domain=? AND transaction_hash=? ORDER BY received_at, seq""",
            (environment, domain, tx)).fetchall()
    return [{"seq": row["seq"], "received_at": row["received_at"],
             "synthetic": bool(row["synthetic"]), "evidence": "SYNTHETIC" if row["synthetic"] else "CIRCLE_HTTP",
             "http_status": row["http_status"], "raw_sha256": row["raw_sha256"],
             **_status(row)} for row in rows if cutoff is None or row["received_at"] <= cutoff]


def asof(path: str | Path, *, environment: str, source_domain: int,
         transaction_hash: str, decision_time: str) -> dict:
    observations = timeline(path, environment=environment, source_domain=source_domain,
                            transaction_hash=transaction_hash, as_of=decision_time)
    latest = observations[-1] if observations else None
    return {"decision_time": _utc(decision_time), "basis": "local receipt time only",
            "historical_availability_proven": False,
            "destination_mint_proven": False, "observation": latest}
