"""Recovery-history continuity verification (V21). No infrastructure mutation authority."""
from __future__ import annotations
from dataclasses import dataclass
from recovery_checkpoint import RecoveryCheckpoint
from recovery_policy import RecoveryDecision

@dataclass(frozen=True)
class ContinuityVerdict:
    valid: bool
    reason: str

class RecoveryContinuityVerifier:
    """Proves that current recovery monotonically extends a prior checkpoint."""
    def verify(self, prior: RecoveryCheckpoint, current: RecoveryDecision) -> ContinuityVerdict:
        if not prior.verify():
            return ContinuityVerdict(False, "prior checkpoint integrity invalid")
        if prior.journal_path != current.journal_path:
            return ContinuityVerdict(False, "journal substitution detected")
        if current.last_good_offset < prior.last_good_offset:
            return ContinuityVerdict(False, "journal rollback detected")
        if current.original_file_size < prior.last_good_offset:
            return ContinuityVerdict(False, "journal truncation before prior boundary")
        current_hashes = tuple(x.transaction_hash for x in current.accepted_transactions)
        old = prior.accepted_transaction_hashes
        if len(current_hashes) < len(old):
            return ContinuityVerdict(False, "accepted proof history rollback detected")
        if current_hashes[:len(old)] != old:
            return ContinuityVerdict(False, "forked or substituted proof history detected")
        if not current.proof_restore_eligible:
            return ContinuityVerdict(False, "current recovery is not proof-restore eligible")
        return ContinuityVerdict(True, "continuous")
