import os
from durable_journal import DurableProofJournal

def p(i): return {"intervention_id":i,"transaction_hash":"tx-"+i,"proof_envelope_hash":"env-"+i}

def test_clean_recovery_multiple_frames(tmp_path):
    j=DurableProofJournal(tmp_path/"proof.jnl"); j.append(p("a")); j.append(p("b"))
    r=j.recover(); assert r.clean and [x.payload["intervention_id"] for x in r.records]==["a","b"]
    assert r.last_good_offset==r.file_size

def test_truncated_payload_recovers_only_last_good(tmp_path):
    path=tmp_path/"proof.jnl"; j=DurableProofJournal(path); first=j.append(p("a")); j.append(p("b"))
    raw=path.read_bytes(); path.write_bytes(raw[:-7])
    r=j.recover(); assert r.tail_status=="truncated" and len(r.records)==1 and r.last_good_offset==first.end_offset

def test_checksum_corruption_detected(tmp_path):
    path=tmp_path/"proof.jnl"; j=DurableProofJournal(path); j.append(p("a"))
    raw=bytearray(path.read_bytes()); raw[-1]^=1; path.write_bytes(raw)
    r=j.recover(); assert r.tail_status=="corrupt" and "checksum" in r.reason and not r.records

def test_garbage_tail_detected(tmp_path):
    path=tmp_path/"proof.jnl"; j=DurableProofJournal(path); rec=j.append(p("a"))
    with path.open("ab") as f: f.write(b"garbage")
    r=j.recover(); assert r.tail_status=="truncated" and r.last_good_offset==rec.end_offset

def test_duplicate_intervention_is_not_clean(tmp_path):
    j=DurableProofJournal(tmp_path/"proof.jnl"); j.append(p("a")); j.append(p("a"))
    r=j.recover(); assert not r.clean and r.duplicate_interventions==("a",)

def test_quarantine_preserves_bad_tail_and_restores_clean_prefix(tmp_path):
    path=tmp_path/"proof.jnl"; q=tmp_path/"bad.tail"; j=DurableProofJournal(path); j.append(p("a")); j.append(p("b"))
    path.write_bytes(path.read_bytes()[:-9]); r=j.recover(); n=j.quarantine_tail(r,q)
    assert n>0 and q.stat().st_size==n
    rr=j.recover(); assert rr.clean and len(rr.records)==1

def test_empty_missing_journal_is_clean(tmp_path):
    r=DurableProofJournal(tmp_path/"missing").recover(); assert r.clean and r.records==() and r.last_good_offset==0

def test_no_mutation_authority_surface(tmp_path):
    j=DurableProofJournal(tmp_path/"proof.jnl")
    assert {"execute","mutate","promote","rollback","acquire","release"}.isdisjoint(set(dir(j)))
