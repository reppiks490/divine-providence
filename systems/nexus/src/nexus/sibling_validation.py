from __future__ import annotations
from dataclasses import dataclass,asdict
import importlib.util
import sys
from pathlib import Path
import tempfile,json
from .adapters import aion_source_spec,aion_bar_observation,aion_derivation_source_spec,aion_derivation_observation,argus_candle_proxy_feature,athena_provenance,daedalus_candidate
from .contracts import StreamIdentity,StreamManifest,BarEvent
from .replay import ReplayBus
from .sibling_replay import SiblingInstantRouter
from .lineage import DerivationRecord
from .source_health import SourceHealthRegistry, SourceSLOPolicy

@dataclass(frozen=True,slots=True)
class SiblingValidationResult:
    aion:bool;argus:bool;athena:bool;daedalus:bool
    details:dict[str,str]
    @property
    def passed(self)->bool:return self.aion and self.argus and self.athena and self.daedalus
    def to_dict(self)->dict:return {**asdict(self),"passed":self.passed}

def _load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:raise ImportError(path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

def validate_sibling_contracts(*,aion_root:str|Path,argus_root:str|Path,athena_root:str|Path,daedalus_root:str|Path)->SiblingValidationResult:
    details={};ok={"aion":False,"argus":False,"athena":False,"daedalus":False}
    ident=StreamIdentity('csv','CME','NQ1!','1','clock:1m','NQ.csv','a'*64)
    manifest=StreamManifest(ident,2,['time','open','high','low','close'],1,2,60_000_000_000,1.0,0,0,0)
    event=BarEvent(ident.stream_id,100,0,1,2,0.5,1.5,10,'NQ.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus();batch=next(bus.merge_batches({ident.stream_id:[event]},require_available=True));state=next(bus.states_batches([batch]))
    deriv=DerivationRecord.create(product_id='NEXUS:VALIDATION',product_version='3',decision_ns=state.decision_ns,spec_hash='b'*64,input_hashes={'NQ':ident.raw_sha256},code_version='sibling-validation')
    health=SourceHealthRegistry();health.set_policy(ident.stream_id,SourceSLOPolicy(max_receive_lag_ns_p95=20,max_gap_size=0));health.observe(event,received_ns=170)
    health_plane=health.snapshot(state.decision_ns)
    bundle=SiblingInstantRouter().package(batch=batch,state=state,manifests={ident.stream_id:manifest},factors={'market_state':.25},topology={'entropy':.5},quality={'coverage':1.0},ood={'novelty':.1},ingested_ns=170,factor_derivations=[deriv],source_health=health_plane)
    if bundle.athena.get('source_health',{}).get('plane_hash')!=health_plane.plane_hash: raise ValueError('source-health plane did not survive atomic sibling routing')
    try:
        c=_load('_nexus_aion_contracts',Path(aion_root)/'aion'/'contracts.py')
        specs={d['source_id']:c.SourceSpec.from_dict(d) for d in bundle.aion['source_specs']}
        for d in bundle.aion['observations']:
            obs=c.Observation.from_dict(d);c.validate_source_event(specs[obs.source_id],obs)
        if deriv.derivation_hash not in bundle.aion.get('derivation_hashes',[]):
            raise ValueError('derivation genealogy missing from AION packet')
        # Durable integration, not schema-only: append the exact same instant into AION,
        # verify the append-only hash chain, and recover the derivation by as-of time.
        root=str(Path(aion_root).resolve());inserted=False
        if root not in sys.path:sys.path.insert(0,root);inserted=True
        try:
            import importlib
            store_mod=importlib.import_module('aion.store');contracts_mod=importlib.import_module('aion.contracts')
            with tempfile.TemporaryDirectory() as td:
                store=store_mod.EventStore(Path(td)/'aion.sqlite')
                for row in bundle.aion['source_specs']:
                    store.register(contracts_mod.SourceSpec.from_dict(row))
                appended=[]
                for row in bundle.aion['observations']:
                    appended.append(store.append(contracts_mod.Observation.from_dict(row)))
                chain=store.verify_chain();rows=store.asof(state.decision_ns,symbol=deriv.product_id)
                if not chain.get('verified') or chain.get('events')!=len(bundle.aion['observations']):
                    raise ValueError('AION durable hash-chain mismatch')
                if len(rows)!=1 or rows[0]['event']['payload'].get('derivation_hash')!=deriv.derivation_hash:
                    raise ValueError('AION derivation as-of recovery mismatch')
                if any(not x.get('event_hash') for x in appended):
                    raise ValueError('AION append did not return event hashes')
        finally:
            if inserted and sys.path and sys.path[0]==root:sys.path.pop(0)
        ok['aion']=True;details['aion']='same-instant bar + derivation + source-health schemas passed; EventStore append/asof/hash-chain persisted genealogy'
    except Exception as e:details['aion']=f'{type(e).__name__}: {e}'
    try:
        c=_load('_nexus_argus_contracts',Path(argus_root)/'src'/'argus'/'contracts.py')
        for d in bundle.argus['features']:
            f=c.MicrostructureFeature(d['name'],d['value'],c.EvidenceTier(d['evidence_tier']),d['event_time_ns'],d['source_id'],d['reason'])
            if f.evidence_tier!=c.EvidenceTier.CANDLE_PROXY:raise ValueError('CSV escaped CANDLE_PROXY firewall')
        if bundle.argus.get('microstructure_truth') is not False:raise ValueError('ARGUS truth firewall missing')
        ok['argus']=True;details['argus']='same-instant MicrostructureFeature CANDLE_PROXY routing passed'
    except Exception as e:details['argus']=f'{type(e).__name__}: {e}'
    try:
        c=_load('_nexus_athena_contracts',Path(athena_root)/'src'/'athena'/'contracts.py')
        for d in bundle.athena['provenance']:
            p=c.Provenance(d['event_time_ns'],d['ingestion_time_ns'],d['source_id'],d['representation_id'],d['version'],c.DataPlane(d['plane']),d['lineage_id'],tuple(d['quality_flags']))
            if p.plane!=c.DataPlane.RESEARCH:raise ValueError('unexpected ATHENA plane')
        if bundle.athena.get('advisory_only') is not True:raise ValueError('ATHENA ownership firewall missing')
        ok['athena']=True;details['athena']='same-instant Provenance + source-health routing passed without WorldState ownership'
    except Exception as e:details['athena']=f'{type(e).__name__}: {e}'
    try:
        b=_load('_nexus_daedalus_bridge',Path(daedalus_root)/'src'/'daedalus'/'bridge.py');d=bundle.daedalus
        if d['schema']!=b.SCHEMA_VERSION or d['status']!='RESEARCH_CANDIDATE_ONLY' or d['production_authorized'] is not False:raise ValueError('promotion firewall mismatch')
        with tempfile.TemporaryDirectory() as td:
            out=b.export_candidate(Path(td)/'candidate.json',d['candidate']);written=json.loads(out.read_text())
            if written!=d:raise ValueError('DAEDALUS bridge payload mismatch')
        ok['daedalus']=True;details['daedalus']='same-instant research-candidate bridge exact-shape passed'
    except Exception as e:details['daedalus']=f'{type(e).__name__}: {e}'
    return SiblingValidationResult(ok['aion'],ok['argus'],ok['athena'],ok['daedalus'],details)
