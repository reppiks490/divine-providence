from daedalus.hypotheses import benjamini_hochberg


def test_bh_monotone_and_bounded():
    q=benjamini_hochberg([0.01,0.04,0.03,0.9])
    assert all(0<=v<=1 for v in q)
    assert q[0] <= q[1]
