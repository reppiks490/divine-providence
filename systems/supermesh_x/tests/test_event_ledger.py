from scripts.event_ledger import build_ledger_entry, verify_ledger


def test_ledger_preserves_event_and_observation_clocks():
    entry = build_ledger_entry({'id':'e1','event_time':'2026-09-24T14:00:00Z','published_time':'2026-09-24T14:00:03Z','retrieved_time':'2026-09-24T14:00:10Z','text':'public statement'})
    assert entry['clock']['event_time'].endswith('Z')
    assert entry['clock']['published_time'].endswith('Z')
    assert entry['clock']['retrieved_time'].endswith('Z')
    assert entry['record_hash']


def test_ledger_hash_chain_verifies():
    first = build_ledger_entry({'id':'e1','event_time':'2026-09-24T14:00:00Z','text':'one'})
    second = build_ledger_entry({'id':'e2','event_time':'2026-09-24T14:01:00Z','text':'two'}, previous=first)
    report = verify_ledger([first, second])
    assert report['valid'] is True
