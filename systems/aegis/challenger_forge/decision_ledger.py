from __future__ import annotations
from dataclasses import dataclass

@dataclass
class LedgerEntry:
    candidate_id: str
    version: str
    state: str
    reason: str = ""
    supersedes: str | None = None

class DecisionLedger:
    def __init__(self):
        self.entries=[]
    def record(self, entry: LedgerEntry):
        self.entries.append(entry)
    def tombstone(self, candidate_id, version, reason):
        self.record(LedgerEntry(candidate_id,version,"TOMBSTONED",reason))
    def revive(self, candidate_id, version, reason, supersedes=None):
        self.record(LedgerEntry(candidate_id,version,"ACTIVE",reason,supersedes))
    def current(self, candidate_id):
        xs=[e for e in self.entries if e.candidate_id==candidate_id]
        return xs[-1] if xs else None
    def is_active(self, candidate_id):
        e=self.current(candidate_id)
        return bool(e and e.state=="ACTIVE")
