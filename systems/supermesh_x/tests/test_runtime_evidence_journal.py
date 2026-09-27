
import pytest
from scripts.runtime_evidence_journal import EvidenceJournal, EvidenceError, normalize_resources, verify_termination_tree, ResolverPinSession

def test_hash_chain_detects_tamper_and_is_deterministic():
    j=EvidenceJournal("run-1")
    a=j.append("launch",{"pid":7,"provider":"x"})
    b=j.append("heartbeat",{"seq":1})
    assert b["prev_digest"]==a["digest"]
    assert j.verify()
    j._events[0]["payload"]["pid"]=8
    with pytest.raises(EvidenceError): j.verify()

def test_reconciliation_is_idempotent_and_fenced():
    j=EvidenceJournal("r")
    first=j.reconcile("w1",4,"destroy","lost-owner")
    again=j.reconcile("w1",4,"destroy","lost-owner")
    assert first==again
    with pytest.raises(EvidenceError): j.reconcile("w1",3,"adopt","stale")

def test_normalized_resources_reject_ambiguous_units():
    got=normalize_resources({"cpu_millicores":750,"memory_bytes":1048576,"storage_bytes":4096,"gpu_units":0})
    assert got["cpu_millicores"]==750
    with pytest.raises(EvidenceError): normalize_resources({"cpu":1,"memory_mb":512})

def test_termination_tree_requires_every_descendant_dead():
    assert verify_termination_tree(10,{10:False,11:False,12:False},[(10,11),(11,12)])["verified"]
    with pytest.raises(EvidenceError):
        verify_termination_tree(10,{10:False,11:True},[(10,11)])

def test_resolver_pin_session_blocks_rebinding_and_private_answers():
    s=ResolverPinSession("example.test",["93.184.216.34"])
    assert s.verify_connect("93.184.216.34")["allowed"]
    with pytest.raises(EvidenceError): s.verify_refresh(["127.0.0.1"])
    with pytest.raises(EvidenceError): s.verify_connect("93.184.216.35")

def test_journal_export_is_secret_safe():
    j=EvidenceJournal("r")
    with pytest.raises(EvidenceError): j.append("x",{"credential":"secretref://vault/a"})
