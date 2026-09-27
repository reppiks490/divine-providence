from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from recovery_governance_quorum import GovernanceApproval
from recovery_governance_state_machine import GovernanceTransactionJournal, JournalPhase

@dataclass(frozen=True)
class CompositeVerdict: valid: bool; reason: str; epoch: int

class CrashReconciledGovernanceStore:
    """Journaled crash-reconcilable composition of governance + M-of-N admission."""
    def __init__(self,governance_store,admission_store,directory):
        self.governance=governance_store; self.admission=admission_store; self.directory=Path(directory)
        self.journal=GovernanceTransactionJournal(self.directory/'journal')
    def _payload(self,e): return self.directory/f'payload-{e:020d}.json'
    def _write_payload(self,epoch,approvals):
        self.directory.mkdir(parents=True,exist_ok=True); p=self._payload(epoch.epoch)
        p.write_text(json.dumps({'epoch':epoch.to_mapping(),'approvals':[a.__dict__ for a in approvals]},sort_keys=True,separators=(',',':'))+'\n')
        return p
    def _load_payload(self,e):
        from recovery_witness_governance import WitnessGovernanceEpoch
        d=json.loads(self._payload(e).read_text())
        return WitnessGovernanceEpoch.from_mapping(d['epoch']),[GovernanceApproval(**a) for a in d['approvals']]
    def commit(self,epoch,approvals,*,fsync=True,failpoint=None):
        gv=self.governance.verify_chain(allow_empty=True); av=self.admission.verify_chain(allow_empty=True)
        if not gv.valid or not av.valid or gv.epoch!=av.epoch: raise ValueError('composite pre-state invalid')
        if epoch.epoch!=gv.epoch+1: raise ValueError('epoch gap/replay')
        q=self.admission.quorum.verify(epoch.epoch,epoch.epoch_hash,approvals)
        if not q.valid: raise ValueError(q.reason)
        self._write_payload(epoch,approvals); self.journal.prepare(epoch.epoch,epoch.epoch_hash,fsync=fsync)
        if failpoint=='after_prepared': raise RuntimeError('injected crash after prepared')
        self.governance.append(epoch,fsync=fsync); self.journal.advance(epoch.epoch,JournalPhase.GOVERNANCE_WRITTEN,fsync=fsync)
        if failpoint=='after_governance': raise RuntimeError('injected crash after governance')
        self.admission.admit(epoch.epoch,epoch.epoch_hash,approvals,fsync=fsync); self.journal.advance(epoch.epoch,JournalPhase.ADMISSION_WRITTEN,fsync=fsync)
        if failpoint=='after_admission': raise RuntimeError('injected crash after admission')
        self.journal.advance(epoch.epoch,JournalPhase.COMMITTED,fsync=fsync); self._payload(epoch.epoch).unlink(missing_ok=True)
        return epoch
    def recover(self,*,fsync=True):
        jv=self.journal.verify()
        if not jv.valid: raise ValueError('invalid transaction journal')
        cur=self.journal.current()
        if cur is None or cur.phase==JournalPhase.COMMITTED: return self.verify()
        epoch,approvals=self._load_payload(cur.epoch)
        if epoch.epoch_hash!=cur.epoch_hash: raise ValueError('journal/payload hash mismatch')
        gv=self.governance.verify_chain(allow_empty=True); av=self.admission.verify_chain(allow_empty=True)
        if not gv.valid or not av.valid: raise ValueError('cannot reconcile invalid component chain')
        if cur.phase==JournalPhase.PREPARED:
            if gv.epoch==epoch.epoch-1: self.governance.append(epoch,fsync=fsync)
            elif gv.epoch!=epoch.epoch: raise ValueError('ambiguous governance recovery state')
            self.journal.advance(epoch.epoch,JournalPhase.GOVERNANCE_WRITTEN,fsync=fsync); cur=self.journal.current()
        if cur.phase==JournalPhase.GOVERNANCE_WRITTEN:
            av=self.admission.verify_chain(allow_empty=True)
            if av.epoch==epoch.epoch-1: self.admission.admit(epoch.epoch,epoch.epoch_hash,approvals,fsync=fsync)
            elif av.epoch!=epoch.epoch: raise ValueError('ambiguous admission recovery state')
            self.journal.advance(epoch.epoch,JournalPhase.ADMISSION_WRITTEN,fsync=fsync); cur=self.journal.current()
        if cur.phase==JournalPhase.ADMISSION_WRITTEN:
            if not self._components_match(epoch.epoch): raise ValueError('reconciled components mismatch')
            self.journal.advance(epoch.epoch,JournalPhase.COMMITTED,fsync=fsync)
        self._payload(epoch.epoch).unlink(missing_ok=True)
        return self.verify()
    def _components_match(self,n):
        gv=self.governance.verify_chain(allow_empty=True); av=self.admission.verify_chain(allow_empty=True)
        if not gv.valid or not av.valid or gv.epoch!=av.epoch or gv.epoch!=n:return False
        for i in range(1,n+1):
            g=self.governance.epoch_at(i)
            try:a=json.loads(self.admission.path(i).read_text())
            except Exception:return False
            if g is None or a.get('epoch_hash')!=g.epoch_hash:return False
        return True
    def verify(self):
        gv=self.governance.verify_chain(allow_empty=True); av=self.admission.verify_chain(allow_empty=True); jv=self.journal.verify()
        if not gv.valid or not av.valid:return CompositeVerdict(False,'component chain invalid',min(gv.epoch,av.epoch))
        if not jv.valid:return CompositeVerdict(False,'transaction journal invalid',min(gv.epoch,av.epoch))
        cur=self.journal.current()
        if cur is not None and cur.phase!=JournalPhase.COMMITTED:return CompositeVerdict(False,'pending transaction',min(gv.epoch,av.epoch))
        if gv.epoch!=av.epoch:return CompositeVerdict(False,'governance/admission epoch mismatch',min(gv.epoch,av.epoch))
        if gv.epoch and (cur is None or cur.epoch!=gv.epoch or cur.phase!=JournalPhase.COMMITTED):return CompositeVerdict(False,'journal/component epoch mismatch',gv.epoch)
        if not self._components_match(gv.epoch) if gv.epoch else False:return CompositeVerdict(False,'governance/admission hash mismatch',gv.epoch)
        return CompositeVerdict(True,'composite governance valid',gv.epoch)
