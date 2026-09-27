from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    source_path TEXT NOT NULL,
    model_name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    promoted INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experiments_source ON experiments(source_sha256);
CREATE INDEX IF NOT EXISTS idx_experiments_promoted ON experiments(promoted);
"""


class ExperimentRegistry:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as con:
            con.executescript(SCHEMA)

    def record(
        self,
        experiment_id: str,
        source_sha256: str,
        source_path: str,
        model_name: str,
        config: dict[str, Any],
        result: dict[str, Any],
        promoted: bool,
    ) -> None:
        payload = (
            experiment_id,
            datetime.now(timezone.utc).isoformat(),
            source_sha256,
            source_path,
            model_name,
            json.dumps(config, sort_keys=True, default=str),
            json.dumps(result, sort_keys=True, default=str),
            int(promoted),
        )
        with sqlite3.connect(self.path) as con:
            con.execute("INSERT OR REPLACE INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?)", payload)

    def set_promoted(self, experiment_id: str, promoted: bool) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute("UPDATE experiments SET promoted=? WHERE experiment_id=?", (int(promoted), experiment_id))

    def update_result(self, experiment_id: str, result: dict[str, Any]) -> None:
        """Persist post-corpus evidence (for example q-values) without rewriting identity/config."""
        with sqlite3.connect(self.path) as con:
            cur = con.execute(
                "UPDATE experiments SET result_json=? WHERE experiment_id=?",
                (json.dumps(result, sort_keys=True, default=str), experiment_id),
            )
            if cur.rowcount != 1:
                raise KeyError(f"Unknown experiment_id: {experiment_id}")

    def promoted(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.path) as con:
            rows = con.execute(
                "SELECT experiment_id, created_at, source_sha256, source_path, model_name, result_json "
                "FROM experiments WHERE promoted=1 ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "experiment_id": r[0],
                "created_at": r[1],
                "source_sha256": r[2],
                "source_path": r[3],
                "model_name": r[4],
                "result": json.loads(r[5]),
            }
            for r in rows
        ]
