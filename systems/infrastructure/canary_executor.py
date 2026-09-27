from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping


class CanaryStatus(str, enum.Enum):
    STAGE_FAILED = 'stage_failed'
    ABORTED = 'aborted'
    PROMOTION_FAILED = 'promotion_failed'
    PROMOTED = 'promoted'


@dataclass(frozen=True)
class CanaryProof:
    cycle_id: int
    component: str
    action_fingerprint: str
    staged_at: float
    verified_at: float
    before_score: float
    observed_score: float
    verification_reason: str
    promotion_authorized: bool
    status: str
    proof_hash: str = ''

    def _computed_hash(self) -> str:
        body = dataclasses.asdict(self)
        body['proof_hash'] = ''
        return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()

    def finalized(self) -> 'CanaryProof':
        return dataclasses.replace(self, proof_hash=self._computed_hash())

    def verify_integrity(self) -> bool:
        # Integrity check only: this detects mutation/corruption but is not an
        # identity signature or trust attestation.
        return bool(self.proof_hash) and self.proof_hash == self._computed_hash()


@dataclass(frozen=True)
class CanaryExecutionResult:
    status: CanaryStatus
    proof: CanaryProof
    message: str


class StagedCanaryExecutor:
    """Executes only through an adapter's explicit stage/promote/abort contract."""
    REQUIRED_METHODS = ('stage_canary', 'promote_canary', 'abort_canary')

    def __init__(self, verification_policy):
        self.policy = verification_policy

    @classmethod
    def adapter_capable(cls, adapter: Any) -> bool:
        return all(callable(getattr(adapter, name, None)) for name in cls.REQUIRED_METHODS)

    async def _verify(self, adapter: Any, before: Any):
        import asyncio
        await asyncio.sleep(self.policy.settle_seconds)
        after = await adapter.health()
        delta = after.score - before.score
        if after.score < self.policy.rollback_below_score:
            return False, after, 'canary health below rollback floor'
        if delta < self.policy.min_improvement:
            return False, after, f'canary health regressed by {delta:.4f}'
        return True, after, f'canary verified delta={delta:.4f}'

    def _proof(self, *, cycle_id, action, staged_at, before, after, reason, authorized, status):
        return CanaryProof(
            cycle_id=cycle_id,
            component=action.component,
            action_fingerprint=action.fingerprint,
            staged_at=staged_at,
            verified_at=time.time(),
            before_score=before.score,
            observed_score=after.score,
            verification_reason=reason,
            promotion_authorized=authorized,
            status=status.value,
        ).finalized()

    async def execute(self, adapter: Any, action: Any, before: Any, *, cycle_id: int) -> CanaryExecutionResult:
        if not self.adapter_capable(adapter):
            proof = self._proof(cycle_id=cycle_id, action=action, staged_at=time.time(), before=before,
                                after=before, reason='adapter lacks genuine staged-canary contract',
                                authorized=False, status=CanaryStatus.STAGE_FAILED)
            return CanaryExecutionResult(CanaryStatus.STAGE_FAILED, proof, proof.verification_reason)

        snapshot = await adapter.snapshot()
        staged_at = time.time()
        ok, token, msg = await adapter.stage_canary(action, snapshot)
        if not ok:
            proof = self._proof(cycle_id=cycle_id, action=action, staged_at=staged_at, before=before,
                                after=before, reason=f'canary stage failed: {msg}', authorized=False,
                                status=CanaryStatus.STAGE_FAILED)
            return CanaryExecutionResult(CanaryStatus.STAGE_FAILED, proof, proof.verification_reason)

        try:
            verified, after, reason = await self._verify(adapter, before)
        except Exception as exc:
            abort_ok, abort_msg = await adapter.abort_canary(token, snapshot, action)
            reason = f'verification exception: {type(exc).__name__}: {exc}; abort={abort_ok}:{abort_msg}'
            proof = self._proof(cycle_id=cycle_id, action=action, staged_at=staged_at, before=before,
                                after=before, reason=reason, authorized=False, status=CanaryStatus.ABORTED)
            return CanaryExecutionResult(CanaryStatus.ABORTED, proof, reason)
        if not verified:
            abort_ok, abort_msg = await adapter.abort_canary(token, snapshot, action)
            proof = self._proof(cycle_id=cycle_id, action=action, staged_at=staged_at, before=before,
                                after=after, reason=f'{reason}; abort={abort_ok}:{abort_msg}', authorized=False,
                                status=CanaryStatus.ABORTED)
            return CanaryExecutionResult(CanaryStatus.ABORTED, proof, proof.verification_reason)

        promote_ok, promote_msg = await adapter.promote_canary(token, action)
        status = CanaryStatus.PROMOTED if promote_ok else CanaryStatus.PROMOTION_FAILED
        if not promote_ok:
            abort_ok, abort_msg = await adapter.abort_canary(token, snapshot, action)
            reason = f'promotion failed: {promote_msg}; abort={abort_ok}:{abort_msg}'
        else:
            reason = f'{reason}; promotion={promote_msg}'
        proof = self._proof(cycle_id=cycle_id, action=action, staged_at=staged_at, before=before,
                            after=after, reason=reason, authorized=promote_ok, status=status)
        return CanaryExecutionResult(status, proof, reason)
