import asyncio, json

from infrastructure_loop import (
    GuardPolicy, HealthReport, InfrastructureSupervisoryLoop, LoopConfig, VerificationPolicy,
)
from canary_executor import StagedCanaryExecutor
from evidence_provider import ReadOnlyEvidenceCollector, TelemetryPoint


class LiveAdapter:
    name = "svc"
    def __init__(self):
        self.score = .30
        self.events = []
    async def collect_signals(self): return []
    async def health(self): return HealthReport(self.name, self.score, .95, symptoms=["severe_degradation"])
    async def snapshot(self): return {"score": self.score}
    async def execute(self, action): self.events.append("execute"); return True, "ok"
    async def rollback(self, snapshot, action): self.score=snapshot["score"]; return True,"ok"
    async def stage_canary(self, action, snapshot): self.events.append("stage"); self.score=.65; return True,{"id":"c1"},"staged"
    async def promote_canary(self, token, action): self.events.append("promote"); return True,"promoted"
    async def abort_canary(self, token, snapshot, action): self.events.append("abort"); self.score=snapshot["score"]; return True,"aborted"


class DynamicEvidenceProvider:
    async def telemetry(self, component, start, end):
        # The collector asks for a symmetric bounded window around intervention.
        mid=(start+end)/2
        if component == "ctrl":
            return (TelemetryPoint(start+1,.40,.9), TelemetryPoint(mid-1,.40,.9),
                    TelemetryPoint(mid+1,.40,.9), TelemetryPoint(end-1,.40,.9))
        return (TelemetryPoint(start+1,.30,.9), TelemetryPoint(mid-1,.30,.9),
                TelemetryPoint(mid+1,.65,.9), TelemetryPoint(end-1,.65,.9))
    async def mutation_events(self, start, end): return ()


def test_live_cycle_emits_all_source_native_receipts_and_complete_envelope(tmp_path):
    async def run():
        adapter=LiveAdapter()
        loop=InfrastructureSupervisoryLoop(
            [adapter],
            config=LoopConfig(shadow_mode=False, journal_path=str(tmp_path/'j.jsonl'), attribution_pre_seconds=60, attribution_post_seconds=60),
            guard_policy=GuardPolicy(cooldown_seconds=0, max_mutations_per_cycle=3, critical_health_floor=.25),
            verification_policy=VerificationPolicy(settle_seconds=0, rollback_below_score=.25),
            canary_executor=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0, rollback_below_score=.25)),
            evidence_collector=ReadOnlyEvidenceCollector(DynamicEvidenceProvider()),
            control_components={"svc":"ctrl"},
        )
        summary=await loop.cycle()
        restart=[r for r in summary['executed_results'] if r['action']['name']=='graceful_restart'][0]
        assert restart['success'] is True
        assert restart['causal_eligible'] is True
        assert restart['attribution_eligible'] is True
        assert restart['attribution_hash']
        assert restart['proof_envelope_hash']
        rows=[json.loads(x) for x in (tmp_path/'j.jsonl').read_text().splitlines()]
        fp=restart['action']['fingerprint']
        receipts=[x['receipt'] for x in rows if x.get('type')=='source_receipt' and x['receipt']['action_identity']==fp]
        assert [x['stage'] for x in receipts] == ['guard','topology','lease','canary','evidence','attribution']
        env=[x for x in rows if x.get('type')=='proof_envelope' and x['action_identity']==fp][-1]
        assert env['valid'] is True
        assert env['envelope']['envelope_hash'] == restart['proof_envelope_hash']
        tx=[x for x in rows if x.get('type')=='proof_transaction' and x['transaction']['action_identity']==fp][-1]
        assert tx['transaction']['intervention_id'] == restart['intervention_id']
        assert tx['transaction']['proof_envelope']['envelope_hash'] == restart['proof_envelope_hash']
        assert tx['transaction']['mutation_receipt']['receipt_hash'] == restart['mutation_receipt_hash']
    asyncio.run(run())


def test_missing_evidence_provider_still_emits_complete_audit_envelope_but_no_positive_learning(tmp_path):
    async def run():
        adapter=LiveAdapter()
        loop=InfrastructureSupervisoryLoop(
            [adapter], config=LoopConfig(shadow_mode=False, journal_path=str(tmp_path/'j.jsonl')),
            guard_policy=GuardPolicy(cooldown_seconds=0, critical_health_floor=.25),
            verification_policy=VerificationPolicy(settle_seconds=0, rollback_below_score=.25),
            canary_executor=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0, rollback_below_score=.25)),
        )
        summary=await loop.cycle()
        restart=[r for r in summary['executed_results'] if r['action']['name']=='graceful_restart'][0]
        assert restart['proof_envelope_hash']
        assert restart['attribution_eligible'] is False
        assert restart['attribution_hash'] == ''
        assert sum(loop.memory.successes.values()) == 0
        assert sum(len(v) for v in loop.memory.by_key.values()) == 0
    asyncio.run(run())
