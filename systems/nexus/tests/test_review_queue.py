from nexus.contracts import StreamIdentity, StreamManifest
from nexus.review_queue import build_representation_review_queue


def _m(symbol='NQ', flags=None, kind='fixed_time_candidate', hc=.99, cadence=60):
    ident=StreamIdentity('csv','CME',symbol,'1','csv_export',f'{symbol}.csv','a'*64)
    return StreamManifest(ident,100,['time','open','high','low','close'],1,2,cadence,hc,0,0,0,quality_flags=list(flags or []),metadata={'representation_hypothesis':{'kind':kind,'confidence':hc}})


def test_review_queue_never_infers_timestamp_semantics():
    q=build_representation_review_queue([_m()])
    assert q.verify() and len(q.candidates)==1
    c=q.candidates[0]
    assert c.fixed_interval_candidate_ns==60
    assert c.timestamp_semantics_candidate=='UNKNOWN_REQUIRES_REVIEW'
    assert c.authoritative is False


def test_review_queue_prioritizes_integrity_and_event_ambiguity():
    clean=_m('ES')
    risky=_m('NQ',flags=['claim_mismatch','cadence_ambiguous'],kind='event_or_derived_candidate',hc=.5,cadence=None)
    q=build_representation_review_queue([clean,risky])
    assert q.candidates[0].symbol=='NQ' and q.candidates[0].priority=='P0'
    assert q.candidates[-1].symbol=='ES' and q.candidates[-1].priority=='P2'
    assert q.candidates[0].fixed_interval_candidate_ns is None


def test_review_queue_deduplicates_exact_stream_copies():
    a=_m('NQ')
    b=_m('NQ')
    b.identity=StreamIdentity(
        b.identity.source_id,b.identity.venue,b.identity.symbol,
        b.identity.filename_claim,b.identity.representation,
        'copy/NQ.csv',b.identity.raw_sha256,
    )
    q=build_representation_review_queue([b,a])
    assert len(q.candidates)==1
    assert q.candidates[0].source_path=='NQ.csv'


def test_review_queue_malformed_confidence_is_p0_not_silently_clean():
    m=_m('NQ',hc=float('nan'))
    q=build_representation_review_queue([m])
    assert len(q.candidates)==1
    row=q.candidates[0]
    assert row.priority=='P0'
    assert row.cadence_confidence==0.0
    assert row.hypothesis_confidence==0.0
    assert 'cadence_confidence_nonfinite' in row.review_reasons
    assert 'hypothesis_confidence_nonfinite' in row.review_reasons
