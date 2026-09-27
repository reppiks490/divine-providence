from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from durable_journal import DurableProofJournal
from proof_journal import ProofJournalReplayVerifier, ProofJournalTransaction
def _h(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
@dataclass(frozen=True)
class RecoveryDecision:
    journal_path:str; scanned_records:int; accepted_transactions:Tuple[ProofJournalTransaction,...]; rejected_records:int
    duplicate_interventions:Tuple[str,...]; original_tail_status:str; original_reason:str; last_good_offset:int
    original_file_size:int; quarantined_bytes:int; quarantine_path:str|None; clean_after_policy:bool
    proof_restore_eligible:bool; positive_learning_restore_eligible:bool; decision_hash:str
class StartupRecoveryPolicy:
    def __init__(self,journal_path,*,verifier=None):
        self.journal=DurableProofJournal(journal_path); self.verifier=verifier or ProofJournalReplayVerifier()
    def recover(self,*,quarantine_dir=None,now=None):
        r=self.journal.recover(); qp=None; qb=0
        if r.tail_status!="clean":
            qd=Path(quarantine_dir) if quarantine_dir else self.journal.path.parent/"quarantine"; qd.mkdir(parents=True,exist_ok=True)
            suffix=hashlib.sha256(f"{self.journal.path}:{r.last_good_offset}:{r.file_size}".encode()).hexdigest()[:16]
            qp=qd/f"{self.journal.path.name}.tail.{suffix}.bin"; qb=self.journal.quarantine_tail(r,qp)
        accepted=[]; rejected=0; seen=set(); dup=set(r.duplicate_interventions)
        for rec in r.records:
            try:
                tx=ProofJournalTransaction.from_mapping(rec.payload)
                if tx.intervention_id in seen: dup.add(tx.intervention_id); rejected+=1; continue
                seen.add(tx.intervention_id)
                verdict=self.verifier.verify(tx,now=now)
                if verdict.valid: accepted.append(tx)
                else: rejected+=1
            except Exception: rejected+=1
        clean=self.journal.recover().tail_status=="clean"
        ok=clean and r.tail_status=="clean" and not dup and rejected==0
        body={"journal_path":str(self.journal.path),"scanned":len(r.records),"accepted":[x.transaction_hash for x in accepted],
              "rejected":rejected,"duplicates":sorted(dup),"tail":r.tail_status,"reason":r.reason,"last_good":r.last_good_offset,
              "size":r.file_size,"quarantined":qb,"quarantine_path":str(qp) if qp else None,"clean_after":clean,"eligible":ok}
        return RecoveryDecision(str(self.journal.path),len(r.records),tuple(accepted),rejected,tuple(sorted(dup)),r.tail_status,r.reason,
                                r.last_good_offset,r.file_size,qb,str(qp) if qp else None,clean,ok,ok,_h(body))
