from pathlib import Path

import pandas as pd

from daedalus.batch import run_batch
from daedalus.config import DaedalusConfig


def test_batch_is_development_only_and_resumable(monkeypatch, tmp_path: Path):
    source = tmp_path / "ALT.csv"
    source.write_text("time,open,high,low,close\n1,1,1,1,1\n", encoding="utf-8")
    catalog = pd.DataFrame([
        {"path": str(source), "sha256": "a" * 64, "rows": 1000},
    ])
    monkeypatch.setattr("daedalus.batch.build_catalog", lambda _: catalog)
    calls = []

    def fake_research(path, project_root, cfg, data_root=None, allow_holdout=True):
        calls.append({"path": path, "allow_holdout": allow_holdout})
        return {"status": "development_qualified", "protected_holdout_touched": False}

    monkeypatch.setattr("daedalus.batch.research_file", fake_research)
    cfg = DaedalusConfig()
    first = run_batch(tmp_path, tmp_path, cfg, resume=True)
    assert first["processed"] == 1
    assert calls == [{"path": source, "allow_holdout": False}]
    run_file = tmp_path / cfg.runtime.output_dir / f"{'a' * 16}.json"
    assert run_file.exists()

    second = run_batch(tmp_path, tmp_path, cfg, resume=True)
    assert second["processed"] == 0
    assert second["skipped_existing"] == 1
    assert len(calls) == 1
