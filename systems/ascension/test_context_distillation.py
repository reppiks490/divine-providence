"""Behavioural tests for ASCENSION Context Distillation Engine v0.1.

Replaces the v0.1 kit's placeholder file (which only referenced test_report.json
and collected zero tests).
"""
import copy
import hashlib
import json

import context_distillation as cd

RECORDS = [
    {"source_id": "s1", "authority_boundaries": ["no-execution"], "decisions": ["hold"],
     "contradictions": [], "dependencies": ["NEXUS"], "confidence": 0.7, "revalidation": "daily"},
    {"source_id": "s2", "authority_boundaries": ["no-execution"], "decisions": ["hold", "abstain"],
     "dependencies": "DAEDALUS", "confidence": [0.4]},
]


def test_packet_has_every_required_section_and_schema():
    p = cd.distill(RECORDS)
    for k in cd.REQUIRED:
        assert k in p
    assert p["schema_version"] == "0.1"
    assert p["source_ids"] == ["s1", "s2"]
    assert p["omissions"] == []


def test_provenance_digest_is_canonical_sha256_of_record():
    p = cd.distill(RECORDS)
    want = hashlib.sha256(json.dumps(RECORDS[0], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert p["provenance"][0] == {"source_id": "s1", "digest": want}
    shuffled = dict(reversed(list(RECORDS[0].items())))
    assert cd.distill([shuffled])["provenance"][0]["digest"] == want


def test_scalar_values_are_normalised_to_lists_and_attributed():
    p = cd.distill(RECORDS)
    assert {"source_id": "s2", "value": "DAEDALUS"} in p["dependencies"]
    assert {"source_id": "s1", "value": 0.7} in p["confidence"]
    assert {"source_id": "s1", "value": "daily"} in p["revalidation"]


def test_duplicates_within_a_source_collapse_but_cross_source_values_survive():
    recs = [{"source_id": "a", "decisions": ["x", "x"]}, {"source_id": "b", "decisions": ["x"]}]
    p = cd.distill(recs)
    assert p["decisions"] == [{"source_id": "a", "value": "x"}, {"source_id": "b", "value": "x"}]


def test_distillation_is_deterministic():
    assert cd.distill(copy.deepcopy(RECORDS)) == cd.distill(copy.deepcopy(RECORDS))


def test_own_output_is_loss_free():
    assert cd.audit_loss(RECORDS, cd.distill(RECORDS)) == {"loss_free": True, "losses": {}}


def test_dropped_decision_is_reported_as_loss():
    p = cd.distill(RECORDS)
    p["decisions"] = p["decisions"][1:]
    r = cd.audit_loss(RECORDS, p)
    assert r["loss_free"] is False
    assert r["losses"] == {"decisions": 1}


def test_tampered_provenance_digest_is_reported_as_loss():
    p = cd.distill(RECORDS)
    p["provenance"][1] = {"source_id": "s2", "digest": "0" * 64}
    assert cd.audit_loss(RECORDS, p)["losses"] == {"provenance": 1}


def test_missing_section_counts_every_expected_item():
    p = cd.distill(RECORDS)
    del p["authority_boundaries"]
    assert cd.audit_loss(RECORDS, p)["losses"] == {"authority_boundaries": 2}


def test_record_without_source_id_is_rejected():
    try:
        cd.distill([{"decisions": ["x"]}])
    except KeyError:
        return
    raise AssertionError("record without source_id must not be distilled")
