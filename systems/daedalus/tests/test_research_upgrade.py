from dataclasses import replace
from pathlib import Path
import json
import sqlite3

import pandas as pd
import pytest

from daedalus.batch import run_batch
from daedalus.config import DaedalusConfig, ValidationConfig
from daedalus.splits import PurgedWalkForwardSplit
from daedalus.utils import sqlite_connection


def test_spread_folds_reach_recent_development_without_overlap():
    folds = PurgedWalkForwardSplit(5, 500, 250, 5, 5,
                                  placement="spread", max_train_size=2000).split(38000)
    assert len(folds) == 5
    assert folds[0].test_idx[0] == 505
    assert folds[-1].test_idx[-1] == 37999
    for f in folds:
        assert 500 <= len(f.train_idx) <= 2000
        assert f.train_idx[-1] <= f.test_idx[0] - 6
    for a, b in zip(folds, folds[1:]):
        assert b.test_idx[0] > a.test_idx[-1] + 5


def test_small_spread_source_reduces_fold_count_without_overlapping():
    folds = PurgedWalkForwardSplit(5, 500, 250, 5, 5, placement="spread").split(1100)
    assert len(folds) == 2
    assert folds[-1].test_idx[-1] == 1099
    assert folds[1].test_idx[0] > folds[0].test_idx[-1] + 5


def test_validation_rejects_bad_training_window():
    with pytest.raises(ValueError):
        ValidationConfig(max_train_size=100)
    with pytest.raises(ValueError):
        ValidationConfig(fold_placement="random")


def test_batch_refreshes_config_changed_and_corrupt_results(monkeypatch, tmp_path):
    source = tmp_path / "bars.csv"
    source.write_text("time,open,high,low,close\n1,1,1,1,1\n")
    monkeypatch.setattr("daedalus.batch.build_catalog", lambda _: pd.DataFrame([
        {"path": str(source), "sha256": "a" * 64, "rows": 1000}]))
    calls = []
    def research(*args, **kwargs):
        assert kwargs["allow_holdout"] is False
        calls.append(1)
        return {"status": "development_qualified", "protected_holdout_touched": False}
    monkeypatch.setattr("daedalus.batch.research_file", research)
    cfg = DaedalusConfig()
    run_batch(tmp_path, tmp_path, cfg)
    assert run_batch(tmp_path, tmp_path, cfg)["skipped_existing"] == 1
    changed = replace(cfg, validation=replace(cfg.validation, transaction_cost_bps=10))
    assert run_batch(tmp_path, tmp_path, changed)["processed"] == 1
    p = tmp_path / cfg.runtime.output_dir / f"{'a' * 16}.json"
    data = json.loads(p.read_text()); data["status"] = "tampered"
    p.write_text(json.dumps(data))
    assert run_batch(tmp_path, tmp_path, changed)["processed"] == 1
    assert len(calls) == 3


def test_sqlite_transaction_rolls_back_and_closes(tmp_path):
    path = tmp_path / "closed.db"
    with sqlite_connection(path) as con:
        con.execute("CREATE TABLE value(x)")
    with pytest.raises(sqlite3.ProgrammingError):
        con.execute("SELECT 1")
    with pytest.raises(RuntimeError):
        with sqlite_connection(path) as failed:
            failed.execute("INSERT INTO value VALUES (1)")
            raise RuntimeError("abort")
    with sqlite_connection(path) as check:
        assert check.execute("SELECT count(*) FROM value").fetchone()[0] == 0
    with pytest.raises(sqlite3.ProgrammingError):
        failed.execute("SELECT 1")
