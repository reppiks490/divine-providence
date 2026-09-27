from daedalus.splits import PurgedWalkForwardSplit


def test_purge_and_embargo_geometry():
    s=PurgedWalkForwardSplit(3,100,30,5,7)
    folds=s.split(300)
    assert folds
    for f in folds:
        assert f.train_idx[-1] <= f.test_idx[0]-6
    if len(folds)>1:
        assert folds[1].test_idx[0] >= folds[0].test_idx[-1]+1+7
