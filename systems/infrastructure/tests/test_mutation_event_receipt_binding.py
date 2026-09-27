import asyncio
from evidence_provider import EvidenceRequest, InMemoryEvidenceProvider, MutationEvent, ReadOnlyEvidenceCollector, TelemetryPoint
from mutation_receipt import MutationLifecycleRecorder


def receipt(intervention_id='iv-own', component='svc', fingerprint='same-action'):
    r=MutationLifecycleRecorder(intervention_id=intervention_id, action_fingerprint=fingerprint, component=component)
    r.record('created',timestamp=1); r.record('mutation_started',timestamp=2); r.record('mutation_completed',timestamp=3)
    return r.finalize()

def req(receipt_hash):
    return EvidenceRequest('svc','same-action',3,0,6,intervention_id='iv-own',mutation_receipt_hash=receipt_hash)

def telemetry(): return {'svc':(TelemetryPoint(1,.2),TelemetryPoint(2,.2),TelemetryPoint(4,.6),TelemetryPoint(5,.6))}

def test_exact_id_without_receipt_binding_remains_contamination():
    async def go():
        rcpt=receipt(); p=InMemoryEvidenceProvider(telemetry=telemetry(),mutations=(MutationEvent(3,'svc','own',(), 'iv-own'),))
        assert (await ReadOnlyEvidenceCollector(p).collect(req(rcpt.receipt_hash))).mutation_events == ('own',)
    asyncio.run(go())

def test_exact_id_and_receipt_hash_can_exclude_own_event():
    async def go():
        rcpt=receipt(); p=InMemoryEvidenceProvider(telemetry=telemetry(),mutations=(MutationEvent(3,'svc','own',(), 'iv-own',rcpt.receipt_hash),))
        assert (await ReadOnlyEvidenceCollector(p).collect(req(rcpt.receipt_hash))).mutation_events == ()
    asyncio.run(go())

def test_wrong_receipt_hash_remains_contamination():
    async def go():
        rcpt=receipt(); p=InMemoryEvidenceProvider(telemetry=telemetry(),mutations=(MutationEvent(3,'svc','own',(), 'iv-own','forged'),))
        assert (await ReadOnlyEvidenceCollector(p).collect(req(rcpt.receipt_hash))).mutation_events == ('own',)
    asyncio.run(go())

def test_same_receipt_hash_other_intervention_remains_contamination():
    async def go():
        rcpt=receipt(); p=InMemoryEvidenceProvider(telemetry=telemetry(),mutations=(MutationEvent(3,'svc','other',(), 'iv-other',rcpt.receipt_hash),))
        assert (await ReadOnlyEvidenceCollector(p).collect(req(rcpt.receipt_hash))).mutation_events == ('other',)
    asyncio.run(go())
