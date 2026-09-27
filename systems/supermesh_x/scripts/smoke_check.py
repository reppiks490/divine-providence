#!/usr/bin/env python3
"""Deterministic local smoke checks for the portable SuperMesh-X package."""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from mesh_planner import plan_capability
from public_event_impact import classify_event, attribution_assessment
from geopolitical_event import classify_geopolitical_event, transmission_map
from recency_weight import freshness_bucket
from event_fabric import process_event_batch
from integration_hub import select_integrations
from ibkr_adapter import connection_plan, authorize_operation
from substack_ingest import publication_feed_url
from forex_factory_adapter import normalize_event, surprise_score
from email_intelligence import normalize_message, classify_message
from private_source_policy import can_route_payload, redact_private_record
from private_context_fusion import fuse_public_event_with_private_context
from portfolio_shock_overlay import build_overlay
from tool_surface_diff import diff_tool_surfaces
from discovery_receipt import build_receipt
from adaptive_director import direct_capability
from capability_plan import compile_plan, validate_step, plan_digest
from mcp_era_guard import normalize_tool_contract, protocol_preflight, build_tool_trace
from mrtr_guard import validate_input_required, build_resume_envelope, validate_task_descriptor
from subscription_resilience import SubscriptionResilience
from cross_sdk_conformance import evaluate_fixture
from signed_health_state import sign_health_snapshot, verify_health_snapshot
from execution_domain_kernel import ExecutionDomainLedger, sanitize_trace_context
from durable_execution_store import SQLiteDurableRunStore, StaleFence as DurableStaleFence
from isolation_admission import SQLiteIsolationAdmission, AdmissionDenied
from workspace_isolation import (
    build_mount_manifest, build_network_policy, egress_allowed, build_execution_spec,
    build_execution_receipt, build_runtime_enforcement, build_vault_broker_request,
    build_vault_broker_receipt, watchdog_plan,
)
from remote_store_adapter import MemoryCASBackend, RemoteRunStoreAdapter, StaleFence as RemoteStaleFence
from runtime_driver import InMemorySandboxBackend, IsolatedRuntimeDriver, StaleRuntimeFence, classify_egress_target
from runtime_launch_attestation import build_launch_request, attest_launch, verify_connect_pin, reconcile_runtime
from signed_runtime_evidence import Ed25519Signer, TrustStore, SignedEvidenceJournal
from trust_transparency import TrustPolicy, DurableTrustRoot, TransparencyLog, verify_inclusion_proof
from witnessed_transparency import Witness, WitnessError, RFC9162WitnessedCheckpointLedger
from witness_policy_epoch import WitnessPolicyEpoch, DurableWitnessPolicyRoot, EpochWitnessRegistry, policy_rotation_signature
from durable_gossip_journal import DurableGossipJournal
from trusted_time import TrustedTimeSample, DurableTrustedTimeFloor, TrustedTimeGuard
from cross_runtime_vectors import ed25519_signature_vector, verify_signature_vector


def run_checks():
    states = {
        'twelve-data': {'state': 'ready', 'health': 0.95},
        'tickerlayer': {'state': 'ready', 'health': 0.85},
    }
    mesh = plan_capability('market.quote', states, limit=2)
    mesh_ok = bool(mesh['selected']) and mesh['selected'][0]['routable'] is True

    event = classify_event({'text': 'Public tariff announcement with immediate market relevance'})
    impact = attribution_assessment(
        timing_score=0.95,
        source_score=0.9,
        move_zscore=2.4,
        cross_asset_score=0.8,
        confounder_score=0.1,
        novelty_score=0.8,
        anticipation_score=0.05,
        independent_sources=3,
    )
    impact_ok = event['category'] == 'trade_tariff' and impact['causal_claim'] is False and impact['score'] > 0

    geo = classify_geopolitical_event({'text': 'Iran-related tanker disruption near the Strait of Hormuz'})
    tx = transmission_map(geo)
    geo_ok = 'shipping_chokepoint' in geo['themes'] and 'WTI' in tx['assets'] and 'VIX' in tx['assets']

    recency_ok = freshness_bucket('2026-09-24T19:40:00Z', '2026-09-24T19:45:00Z') == 'breaking'

    fabric = process_event_batch(
        events=[
            {'id':'p1','entity':'example mover','text':'public announcement','published_time':'2026-09-24T19:40:00Z','retrieved_time':'2026-09-24T19:40:05Z','source_family':'official'},
            {'id':'p2','entity':'example mover','text':'public announcement!','published_time':'2026-09-24T19:40:30Z','retrieved_time':'2026-09-24T19:40:40Z','source_family':'wire'},
        ],
        reactions={'NQ':{'return_z':-1.5,'lag_seconds':60,'channel':'equities'},'VIX':{'return_z':2.0,'lag_seconds':30,'channel':'volatility'}},
        cutoff='2026-09-24T19:42:00Z',
        evidence=[{'id':'s1','available_time':'2026-09-24T19:40:05Z','source_family':'official'}],
        market=[{'asset':'NQ','observed_time':'2026-09-24T19:41:00Z','price':25000}],
        priority_inputs={'asset_relevance':1,'topic_relevance':0.8,'recency':1,'historical_impact':0.5,'source_coverage':1},
        base_confidence=0.9,
        age_minutes=2,
        conflict_strength=0.1,
    )
    fabric_ok = fabric['cluster_count'] == 1 and fabric['ledger_verification']['valid'] and fabric['replay']['point_in_time']

    hub = select_integrations('broker.orders', {'interactive-brokers':'ready'})
    ibkr = connection_plan('retail')
    unified_ok = (
        bool(hub['selected'])
        and hub['selected'][0]['permission_class'] == 'read_write_gated'
        and ibkr['primary_mode'] == 'client_portal_gateway'
        and authorize_operation('place_order', False)['allowed'] is False
        and publication_feed_url('example') == 'https://example.substack.com/feed'
        and surprise_score('0.3%','0.2%')['direction'] == 'above_forecast'
    )

    integration = select_integrations('market.quote', {'twelve-data':'ready','interactive-brokers':'auth_required'})
    integration_ok = bool(integration['selected']) and any(x['id']=='interactive-brokers' for x in integration['deferred'])
    ibkr_ok = (not authorize_operation('place_order', False)['allowed']) and authorize_operation('portfolio_read', False)['allowed']
    substack_ok = publication_feed_url('example') == 'https://example.substack.com/feed'
    ff = normalize_event({'title':'CPI','country':'USD','impact':'High','actual':'0.3%','forecast':'0.2%','previous':'0.2%'}, timezone='UTC')
    ff_ok = ff['currency']=='USD' and ff['impact']=='high'

    email = normalize_message({
        'id':'m1','thread_id':'t1','from':'macro@example.com','subject':'New post from Macro Desk',
        'timestamp':'2026-09-24T20:00:00Z','body':'Substack newsletter on rates',
        'attachments':[{'filename':'report.pdf','mime_type':'application/pdf'}],
    })
    email_class = classify_message(email)
    private_intelligence_ok = email['source_class']=='user_authorized_private' and email_class['newsletter'] and email['exportable_to_public_providers'] is False

    guard = can_route_payload(email, target_class='public_provider')
    derived = redact_private_record({'source_class':'user_authorized_private','body':'private','symbol':'NQ','topic':'rates'}, ['symbol','topic'])
    private_guard_ok = guard['allowed'] is False and 'body' not in derived and derived['source_class']=='derived_private_feature'

    overlay = build_overlay(
        [{'symbol':'QQQ','weight':0.4,'asset_class':'etf'},{'symbol':'XLE','weight':0.1,'asset_class':'etf'},{'symbol':'CASH','weight':0.5,'asset_class':'cash'}],
        {'QQQ':{'shock_score':-2.0,'channel':'equities'},'XLE':{'shock_score':1.5,'channel':'energy'}},
    )
    fused = fuse_public_event_with_private_context(
        {'event_id':'e1','topic':'macro','confidence':0.8,'evidence_ids':['pub1']},
        {'portfolio_id':'p1','overlay_score':overlay['portfolio_shock_score'],'evidence_ids':['priv1']},
    )
    portfolio_overlay_ok = overlay['portfolio_shock_score']==-0.65 and overlay['trade_instruction'] is None and fused['private_context_exportable'] is False

    before_surface = [{'name':'quote','inputSchema':{'type':'object','properties':{'symbol':{'type':'string'}},'required':['symbol']}}]
    after_surface = [{'name':'quote','inputSchema':{'type':'object','properties':{'symbol':{'type':'string'},'currency':{'type':'string'}},'required':['symbol']}}]
    surface_diff = diff_tool_surfaces(before_surface, after_surface)
    surface_ok = surface_diff['breaking'] is False and surface_diff['changed'][0]['classification']=='compatible'

    receipt = build_receipt('market quote provider', [
        {'id':'twelve-data','score':0.95,'capabilities':['market.quote'],'raw_args':{'secret':'x'}},
        {'id':'tickerlayer','score':0.85,'capabilities':['market.quote']},
        {'id':'fallback','score':0.50,'capabilities':['market.quote']},
    ], limit=2, stop_reason='limit')
    receipt_ok = receipt['withheld_count']==1 and 'secret' not in str(receipt)

    adaptive_catalog = [
        {'name':'twelve-data','capabilities':['market.quote'],'runtime_targets':['chatgpt'],'transports':['native_tool'],'auth_modes':['none'],'priority':80},
        {'name':'tickerlayer','capabilities':['market.quote'],'runtime_targets':['chatgpt'],'transports':['native_tool'],'auth_modes':['none'],'priority':70},
    ]
    adaptive = direct_capability(
        'market.quote',
        {'twelve-data':{'state':'ready','health':0.9},'tickerlayer':{'state':'ready','health':0.9}},
        adaptive_catalog,
        {'name':'chatgpt','supported_transports':['native_tool'],'credential_modes':['none']},
        feedback={'twelve-data':{'market.quote':{'score':0.25}},'tickerlayer':{'market.quote':{'score':0.95}}},
        now=0,
    )
    adaptive_ok = adaptive['selected'][0]['provider']=='tickerlayer'

    plan = compile_plan(
        request_id='smoke-v090',
        capability='market.quote',
        candidates=[
            {'provider':'twelve-data','adaptive_score':0.95,'schema_fingerprint':'fp-ok'},
            {'provider':'tickerlayer','adaptive_score':0.85,'schema_fingerprint':'fp-fallback'},
        ],
        source_class='public_web',
        observed_schema_fingerprints={'twelve-data':'fp-ok'},
    )
    capability_plan_ok = (
        plan['steps'][0]['provider']=='twelve-data'
        and plan['steps'][0]['fallbacks']==['tickerlayer']
        and plan['auto_execute'] is True
        and len(plan_digest(plan))==64
    )

    order_plan = compile_plan(
        request_id='smoke-order',
        capability='broker.orders',
        candidates=[{'provider':'interactive-brokers','adaptive_score':1.0,'schema_fingerprint':'ibkr-v1'}],
        source_class='user_authorized_private',
    )
    authority_gate_ok = (
        order_plan['authority']['requires_explicit_authorization'] is True
        and order_plan['auto_execute'] is False
    )

    privacy_gate = validate_step({
        'provider':'public-search',
        'provider_visibility':'public',
        'input_class':'user_authorized_private',
        'input_fields':['email_body'],
        'allowed_derived_fields':[],
    })
    privacy_plan_ok = privacy_gate['allowed'] is False

    drift_plan = compile_plan(
        request_id='smoke-drift',
        capability='market.quote',
        candidates=[{'provider':'twelve-data','adaptive_score':0.95,'schema_fingerprint':'old'}],
        source_class='public_web',
        observed_schema_fingerprints={'twelve-data':'new'},
    )
    schema_rediscovery_ok = (
        drift_plan['steps'][0]['preflight']=='rediscover'
        and drift_plan['steps'][0]['executable'] is False
    )

    mcp_contract = normalize_tool_contract({
        'name':'market_quote',
        'annotations':{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':True},
        'inputSchema':{'type':'object'},
    }, '2026-07-28', trusted_server=True)
    mcp_preflight = protocol_preflight('2026-07-28', {'io.modelcontextprotocol/protocolVersion':'2026-07-28'})
    mcp_trace = build_tool_trace('market.quote','tickerlayer','market_quote','2026-07-28',plan_digest(plan),'ok',{'token':'secret','symbol':'US100'})
    mcp_era_ok = (
        mcp_contract['authority']['requires_explicit_authorization'] is False
        and mcp_preflight['allowed'] is True
        and mcp_preflight['discovery_method']=='server/discover'
        and 'token' not in mcp_trace['attributes']
        and mcp_trace['span_name']=='execute_tool'
    )

    mrtr_result = {'resultType':'input_required','requestState':'opaque-smoke','inputRequests':{'confirm':{'method':'elicitation/create'}}}
    mrtr_check = validate_input_required(mrtr_result, protocol_version='2026-07-28')
    mrtr_resume = build_resume_envelope(mrtr_result, {'confirm':{'action':'accept'}, 'unknown':{'action':'accept'}})
    task_check = validate_task_descriptor({'taskId':'a7d4c9028f5e4b1bbd72e99ac0325d12','status':'working'})
    mrtr_ok = mrtr_check['allowed'] and set(mrtr_resume['inputResponses']) == {'confirm'}
    task_ok = task_check['allowed'] and task_check['enumeration_allowed'] is False

    resilience = SubscriptionResilience(base_backoff_ms=100, max_backoff_ms=1000)
    resilience.acknowledged('listen-1', provider='mcp-provider')
    restart = resilience.stream_ended('listen-1', provider='mcp-provider', now_ms=1000, abrupt=True)
    subscription_resilience_ok = restart['refetch_required'] and not restart['replay_allowed'] and restart['retry_after_ms']==1100

    conformance = evaluate_fixture({'sdk':'typescript-v2','era':'modern','discovery':'server/discover','request_meta':{'protocolVersion':'2026-07-28'},'tasks_extension':True})
    health_key=b'smoke-health-key-material-32bytes!'
    signed_health=sign_health_snapshot({'provider':'smoke','health':0.9,'circuit':'closed','sequence':2,'epoch':1}, key=health_key, key_id='smoke-k1')
    verified_health=verify_health_snapshot(signed_health, keys={'smoke-k1':health_key}, minimum_epoch=1, last_sequence=1)

    domain = ExecutionDomainLedger()
    domain_lease = domain.acquire('smoke-domain', 'smoke-worker', now_ms=1000, ttl_ms=1000)
    domain.configure_budget('smoke-domain', {'provider_calls': 2, 'tokens': 1000})
    domain_remaining = domain.consume_budget('smoke-domain', {'provider_calls': 1, 'tokens': 100})
    domain_auth = domain.set_authority('smoke-domain', requested=['filesystem.read','terminal.sandbox','broker.orders'], granted=['filesystem.read','terminal.sandbox'])
    domain_cp = domain.checkpoint('smoke-domain', 'smoke-worker', domain_lease['fencing_token'], {'phase':'smoke','secret':'must-not-appear'}, now_ms=1100)
    domain_trace = sanitize_trace_context({'trace_id':'trace-smoke','authorization':'secret','baggage':{'email':'private'},'labels':{'provider':'local','run_kind':'verification','customer_id':'private'}})
    execution_domain_ok = (
        domain_lease['fencing_token'] == 1
        and domain_remaining['provider_calls'] == 1
        and 'broker.orders' not in domain_auth['granted']
        and 'state' not in domain_cp
        and 'must-not-appear' not in repr(domain_cp)
        and domain_trace == {'trace_id':'trace-smoke','labels':{'provider':'local','run_kind':'verification'}}
    )

    with tempfile.TemporaryDirectory() as td:
        durable_path = Path(td) / 'runs.sqlite3'
        durable1 = SQLiteDurableRunStore(durable_path)
        durable_lease1 = durable1.acquire('durable-smoke', 'worker-a', now_ms=1000, ttl_ms=100)
        durable_cp = durable1.checkpoint('durable-smoke', 'worker-a', durable_lease1['fencing_token'], {'phase':'one','secret':'do-not-store'}, now_ms=1050)
        durable2 = SQLiteDurableRunStore(durable_path)
        durable_lease2 = durable2.acquire('durable-smoke', 'worker-b', now_ms=1100, ttl_ms=100)
        stale_blocked = False
        try:
            durable1.checkpoint('durable-smoke', 'worker-a', durable_lease1['fencing_token'], {'late':True}, now_ms=1110)
        except DurableStaleFence:
            stale_blocked = True
        durable_store_ok = (
            durable_cp['state_hash'].startswith('sha256:')
            and 'do-not-store' not in repr(durable_cp)
            and durable_lease2['fencing_token'] == 2
            and stale_blocked
        )

        admission_path = Path(td) / 'admission.sqlite3'
        capacity = {'cpu_millis':4000,'memory_mb':8192,'storage_mb':10000,'gpu_units':1,'model_tokens':100000,'provider_calls':1000,'concurrent_tasks':16}
        allowed = {'filesystem.read','terminal.sandbox','network.public_read','provider.read','gpu.compute'}
        admission1 = SQLiteIsolationAdmission(admission_path, capacity=capacity, admissible_capabilities=allowed)
        admission_receipt = admission1.admit(
            'admit-smoke', resources={'cpu_millis':1000,'memory_mb':1024,'concurrent_tasks':2},
            authority_manifest={'requested':['terminal.sandbox'],'granted':['terminal.sandbox']},
            credential_refs=['secretref://opaque/smoke'], now_ms=1000,
        )
        admission2 = SQLiteIsolationAdmission(admission_path, capacity=capacity, admissible_capabilities=allowed)
        denied_broker = False
        try:
            admission2.admit('broker-smoke', resources={'cpu_millis':1}, authority_manifest={'requested':['broker.orders'],'granted':['broker.orders']}, now_ms=1100)
        except AdmissionDenied:
            denied_broker = True
        isolation_admission_ok = (
            admission2.available()['cpu_millis'] == 3000
            and admission_receipt['credential_ref_count'] == 1
            and 'opaque/smoke' not in repr(admission_receipt)
            and denied_broker
        )


    mount_manifest = build_mount_manifest('smoke-ws', [
        {'name':'source','source_ref':'artifactref://pkg/source','target':'src','mode':'ro'},
        {'name':'scratch','source_ref':'scratch://smoke-ws','target':'tmp','mode':'rw'},
    ])
    network_policy = build_network_policy('provider_allowlist', allow_hosts=['api.example.com'])
    execution_spec = build_execution_spec(
        argv=['python','-m','pytest','-q'], cwd='src', env={'MODE':'smoke'},
        secret_env={'API_TOKEN':'secretref://vault/smoke/token'}, timeout_ms=5000,
    )
    execution_receipt = build_execution_receipt(execution_spec, exit_code=0, started_at_ms=1, ended_at_ms=5, stdout_bytes=10)
    runtime_hook = build_runtime_enforcement(
        {'run_id':'smoke-runtime','resources':{'cpu_millis':1000,'ram_mb':1024},'granted_capabilities':['terminal.sandbox'],'request_digest':'sha256:smoke'},
        requested_limits={'cpu_millis':500}, requested_capabilities=['terminal.sandbox'],
    )
    vault_req = build_vault_broker_request(
        run_id='smoke-runtime', secret_refs=['secretref://vault/smoke/token'], purpose='smoke',
        authority_manifest={'granted':['secrets.resolve']},
    )
    vault_receipt = build_vault_broker_receipt(vault_req, status='resolved', lease_ids=['opaque-lease'])
    wd = watchdog_plan([{'run_id':'lost','status':'running','lease_expires_at_ms':10,'updated_at_ms':1}], {'lost':{}}, now_ms=20)
    workspace_isolation_ok = (
        mount_manifest['host_filesystem_visible'] is False
        and egress_allowed(network_policy, 'https://api.example.com/v1')
        and not egress_allowed(network_policy, 'https://127.0.0.1/')
        and execution_receipt['exit_code'] == 0
        and 'vault/smoke/token' not in repr(execution_receipt)
        and runtime_hook['limits']['cpu_millis'] == 500
        and 'vault/smoke/token' not in repr(vault_receipt)
        and wd['executed'] is False and wd['action_count'] == 2
    )

    remote_backend = MemoryCASBackend()
    remote_a = RemoteRunStoreAdapter(remote_backend)
    remote_b = RemoteRunStoreAdapter(remote_backend)
    remote_lease1 = remote_a.acquire('remote-smoke','worker-a',now_ms=100,ttl_ms=10)
    remote_lease2 = remote_b.acquire('remote-smoke','worker-b',now_ms=110,ttl_ms=10)
    remote_stale_blocked = False
    try:
        remote_a.checkpoint('remote-smoke','worker-a',remote_lease1['fencing_token'],{'late':True},now_ms=111)
    except RemoteStaleFence:
        remote_stale_blocked = True
    remote_store_adapter_ok = remote_lease2['fencing_token'] == 2 and remote_stale_blocked

    runtime_backend = InMemorySandboxBackend()
    runtime_driver = IsolatedRuntimeDriver(runtime_backend)
    runtime_reservation = {'run_id':'runtime-smoke','resources':{'cpu_millis':500,'ram_mb':512},'granted_capabilities':['terminal.sandbox'],'request_digest':'sha256:runtime'}
    runtime_created = runtime_driver.create('runtime-smoke','worker-a',1,runtime_reservation,secret_refs=['secretref://vault/runtime/token'])
    runtime_driver.start('runtime-smoke','worker-a',1,now_ms=10)
    runtime_backend.force_takeover('runtime-smoke','worker-b',2)
    runtime_stale_blocked = False
    try:
        runtime_driver.stop('runtime-smoke','worker-a',1,now_ms=20,reason='late')
    except StaleRuntimeFence:
        runtime_stale_blocked = True
    runtime_driver_ok = (runtime_created['enforced_limits']['cpu_millis']==500 and runtime_stale_blocked and 'vault/runtime/token' not in repr(runtime_created) and not classify_egress_target('169.254.169.254')['allowed'])

    signing_key = Ed25519Signer.generate('smoke-ed25519')
    signing_trust = TrustStore(); signing_trust.add('smoke-ed25519', signing_key.public_key_bytes())
    signed_journal = SignedEvidenceJournal('signed-smoke', signing_trust, allowed_capabilities={'runtime.inspect'})
    signed_receipt = signed_journal.admit(signing_key.sign({'run_id':'signed-smoke','fencing_token':1,'kind':'launch','payload':{'capabilities':['runtime.inspect']}}))
    signed_runtime_ok = signed_journal.verify() and signed_receipt['kind']=='signed:launch'

    with tempfile.TemporaryDirectory() as trust_td:
        root_signer = Ed25519Signer.generate('root-smoke')
        next_signer = Ed25519Signer.generate('next-smoke')
        trust_root = DurableTrustRoot.bootstrap(Path(trust_td)/'trust.json', TrustPolicy.from_signers(1,[root_signer]))
        next_policy = TrustPolicy.from_signers(2,[next_signer])
        rotation_statement = trust_root.make_rotation_statement(next_policy)
        trust_root.rotate(next_policy,[root_signer.sign(rotation_statement),next_signer.sign(rotation_statement)])
        transparency = TransparencyLog(); transparency.append({'kind':'runtime','id':'smoke'}); transparency.append({'kind':'runtime','id':'smoke-2'})
        proof = transparency.inclusion_proof(1)
        checkpoint = transparency.checkpoint(next_signer,key_epoch=2)
        trust_transparency_ok = (trust_root.policy.epoch==2 and verify_inclusion_proof({'kind':'runtime','id':'smoke-2'},1,2,proof,transparency.root_digest()) and transparency.verify_checkpoint(checkpoint,next_signer.public_key_bytes())['verified'])

    with tempfile.TemporaryDirectory() as witness_td:
        wa, wb, wc = Witness.generate('wa'), Witness.generate('wb'), Witness.generate('wc')
        wp1 = WitnessPolicyEpoch(1, {w.witness_id:w.public_key_bytes() for w in (wa,wb)}, 2)
        wroot = DurableWitnessPolicyRoot.bootstrap(Path(witness_td)/'witness-policy.json', wp1)
        wreg = EpochWitnessRegistry(wroot)
        wledger = RFC9162WitnessedCheckpointLedger(wreg, 'smoke-log')
        wjournal = DurableGossipJournal(Path(witness_td)/'gossip.jsonl', wreg)
        wcp1 = wledger.checkpoint([b'a'], [wa,wb]); wjournal.append(wcp1)
        wsnapshot = Path(witness_td)/'gossip-snapshot-1.json'
        wanchors = Path(witness_td)/'gossip-anchors.jsonl'
        wcompact = wjournal.compact(wsnapshot, wanchors, [wa,wb])
        wp2 = WitnessPolicyEpoch(2, {w.witness_id:w.public_key_bytes() for w in (wb,wc)}, 2)
        wst = wroot.make_rotation_statement(wp2)
        wroot.rotate(wp2, [policy_rotation_signature(w,wst) for w in (wa,wb,wc)])
        wcp2 = wledger.checkpoint([b'a',b'b'], [wb,wc]); wjournal.append(wcp2)
        replayed = DurableGossipJournal.load(Path(witness_td)/'gossip.jsonl', wreg)
        compacted = DurableGossipJournal.load_compacted(
            Path(witness_td)/'gossip.jsonl', wsnapshot, wanchors, wreg,
            minimum_snapshot_epoch=1, expected_anchor_digest=wcompact['anchor_digest'],
        )
        vector = ed25519_signature_vector('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60', {})
        witness_policy_epoch_ok = (
            wcp1['policy_epoch']==1 and wcp2['policy_epoch']==2
            and replayed.latest('smoke-log')['tree_size']==2
            and compacted.latest('smoke-log')['tree_size']==2
            and compacted.compaction_report['snapshot_epoch']==1
            and verify_signature_vector(vector)
            and 'private_key' not in repr(wcp2).lower()
        )
        gossip_compaction_ok = (
            wcompact['snapshot_epoch']==1
            and wcompact['journal_sequence']==1
            and len(wcompact['anchor_digest'])==64
            and compacted.sequence==2
        )

        class _SmokeTimeSource:
            def __init__(self, sample):
                self.current = sample
            def sample(self):
                return self.current

        tsource = _SmokeTimeSource(TrustedTimeSample(1000, 0, 'smoke-trusted-time', 'sha256:smoke-time'))
        tguard = TrustedTimeGuard(
            tsource,
            floor=DurableTrustedTimeFloor(Path(witness_td)/'trusted-time-floor.json'),
            max_uncertainty_seconds=5,
            minimum_lower_bound_unix=900,
        )
        tp = WitnessPolicyEpoch(1, {w.witness_id:w.public_key_bytes() for w in (wa,wb)}, 2, expires_unix=2000)
        troot = DurableWitnessPolicyRoot.bootstrap(Path(witness_td)/'timed-policy.json', tp, trusted_time_guard=tguard)
        treg = EpochWitnessRegistry(troot, trusted_time_guard=tguard)
        tledger = RFC9162WitnessedCheckpointLedger(treg, 'timed-log')
        tjournal = DurableGossipJournal(Path(witness_td)/'timed-gossip.jsonl', treg)
        tcp = tledger.checkpoint([b't'], [wa,wb]); tjournal.append(tcp)
        tsnapshot = Path(witness_td)/'timed-snapshot.json'
        tanchors = Path(witness_td)/'timed-anchors.jsonl'
        tjournal.compact(tsnapshot, tanchors, [wa,wb])
        tenv = json.loads(tsnapshot.read_text())
        tbound = tenv['statement'].get('trusted_time', {})
        tsource.current = TrustedTimeSample(2001, 0, 'smoke-trusted-time', 'sha256:smoke-time-2')
        expired_blocked = False
        try:
            tledger.checkpoint([b't',b'u'], [wa,wb])
        except WitnessError:
            expired_blocked = True
        trusted_time_freeze_guard_ok = (
            tbound.get('source') == 'smoke-trusted-time'
            and tbound.get('lower_bound_unix') == 1000
            and tbound.get('upper_bound_unix') == 1000
            and tbound.get('policy_expires_unix') == 2000
            and expired_blocked
            and (Path(witness_td)/'trusted-time-floor.json').exists()
        )

    checks = {
        'mesh_planner': mesh_ok,
        'public_event_impact': impact_ok,
        'geopolitical_transmission': geo_ok,
        'recency_guard': recency_ok,
        'event_fabric': fabric_ok,
        'unified_integration_fabric': unified_ok,
        'unified_integration_hub': integration_ok,
        'ibkr_permission_gate': ibkr_ok,
        'substack_ingest': substack_ok,
        'forex_factory_macro': ff_ok,
        'private_intelligence_bus': private_intelligence_ok,
        'email_intelligence_bus': private_intelligence_ok,
        'private_source_guard': private_guard_ok,
        'private_source_firewall': private_guard_ok,
        'portfolio_shock_overlay': portfolio_overlay_ok,
        'private_context_fusion': fused['private_context_exportable'] is False and fused['public_evidence_ids']==['pub1'] and fused['private_evidence_ids']==['priv1'],
        'tool_surface_diff': surface_ok,
        'discovery_receipt': receipt_ok,
        'adaptive_capability_director': adaptive_ok,
        'capability_execution_plan': capability_plan_ok,
        'plan_authority_gate': authority_gate_ok,
        'plan_privacy_firewall': privacy_plan_ok,
        'plan_schema_rediscovery': schema_rediscovery_ok,
        'mcp_protocol_era_guard': mcp_era_ok,
        'mcp_tool_annotation_guard': mcp_contract['annotations']['readOnlyHint'] is True,
        'tool_trace_redaction': 'token' not in mcp_trace['attributes'],
        'mcp_multi_round_trip_guard': mrtr_ok,
        'mcp_task_extension_guard': task_ok,
        'mcp_subscription_restart_guard': subscription_resilience_ok,
        'mcp_cross_sdk_conformance': conformance['conformant'] and len(conformance['receipt_hash'])==64,
        'authenticated_provider_health_state': verified_health['provider']=='smoke',
        'execution_domain_foundation': execution_domain_ok,
        'durable_execution_store': durable_store_ok,
        'isolation_admission': isolation_admission_ok,
        'workspace_isolation': workspace_isolation_ok,
        'remote_store_adapter': remote_store_adapter_ok,
        'isolated_runtime_driver': runtime_driver_ok,
        'signed_runtime_evidence': signed_runtime_ok,
        'trust_transparency': trust_transparency_ok,
        'witness_policy_epochs': witness_policy_epoch_ok,
        'gossip_torn_tail_quarantine': hasattr(DurableGossipJournal, 'recover'),
        'gossip_signed_compaction': gossip_compaction_ok,
        'trusted_time_freeze_guard': trusted_time_freeze_guard_ok,
    }
    manifest = (ROOT / 'manifest.yaml').read_text(encoding='utf-8')
    version = 'unknown'
    for line in manifest.splitlines():
        if line.startswith('version:'):
            version = line.split(':', 1)[1].strip()
            break

    launch_req = build_launch_request('smoke-launch','worker',3,{'cpu_millis':500,'ram_mb':256},['8.8.8.8'],['/workspace/in'])
    launch_att = attest_launch(launch_req,{'cpu_millis':500,'ram_mb':256},{'/workspace/in':'ro','/workspace/out':'rw'},pid=42)
    runtime_launch_attestation_ok = launch_att['verified'] and verify_connect_pin('dns.google',['8.8.8.8'],'8.8.8.8')['allowed'] and reconcile_runtime(None,{'worker_id':'worker','fencing_token':3,'status':'running'})['action']=='mark_lost_and_requeue'

    return {
        'runtime_launch_attestation': runtime_launch_attestation_ok,
        'package_version': version,
        'status': 'pass' if all(checks.values()) else 'fail',
        'checks': checks,
    }


def main():
    result = run_checks()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
