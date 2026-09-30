import numpy as np
from nexus.latent import CausalPCAFactor
from nexus.representation import robust_representation_consensus


def test_causal_pca_current_row_does_not_change_its_own_fit():
    rng=np.random.default_rng(7)
    history=[{'a':float(x),'b':float(2*x+rng.normal(0,.05))} for x in rng.normal(size=30)]
    f1=CausalPCAFactor(window=40,min_obs=20)
    f2=CausalPCAFactor(window=40,min_obs=20)
    for i,row in enumerate(history):
        f1.update(i,row); f2.update(i,row)
    p1=f1.update(100,{'a':1.0,'b':2.0})
    p2=f2.update(100,{'a':1000.0,'b':-1000.0})
    # Loadings/explained variance are fitted on identical prior history only.
    assert p1.loadings==p2.loadings
    assert abs(p1.explained_variance-p2.explained_variance)<1e-12
    assert p1.score!=p2.score


def test_representation_consensus_downweights_outlier_without_merging_identity():
    r=robust_representation_consensus('NQ',1,{'time':.01,'renko':.011,'ha':.009,'bad':.50})
    assert r.representation_count==4
    assert abs(r.consensus_return-.01)<.02
    assert r.contributions['bad'] < r.contributions['time']
    assert set(r.contributions)=={'time','renko','ha','bad'}


def test_empty_representation_consensus_is_missing_not_zero():
    r=robust_representation_consensus('NQ',1,{})
    assert r.representation_count==0
    assert np.isnan(r.consensus_return)
    assert np.isnan(r.disagreement)
    assert np.isnan(r.directional_agreement)
