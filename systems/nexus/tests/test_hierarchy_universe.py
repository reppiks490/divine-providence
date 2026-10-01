import numpy as np
import pandas as pd
from nexus.contracts import StreamIdentity,StreamManifest
from nexus.hierarchy import fuse_representations_by_symbol,HierarchicalFactorEngine
from nexus.synthetic import EnsembleDefinition
from nexus.universe import build_factor_universe


def test_representation_fusion_prevents_vote_count_bias():
    idx=range(5)
    r=pd.DataFrame({"A:1":[.01]*5,"A:2":[.011]*5,"A:3":[.009]*5,"B:1":[-.01]*5},index=idx)
    fused,dis,agree,cov=fuse_representations_by_symbol(r,{"A:1":"A","A:2":"A","A:3":"A","B:1":"B"})
    assert list(fused.columns)==["A","B"]
    assert abs(fused.iloc[0]["A"]-.01)<1e-9
    assert fused.iloc[0]["B"]==-.01
    assert cov.iloc[0]["A"]==1.0
    assert cov.iloc[0]["B"]==1.0


def test_quality_weight_can_suppress_bad_representation_without_imputation():
    r=pd.DataFrame({"A:good":[.01],"A:bad":[1.0]})
    fused,_,_,_=fuse_representations_by_symbol(r,{"A:good":"A","A:bad":"A"},quality_weights={"A:good":1,"A:bad":0})
    assert fused.iloc[0]["A"]==.01


def _m(sym,h,score=1.0,duplicate=None):
    i=StreamIdentity("csv","X",sym,"1","csv_export",f"{sym}-{h}.csv",h*64)
    return StreamManifest(i,100,["time","open","high","low","close"],0,100,60,score,0,0,0,duplicate,[],{"logical_sha256":h*64,"usable_ohlc_rows":100})


def test_universe_deduplicates_before_symbol_cap():
    a=_m("A","a");a2=_m("A","a",duplicate=a.identity.source_path);a3=_m("A","b")
    b=_m("B","c")
    selected,decisions=build_factor_universe([a,a2,a3,b],max_streams_per_symbol=1)
    assert len(selected)==2
    reasons=[d.reason for d in decisions]
    assert "exact_byte_duplicate" in reasons
    assert "symbol_representation_cap" in reasons


def test_hierarchical_factor_runs_on_symbol_plane():
    n=80;idx=pd.RangeIndex(n);x=np.linspace(0,.2,n)
    r=pd.DataFrame({"A:1":np.sin(x)/100,"A:2":np.sin(x)/100+.00001,"B:1":np.cos(x)/100},index=idx)
    d=EnsembleDefinition("H",("A","B"),methods=("equal","inverse_vol"),window=30,min_periods=10,rebalance_every=5)
    result=HierarchicalFactorEngine().build(r,{"A:1":"A","A:2":"A","B:1":"B"},d)
    assert not result.factor.empty
    assert set(result.symbol_returns)=={"A","B"}


def test_sampling_then_family_balancing_prevents_dense_timeframe_vote_inflation():
    idx=range(3)
    r=pd.DataFrame({
        "NQ:t1":[0.03]*3,
        "NQ:t2":[0.031]*3,
        "NQ:t3":[0.029]*3,
        "NQ:t4":[0.032]*3,
        "NQ:tick":[-0.02]*3,
        "NQ:range":[-0.021]*3,
        "NQ:renko":[-0.019]*3,
    },index=idx)
    symbol={col:"NQ" for col in r.columns}
    family={
        "NQ:t1":"regular_candles",
        "NQ:t2":"regular_candles",
        "NQ:t3":"regular_candles",
        "NQ:t4":"regular_candles",
        "NQ:tick":"regular_candles",
        "NQ:range":"regular_candles",
        "NQ:renko":"renko",
    }
    construction={
        "NQ:t1":"time_bar",
        "NQ:t2":"time_bar",
        "NQ:t3":"time_bar",
        "NQ:t4":"time_bar",
        "NQ:tick":"tick",
        "NQ:range":"range",
        "NQ:renko":"range",
    }
    fused,_,agreement,coverage=fuse_representations_by_symbol(
        r,symbol,stream_to_family=family,stream_to_construction=construction
    )
    assert fused.iloc[0]["NQ"] < 0.0
    assert agreement.iloc[0]["NQ"] >= 0.5
    assert coverage.iloc[0]["NQ"] == 1.0


def test_build_from_manifests_fails_closed_on_unresolved_time_family():
    from nexus.hierarchy import HierarchicalFactorEngine
    unresolved=_m("NQ","d")
    unresolved.metadata["representation_claim"]={
        "family":"unknown","sampling_domain":"time","construction":"time_bar"
    }
    returns=pd.DataFrame({unresolved.identity.stream_id:[0.01,0.01,0.01]})
    d=EnsembleDefinition("H",("NQ",),methods=("equal",),window=2,min_periods=1,rebalance_every=1)
    import pytest
    with pytest.raises(ValueError,match="representation identity unresolved"):
        HierarchicalFactorEngine().build_from_manifests(returns,[unresolved],d)


def test_build_from_manifests_rejects_inferred_identity_by_default():
    from nexus.hierarchy import HierarchicalFactorEngine
    m=_m("NQ","e")
    m.metadata["representation_claim"]={
        "family":"regular_candles",
        "sampling_domain":"time",
        "construction":"time_bar",
        "authoritative":False,
    }
    returns=pd.DataFrame({m.identity.stream_id:[0.01,0.01,0.01]})
    d=EnsembleDefinition("H",("NQ",),methods=("equal",),window=2,min_periods=1,rebalance_every=1)
    import pytest
    with pytest.raises(ValueError,match="representation identity unresolved"):
        HierarchicalFactorEngine().build_from_manifests(returns,[m],d)


def test_build_from_manifests_accepts_authoritative_identity():
    from nexus.hierarchy import HierarchicalFactorEngine
    m=_m("NQ","f")
    m.metadata["representation_claim"]={
        "family":"regular_candles",
        "price_geometry":"standard_ohlc",
        "sampling_domain":"time",
        "construction":"time_bar",
        "authoritative":True,
    }
    returns=pd.DataFrame({m.identity.stream_id:[0.01,0.01,0.01,0.01]})
    d=EnsembleDefinition("H",("NQ",),methods=("equal",),window=2,min_periods=1,rebalance_every=1)
    result=HierarchicalFactorEngine().build_from_manifests(returns,[m],d)
    assert list(result.symbol_returns.columns)==["NQ"]


def test_universe_owner_exclusion_preserves_data_but_blocks_selection():
    nq=_m("NQ1!","e")
    eth=_m("ETHUSD","f")
    selected,decisions=build_factor_universe(
        [nq,eth],excluded_symbols=("ETHUSD","SOLUSD","MBT1!")
    )
    assert nq.identity.stream_id in selected
    assert eth.identity.stream_id not in selected
    d=next(x for x in decisions if x.stream_id==eth.identity.stream_id)
    assert d.reason=="owner_excluded_symbol"


def test_price_geometry_balancing_prevents_geometry_count_bias():
    r=pd.DataFrame({
        "NQ:s1":[0.03]*3,
        "NQ:s2":[0.031]*3,
        "NQ:s3":[0.029]*3,
        "NQ:s4":[0.032]*3,
        "NQ:ha":[-0.02]*3,
    })
    symbol={col:"NQ" for col in r.columns}
    family={col:"profile_view" for col in r.columns}
    geometry={
        "NQ:s1":"standard_ohlc",
        "NQ:s2":"standard_ohlc",
        "NQ:s3":"standard_ohlc",
        "NQ:s4":"standard_ohlc",
        "NQ:ha":"heikin_ashi",
    }
    construction={col:"time_bar" for col in r.columns}
    fused,_,_,_=fuse_representations_by_symbol(
        r,symbol,
        stream_to_family=family,
        stream_to_geometry=geometry,
        stream_to_construction=construction,
    )
    # Four standard-geometry files collapse to one geometry plane before the
    # single HA geometry plane is fused, so file count cannot dominate.
    assert abs(fused.iloc[0]["NQ"]-0.00525) < 0.002


def test_universe_duplicate_choice_is_input_order_independent():
    # Same logical payload presented under two paths must resolve deterministically,
    # independent of caller iteration order.
    a=_m("A","a")
    a_alt=_m("A","a")
    a_alt.identity = StreamIdentity(
        a_alt.identity.source_id,a_alt.identity.venue,a_alt.identity.symbol,
        a_alt.identity.filename_claim,a_alt.identity.representation,
        "zzz.csv",a_alt.identity.raw_sha256,
    )
    first=build_factor_universe([a_alt,a])
    second=build_factor_universe([a,a_alt])
    assert first[0]==second[0]
    assert [(d.stream_id,d.selected,d.reason) for d in first[1]] == [
        (d.stream_id,d.selected,d.reason) for d in second[1]
    ]


def test_universe_rejects_negative_symbol_cap():
    import pytest
    with pytest.raises(ValueError,match='max_streams_per_symbol'):
        build_factor_universe([_m("A","a")],max_streams_per_symbol=-1)


def test_hierarchy_rejects_invalid_quality_and_missing_manifest_identity():
    import pytest
    r=pd.DataFrame({'s':[0.01,0.02]})
    with pytest.raises(ValueError,match='quality weight'):
        fuse_representations_by_symbol(
            r,{'s':'NQ'},quality_weights={'s':float('nan')}
        )

    d=EnsembleDefinition(
        'H',('NQ',),methods=('equal',),window=2,min_periods=1,rebalance_every=1
    )
    with pytest.raises(ValueError,match='representation identity unresolved'):
        HierarchicalFactorEngine().build_from_manifests(r,[],d)


def test_hierarchy_rejects_stream_id_collision_across_distinct_bytes():
    import pytest
    a=_m('NQ','a')
    b=_m('NQ','b')
    # Explicitly emulate a compact-id collision while preserving distinct raw bytes.
    object.__setattr__(b.identity,'source_id',a.identity.source_id)
    object.__setattr__(b.identity,'symbol',a.identity.symbol)
    object.__setattr__(b.identity,'raw_sha256','a'*12+'b'*52)
    # raw hash prefix now collides with a.
    assert b.identity.stream_id==a.identity.stream_id
    returns=pd.DataFrame({a.identity.stream_id:[.01,.02]})
    d=EnsembleDefinition(
        'H',('NQ',),methods=('equal',),window=2,min_periods=1,rebalance_every=1
    )
    with pytest.raises(ValueError,match='collision'):
        HierarchicalFactorEngine().build_from_manifests(returns,[a,b],d)


def test_universe_rejects_compact_stream_id_hash_prefix_collision():
    import pytest
    from nexus.contracts import StreamIdentity, StreamManifest

    def mk(raw,path):
        ident=StreamIdentity("src","CME","NQ1!","20",source_path=path,raw_sha256=raw)
        return StreamManifest(
            ident,10,["time","open","high","low","close"],
            1,10,1_200_000_000_000,1.0,0,0,0,
            metadata={"usable_ohlc_rows":10},
        )

    a=mk("a"*12+"1"*52,"a.csv")
    b=mk("a"*12+"2"*52,"b.csv")
    assert a.identity.stream_id==b.identity.stream_id
    with pytest.raises(ValueError,match="stream_id collision"):
        build_factor_universe([a,b])


def test_universe_rejects_coerced_symbol_cap():
    import pytest
    with pytest.raises(ValueError,match="max_streams_per_symbol"):
        build_factor_universe([_m("A","a")],max_streams_per_symbol=1.5)
    with pytest.raises(ValueError,match="max_streams_per_symbol"):
        build_factor_universe([_m("A","a")],max_streams_per_symbol=True)


def test_reviewed_registry_can_authorize_exact_bytes_for_model_plane():
    from nexus.review_registry import ReviewedRepresentationRecord,ReviewedRepresentationRegistry
    m=_m("NQ","9")
    m.metadata["representation_claim"]={
        "family":"regular_candles",
        "price_geometry":"standard_ohlc",
        "sampling_domain":"time",
        "construction":"time_bar",
        "authoritative":False,
    }
    record=ReviewedRepresentationRecord(
        stream_id=m.identity.stream_id,
        version="1",
        canonical_instrument="NQ",
        asset_class="futures",
        representation_class="regular-1m",
        kind="time_bar",
        timestamp_semantics="bar_close",
        review_evidence_sha256="e"*64,
        reviewed_by="human-review",
        venue="X",
        raw_sha256=m.identity.raw_sha256,
        chart_view_family="regular_candles",
        price_geometry="standard_ohlc",
        sampling_domain="time",
        sampling_construction="time_bar",
        native_setting="1m",
    )
    registry=ReviewedRepresentationRegistry()
    registry.register(record);registry.activate(m.identity.stream_id,"1")
    returns=pd.DataFrame({m.identity.stream_id:[.01,.01,.01,.01]})
    d=EnsembleDefinition("H",("NQ",),methods=("equal",),window=2,min_periods=1,rebalance_every=1)
    result=HierarchicalFactorEngine().build_from_manifests(
        returns,[m],d,reviewed_registry=registry
    )
    assert list(result.symbol_returns.columns)==["NQ"]


def test_reviewed_registry_model_authority_is_exact_byte_bound():
    import pytest
    from nexus.review_registry import ReviewedRepresentationRecord,ReviewedRepresentationRegistry
    m=_m("NQ","8")
    record=ReviewedRepresentationRecord(
        stream_id=m.identity.stream_id,
        version="1",
        canonical_instrument="NQ",
        asset_class="futures",
        representation_class="regular-1m",
        kind="time_bar",
        timestamp_semantics="bar_close",
        review_evidence_sha256="e"*64,
        reviewed_by="human-review",
        venue="X",
        raw_sha256="7"*64,
        chart_view_family="regular_candles",
        price_geometry="standard_ohlc",
        sampling_domain="time",
        sampling_construction="time_bar",
    )
    registry=ReviewedRepresentationRegistry()
    registry.register(record);registry.activate(m.identity.stream_id,"1")
    returns=pd.DataFrame({m.identity.stream_id:[.01,.01,.01]})
    d=EnsembleDefinition("H",("NQ",),methods=("equal",),window=2,min_periods=1,rebalance_every=1)
    with pytest.raises(ValueError,match="raw_sha256"):
        HierarchicalFactorEngine().build_from_manifests(
            returns,[m],d,reviewed_registry=registry
        )
