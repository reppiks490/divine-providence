from nexus.contracts import StreamIdentity, StreamManifest
from nexus.corpus_recovery import HistoricalCorpusAnchor, build_corpus_recovery_plan


def _m(raw: str, rows: int = 10):
    ident = StreamIdentity("zipcsv", "CME", "NQ1!", "1", source_path=f"{raw}.csv", raw_sha256=raw * 64)
    return StreamManifest(
        ident, rows, ["time", "open", "high", "low", "close"],
        1, rows, 60, 1.0, 0, 0, 0,
        quality_flags=[], metadata={}
    )


def test_recovery_plan_separates_unique_content_from_duplicate_lineage():
    a = _m("a", 10)
    b = _m("b", 20)
    # same raw bytes as a, separate manifest entry
    dup_ident = StreamIdentity("zipcsv", "CME", "ES1!", "1", source_path="dup.csv", raw_sha256="a" * 64)
    dup = StreamManifest(dup_ident, 10, ["time","open","high","low","close"], 1, 10, 60, 1.0, 0, 0, 0)
    anchor = HistoricalCorpusAnchor(usable_entries=6, usable_rows=100, distinct_byte_contents=5, archive_count=3, label="prior")
    out = build_corpus_recovery_plan([a,b,dup], anchor, owner_expected_min_entries=8)
    assert out["current"]["usable_entries"] == 3
    assert out["current"]["distinct_byte_contents"] == 2
    assert out["current"]["duplicate_entries"] == 1
    assert out["gaps_relative_to_historical_anchor"]["usable_entry_gap"] == 3
    assert out["gaps_relative_to_historical_anchor"]["distinct_byte_content_gap_floor"] == 3
    # historical duplicates = 1 and current duplicates = 1, so no duplicate-only gap
    assert out["gaps_relative_to_historical_anchor"]["duplicate_entry_gap"] == 0
    assert out["owner_expected_min_entry_gap"] == 5
    assert out["acceptance"]["coverage_claim_allowed"] is False


def test_recovery_plan_ignores_appledouble_and_empty_entries():
    good = _m("c", 12)
    appledouble = _m("d", 5)
    appledouble.quality_flags.append("appledouble")
    empty = _m("e", 0)
    anchor = HistoricalCorpusAnchor(1, 12, 1, 1)
    out = build_corpus_recovery_plan([good, appledouble, empty], anchor)
    assert out["current"]["usable_entries"] == 1
    assert out["current"]["usable_rows"] == 12
    assert out["current"]["distinct_byte_contents"] == 1
