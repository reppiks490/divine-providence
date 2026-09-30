from pathlib import Path
from nexus.timeutil import timestamp_to_ns
from nexus.ingest import iter_bars, BarClockPolicy, policy_from_manifest
from nexus.contracts import StreamIdentity, StreamManifest
from nexus.features import causal_bar_features


def test_fractional_epoch_preserved():
    ns,frac=timestamp_to_ns('1700000000.125')
    assert frac
    assert ns==1_700_000_000_125_000_000


def test_repeated_timestamps_preserve_sequence(tmp_path: Path):
    p=tmp_path/'x.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n100,1,3,0,2\n')
    rows=list(iter_bars(p,'s',emit_unsealed_terminal=True))
    assert [r.event_ns for r in rows]==[100_000_000_000,100_000_000_000]
    assert [r.source_sequence for r in rows]==[0,1]


def test_nonfinite_epoch_is_rejected():
    import pytest
    for value in ('NaN','Infinity','-Infinity'):
        with pytest.raises(ValueError):
            timestamp_to_ns(value)


def test_manifest_policy_requires_review_for_explicit_clock():
    import pytest
    ident=StreamIdentity('csv','CME','NQ','1','csv','x.csv','a'*64)
    manifest=StreamManifest(ident,10,['time','open','high','low','close'],0,9,60,1.0,0,0,0)
    with pytest.raises(ValueError,match='reviewed=True'):
        policy_from_manifest(manifest,source_stamp='close')
    policy=policy_from_manifest(manifest,source_stamp='close',reviewed=True)
    assert policy.basis=='verified_bar_close'
    assert 'clock_policy_reviewed' in policy.extra_quality_flags


def test_bar_clock_policy_rejects_negative_delay_and_bad_cadence():
    import pytest
    with pytest.raises(ValueError,match='availability_delay_ns'):
        BarClockPolicy(availability_delay_ns=-1)
    with pytest.raises(ValueError,match='cadence_ns'):
        BarClockPolicy(cadence_ns=0)
    with pytest.raises(ValueError,match='open-stamped'):
        BarClockPolicy(source_stamp='open')
    with pytest.raises(ValueError,match='unknown source_stamp'):
        BarClockPolicy(source_stamp='nonsense')


def test_causal_bar_features_reject_invalid_log_domain_and_infinity():
    import pandas as pd
    import pytest
    good=pd.DataFrame({
        'open':[1.,2.],'high':[2.,3.],'low':[.5,1.5],'close':[1.5,2.5]
    })
    out=causal_bar_features(good)
    assert list(out.index)==[0,1]

    zero=good.copy();zero.loc[1,'close']=0.0
    with pytest.raises(ValueError,match='strictly positive'):
        causal_bar_features(zero)

    inf=good.copy();inf.loc[1,'high']=float('inf')
    with pytest.raises(ValueError,match='infinite'):
        causal_bar_features(inf)


def test_causal_bar_features_reject_negative_or_infinite_volume():
    import pandas as pd
    import pytest
    base=pd.DataFrame({
        'open':[1.,2.],'high':[2.,3.],'low':[.5,1.5],'close':[1.5,2.5],
        'volume':[1.,2.],
    })
    bad=base.copy();bad.loc[1,'volume']=-1
    with pytest.raises(ValueError,match='non-negative'):
        causal_bar_features(bad)
    bad=base.copy();bad.loc[1,'volume']=float('inf')
    with pytest.raises(ValueError,match='infinite'):
        causal_bar_features(bad)


def test_causal_bar_features_reject_malformed_volume_text():
    import pandas as pd
    import pytest
    bad=pd.DataFrame({
        'open':[1.,2.],'high':[2.,3.],'low':[.5,1.5],'close':[1.5,2.5],
        'volume':[1.,'not-volume'],
    })
    with pytest.raises(ValueError,match='volume feature input must be numeric'):
        causal_bar_features(bad)
