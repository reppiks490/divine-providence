import io
import json
import sqlite3
from urllib.error import HTTPError

import pytest

from divine_providence import onchain_research as clock


TX = "0x" + "a" * 64
EARLY = "2026-01-01T00:00:00Z"
LATE = "2026-01-01T01:00:00Z"
QUERY = {"environment": "sandbox", "source_domain": 3, "transaction_hash": TX}
ATTESTATION = "0x" + "12" * 65


def body(status, *, attestation=None):
    message = {"cctpVersion": 2, "eventNonce": "42", "status": status,
               "decodedMessage": {"sourceDomain": "3"}}
    if attestation is not None:
        message["attestation"] = attestation
    return json.dumps({"sourceTxHash": TX, "messages": [message]}).encode()


def add(path, when, raw, *, status=200, synthetic=True):
    return clock.append_snapshot(path, **QUERY, received_at=when, http_status=status,
                                 raw_response=raw, synthetic=synthetic)


def test_asof_excludes_later_revised_status_and_marks_synthetic(tmp_path):
    db = tmp_path / "clock.sqlite"
    first = add(db, EARLY, body("pending_confirmations"))
    second = add(db, LATE, body("complete", attestation=ATTESTATION))
    assert first["duplicate"] is False and second["duplicate"] is False
    assert add(db, EARLY, body("pending_confirmations"))["duplicate"] is True
    assert clock.verify(db)["rows"] == 2
    earlier = clock.asof(db, **QUERY, decision_time="2026-01-01T00:30:00Z")
    assert earlier["observation"]["messages"][0]["state"] == "pending"
    assert earlier["observation"]["received_at"].startswith("2026-01-01T00:00:00")
    assert earlier["observation"]["evidence"] == "SYNTHETIC"
    assert earlier["historical_availability_proven"] is False
    assert earlier["destination_mint_proven"] is False
    later = clock.asof(db, **QUERY, decision_time=LATE)
    assert later["observation"]["messages"][0]["state"] == "attestation_available"
    assert later["observation"]["messages"][0]["destination_mint_proven"] is False
    assert clock.asof(db, **QUERY, decision_time="2025-12-31T23:59:59Z")["observation"] is None


def test_verify_detects_content_tamper(tmp_path):
    db = tmp_path / "clock.sqlite"
    add(db, EARLY, body("pending_confirmations"))
    add(db, LATE, body("complete", attestation=ATTESTATION))
    with sqlite3.connect(db) as connection:
        connection.execute("DROP TRIGGER snapshots_no_update")
        connection.execute("UPDATE snapshots SET raw_response=? WHERE seq=1", (body("complete", attestation=ATTESTATION),))
    with pytest.raises(ValueError, match="tampered"):
        clock.verify(db)
    with pytest.raises(ValueError, match="tampered"):
        clock.asof(db, **QUERY, decision_time=LATE)


def test_same_payload_at_new_receipt_is_a_new_observation(tmp_path):
    db = tmp_path / "clock.sqlite"
    raw = body("pending_confirmations")
    assert add(db, EARLY, raw)["duplicate"] is False
    assert add(db, LATE, raw)["duplicate"] is False
    assert clock.verify(db)["rows"] == 2


@pytest.mark.parametrize("raw,status,expected", [
    (b"not json", 200, "invalid_response"),
    (body("complete"), 200, "invalid_response"),
    (body("settled", attestation=ATTESTATION), 200, "unknown"),
    (body("pending_confirmations", attestation="PENDING"), 200, "pending"),
    (body("complete", attestation=ATTESTATION), 429, "http_error"),
    (body("complete", attestation="0x12"), 200, "invalid_response"),
    (b'{"sourceTxHash":"' + TX.encode() + b'","messages":[],"messages":[]}', 200, "invalid_response"),
    (json.dumps({"sourceTxHash": "0x" + "b" * 64,
                 "messages": [{"cctpVersion": 2, "eventNonce": "42", "status": "complete",
                               "attestation": ATTESTATION}]}).encode(), 200, "invalid_response"),
])
def test_fail_closed_provider_and_http_status(tmp_path, raw, status, expected):
    db = tmp_path / "clock.sqlite"
    add(db, EARLY, raw, status=status)
    observation = clock.timeline(db, **QUERY)[0]
    actual = observation["messages"][0]["state"] if observation["messages"] else observation["state"]
    assert actual == expected
    assert actual != "attestation_available"


def test_strict_query_validation(tmp_path):
    for domain, tx in [(-1, TX), (True, TX), ("3", TX), (3, "0xabc"), (3, TX + "?nonce=1")]:
        with pytest.raises(ValueError):
            clock.fetch(tmp_path / "clock.sqlite", environment="sandbox",
                        source_domain=domain, transaction_hash=tx)


def test_caller_cannot_forge_circle_http_history(tmp_path):
    db = tmp_path / "clock.sqlite"
    with pytest.raises(ValueError, match="synthetic"):
        clock.append_snapshot(db, **QUERY, received_at="2020-01-01T00:00:00Z",
                              http_status=200,
                              raw_response=body("complete", attestation=ATTESTATION),
                              synthetic=False)
    assert not db.exists()


def test_fetch_captures_exact_http_error_bytes_without_network(tmp_path, monkeypatch):
    db = tmp_path / "clock.sqlite"
    raw = b'{"status":"complete"}\n'

    def fake_urlopen(request, timeout):
        assert request.full_url == f"https://iris-api-sandbox.circle.com/v2/messages/3?transactionHash={TX}"
        assert request.get_method() == "GET" and timeout == clock.TIMEOUT_SECONDS
        raise HTTPError(request.full_url, 429, "rate limited", {}, io.BytesIO(raw))

    monkeypatch.setattr(clock, "urlopen", fake_urlopen)
    clock.fetch(db, **QUERY)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT raw_response FROM snapshots").fetchone()[0] == raw
    observation = clock.timeline(db, **QUERY)[0]
    assert observation["state"] == "http_error"
    assert observation["synthetic"] is False
    assert observation["evidence"] == "CIRCLE_HTTP"


def test_response_size_bound(tmp_path, monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def read(self, size):
            assert size == clock.MAX_RESPONSE_BYTES + 1
            return b"x" * size

    monkeypatch.setattr(clock, "urlopen", lambda *_args, **_kwargs: Response())
    db = tmp_path / "clock.sqlite"
    with pytest.raises(ValueError, match="size limit"):
        clock.fetch(db, **QUERY)
    assert not db.exists()
