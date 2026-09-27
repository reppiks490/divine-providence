#!/usr/bin/env python3
"""Integrated, replayable public-event fabric for market-impact analysis."""
try:
    from .event_dedup import cluster_events
    from .event_ledger import build_ledger_entry, verify_ledger
    from .shock_graph import build_shock_graph
    from .watchlist_priority import score_mover
    from .confidence_decay import decayed_confidence
    from .replay_bundle import build_replay_bundle
except ImportError:
    from event_dedup import cluster_events
    from event_ledger import build_ledger_entry, verify_ledger
    from shock_graph import build_shock_graph
    from watchlist_priority import score_mover
    from confidence_decay import decayed_confidence
    from replay_bundle import build_replay_bundle


def process_event_batch(events, reactions, cutoff, evidence, market, priority_inputs,
                        base_confidence, age_minutes, conflict_strength, bucket_seconds=120):
    clusters=cluster_events(events,bucket_seconds=bucket_seconds)
    ledger=[]
    previous=None
    for cluster in clusters:
        representative=dict(cluster['representative'])
        representative.setdefault('id',cluster['cluster_id'])
        entry=build_ledger_entry(representative,previous=previous)
        ledger.append(entry)
        previous=entry
    replay_event=clusters[0]['representative'] if clusters else {'id':'none','event_time':cutoff,'text':''}
    replay=build_replay_bundle(replay_event,evidence=evidence,market=market,cutoff=cutoff)
    return {
        'cluster_count':len(clusters),
        'clusters':clusters,
        'ledger':ledger,
        'ledger_verification':verify_ledger(ledger),
        'shock_graph':build_shock_graph(reactions),
        'priority':score_mover(**priority_inputs),
        'confidence':decayed_confidence(base_confidence,age_minutes=age_minutes,conflict_strength=conflict_strength),
        'replay':replay,
        'policy':'public-event evidence fabric; descriptive market attribution only',
    }
