from pathlib import Path
import pytest

from nexus.filename import parse_market_filename, timeframe_claim_to_ns
from nexus.representation import RepresentationKind, RepresentationPolicy, TimestampSemantics
from nexus.contracts import QualityFlag


def test_download_copy_suffix_is_not_timeframe():
    x=parse_market_filename(Path('CME_MINI_DL_NQ1!, 1S 4.csv'))
    assert x.venue=='CME'
    assert x.symbol=='NQ1!'
    assert x.timeframe_claim=='1S'
    assert x.copy_ordinal==4
    assert x.raw_claim=='1S 4'
    assert timeframe_claim_to_ns(x.timeframe_claim)==1_000_000_000


def test_numeric_claim_means_minutes_and_month_is_not_fixed():
    assert timeframe_claim_to_ns('60')==3_600_000_000_000
    assert timeframe_claim_to_ns('1D')==86_400_000_000_000
    assert timeframe_claim_to_ns('1M') is None


def test_event_bar_never_uses_observed_cadence_as_completion_offset():
    p=RepresentationPolicy('renko-10',RepresentationKind.EVENT_BAR,TimestampSemantics.EVENT_COMPLETION,reviewed=True)
    cp=p.to_clock_policy()
    t=1_700_000_000_000_000_000
    event,available,flags,basis=cp.resolve(t)
    assert event==t and available==t
    assert QualityFlag.EVENT_DRIVEN_REPRESENTATION.value in flags
    assert QualityFlag.CLOCK_POLICY_REVIEWED.value in flags
    assert basis=='verified_bar_close'


def test_open_stamped_event_bar_is_rejected():
    with pytest.raises(ValueError):
        RepresentationPolicy('range',RepresentationKind.EVENT_BAR,TimestampSemantics.BAR_OPEN,fixed_interval_ns=60_000_000_000)
