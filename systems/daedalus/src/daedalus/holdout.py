from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS holdout_exposures (
    source_sha256 TEXT NOT NULL,
    protocol_hash TEXT NOT NULL,
    holdout_start INTEGER NOT NULL,
    holdout_end INTEGER NOT NULL,
    first_exposed_at TEXT NOT NULL,
    last_exposed_at TEXT NOT NULL,
    exposure_count INTEGER NOT NULL,
    PRIMARY KEY(source_sha256, protocol_hash, holdout_start, holdout_end)
);
CREATE INDEX IF NOT EXISTS idx_holdout_source ON holdout_exposures(source_sha256);
"""


@dataclass(frozen=True)
class HoldoutAssessment:
    source_sha256: str
    protocol_hash: str
    holdout_start: int
    holdout_end: int
    prior_same_protocol_exposures: int
    prior_conflicting_protocols: int
    protocol_clean: bool

    def to_dict(self) -> dict:
        return asdict(self)


class HoldoutLedger:
    """Persistent guardrail against silently reusing a final holdout after redesign.

    Re-running the exact same frozen protocol is reproducibility, not a new experiment.
    A different protocol for the same source is recorded as a conflict so promotion can
    be blocked until Work rotates to a fresh untouched temporal tail.
    """

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as con:
            con.executescript(SCHEMA)

    def assess(
        self,
        source_sha256: str,
        protocol_hash: str,
        holdout_start: int,
        holdout_end: int,
    ) -> HoldoutAssessment:
        with sqlite3.connect(self.path) as con:
            rows = con.execute(
                "SELECT protocol_hash, holdout_start, holdout_end, exposure_count "
                "FROM holdout_exposures WHERE source_sha256=?",
                (source_sha256,),
            ).fetchall()
        same = 0
        conflicts = 0
        for ph, hs, he, count in rows:
            if ph == protocol_hash and int(hs) == int(holdout_start) and int(he) == int(holdout_end):
                same += int(count)
            else:
                conflicts += 1
        return HoldoutAssessment(
            source_sha256=source_sha256,
            protocol_hash=protocol_hash,
            holdout_start=int(holdout_start),
            holdout_end=int(holdout_end),
            prior_same_protocol_exposures=same,
            prior_conflicting_protocols=conflicts,
            protocol_clean=conflicts == 0,
        )

    def record(self, assessment: HoldoutAssessment) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path) as con:
            row = con.execute(
                "SELECT exposure_count, first_exposed_at FROM holdout_exposures "
                "WHERE source_sha256=? AND protocol_hash=? AND holdout_start=? AND holdout_end=?",
                (
                    assessment.source_sha256,
                    assessment.protocol_hash,
                    assessment.holdout_start,
                    assessment.holdout_end,
                ),
            ).fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO holdout_exposures VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        assessment.source_sha256,
                        assessment.protocol_hash,
                        assessment.holdout_start,
                        assessment.holdout_end,
                        now,
                        now,
                        1,
                    ),
                )
            else:
                con.execute(
                    "UPDATE holdout_exposures SET last_exposed_at=?, exposure_count=? "
                    "WHERE source_sha256=? AND protocol_hash=? AND holdout_start=? AND holdout_end=?",
                    (
                        now,
                        int(row[0]) + 1,
                        assessment.source_sha256,
                        assessment.protocol_hash,
                        assessment.holdout_start,
                        assessment.holdout_end,
                    ),
                )
