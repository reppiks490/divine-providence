from scripts.provider_health_merge import merge_health_snapshots, apply_quota_headroom


def test_merge_rejects_older_snapshot_for_same_provider():
    a={'provider':'exa','observed_at_ms':200,'health':0.7,'circuit':'closed','sequence':4}
    b={'provider':'exa','observed_at_ms':100,'health':0.1,'circuit':'open','sequence':3}
    out=merge_health_snapshots([a,b])
    assert out['exa']['sequence']==4
    assert out['exa']['health']==0.7


def test_merge_uses_sequence_before_wall_clock_for_order_safety():
    newer={'provider':'tavily','observed_at_ms':100,'health':0.8,'circuit':'closed','sequence':9}
    skewed={'provider':'tavily','observed_at_ms':9999,'health':0.2,'circuit':'open','sequence':8}
    out=merge_health_snapshots([newer,skewed])
    assert out['tavily']['sequence']==9


def test_equal_sequence_merges_conservatively():
    a={'provider':'p','observed_at_ms':100,'health':0.9,'circuit':'closed','sequence':2}
    b={'provider':'p','observed_at_ms':110,'health':0.4,'circuit':'open','sequence':2}
    out=merge_health_snapshots([a,b])['p']
    assert out['health']==0.4 and out['circuit']=='open'


def test_quota_headroom_penalizes_health_without_opening_authority():
    row={'provider':'p','health':0.9,'circuit':'closed','sequence':1,'observed_at_ms':1}
    out=apply_quota_headroom(row, remaining=5, limit=100)
    assert out['health'] < 0.9
    assert out['quota_headroom']==0.05
    assert 'authority' not in out


def test_unknown_quota_is_conservative_but_not_failure():
    row={'provider':'p','health':0.8,'circuit':'closed','sequence':1,'observed_at_ms':1}
    out=apply_quota_headroom(row, remaining=None, limit=None)
    assert out['health']==0.8 and out['quota_headroom'] is None
