from oracle.contracts import EvidenceRecord, FinancialState, ResearchJob
from oracle.engine import OracleEngine
from oracle.automation import AutonomousResearchLoop
from oracle.hypothesis_factory import Trigger
from oracle.scheduler import ResearchScheduler
from oracle.persistence import sqlite_connection
import sqlite3
import pytest


def test_assessment_excludes_future_received_evidence_and_reworded_votes(tmp_path):
    engine = OracleEngine(tmp_path / "oracle.db")
    h = engine.ingest_trigger(Trigger("test", 1, "source", 1, 0, {}))
    evidence = EvidenceRecord("e", h.hypothesis_id, "AION", "historical_analogue", 2,
                              {}, "a" * 64, .2, True)
    engine.contribute(h.hypothesis_id, evidence, claim="first wording", submitted_ns=10)
    assert engine.assess(h.hypothesis_id, assessed_ns=5).support_score == 0
    engine.contribute(h.hypothesis_id, evidence, claim="second wording", submitted_ns=11)
    assert engine.assess(h.hypothesis_id, assessed_ns=12).support_score == .2
    alias = EvidenceRecord("alias", h.hypothesis_id, "AION", "historical_analogue", 2,
                           {}, "a" * 64, .2, True)
    engine.contribute(h.hypothesis_id, alias, claim="same observation, another identifier", submitted_ns=13)
    assert engine.assess(h.hypothesis_id, assessed_ns=14).support_score == .2


def test_exchange_rejects_source_spoofing(tmp_path):
    engine = OracleEngine(tmp_path / "oracle.db")
    h = engine.ingest_trigger(Trigger("test", 1, "source", 1, 0, {}))
    e = EvidenceRecord("e", h.hypothesis_id, "AION", "historical_analogue", 2, {}, "a"*64, .2, True)
    qid = engine.question_by_hypothesis[h.hypothesis_id]
    with pytest.raises(ValueError):
        engine.exchange.contribute(qid, system="DAEDALUS", evidence=e, claim="spoof", submitted_ns=3)


def test_dispatch_rejects_future_financial_context(tmp_path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "o.db"))
    loop.set_financial_state(FinancialState("S100", 100, {}, .5, .5, {}))
    with pytest.raises(ValueError):
        loop.dispatch(50)
    assert loop.budget.consumed_compute == 0


def test_existing_scheduler_diversifies_immutable_jobs():
    s = ResearchScheduler()
    for key, cost in [("a", 1), ("b", 1), ("c", 1.1)]:
        s.submit(ResearchJob(key, key, "research", 1, 1, 1, 1, 1, 1, cost, ("DAEDALUS",)))
    original = dict(s._jobs)
    selected = s.rank(2, groups={"a": "same", "b": "same", "c": "other"}, limit=2)
    assert [j.job_id for j in selected] == ["a", "c"]
    assert s._jobs == original
    assert [j.job_id for j in s.rank(2)] == ["a", "b", "c"]


def test_owner_sqlite_connection_closes_after_error(tmp_path):
    with pytest.raises(RuntimeError):
        with sqlite_connection(tmp_path / "close.db") as con:
            raise RuntimeError("abort")
    with pytest.raises(sqlite3.ProgrammingError):
        con.execute("SELECT 1")
