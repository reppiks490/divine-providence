
from __future__ import annotations
from dataclasses import dataclass, asdict
import math, random

def mean(xs):
    return sum(xs)/len(xs) if xs else float("nan")

def bootstrap_mean_ci(values, n_bootstrap=5000, alpha=0.05, seed=12345):
    if not values:
        raise ValueError("values required")
    rng=random.Random(seed)
    n=len(values)
    boots=[]
    for _ in range(n_bootstrap):
        sample=[values[rng.randrange(n)] for _ in range(n)]
        boots.append(mean(sample))
    boots.sort()
    def q(p):
        pos=(len(boots)-1)*p
        lo=int(math.floor(pos)); hi=int(math.ceil(pos))
        return boots[lo] + (boots[hi]-boots[lo])*(pos-lo)
    return {"mean":mean(values),"low":q(alpha/2),"high":q(1-alpha/2),"n":n,"bootstrap_draws":n_bootstrap}

def sign_flip_pvalue(values, n_perm=5000, seed=67890):
    if not values:
        raise ValueError("values required")
    rng=random.Random(seed)
    obs=abs(mean(values))
    extreme=0
    for _ in range(n_perm):
        m=mean([x if rng.random()<0.5 else -x for x in values])
        if abs(m) >= obs:
            extreme += 1
    return (extreme+1)/(n_perm+1)

def purged_walk_forward_splits(n_rows, initial_train, validation_size, step, purge, embargo, holdout_start):
    if not (0 < initial_train < holdout_start < n_rows):
        raise ValueError("invalid train/holdout boundaries")
    folds=[]
    train_end=initial_train
    fold=1
    while True:
        val_start=train_end + purge
        val_end=val_start + validation_size
        if val_end + embargo > holdout_start:
            break
        folds.append({
            "fold":fold,
            "train":[0,train_end],
            "purge":[train_end,val_start],
            "validation":[val_start,val_end],
            "embargo":[val_end,val_end+embargo],
            "holdout_start":holdout_start
        })
        fold += 1
        train_end += step
    return folds

def bonferroni(p_values):
    m=max(1,len(p_values))
    return [min(1.0,p*m) for p in p_values]

def benjamini_hochberg(p_values):
    m=len(p_values)
    order=sorted(range(m), key=lambda i:p_values[i])
    adjusted=[1.0]*m
    prev=1.0
    for rank_rev, idx in enumerate(reversed(order), start=1):
        rank=m-rank_rev+1
        val=min(prev, p_values[idx]*m/rank)
        adjusted[idx]=min(1.0,val)
        prev=adjusted[idx]
    return adjusted

@dataclass
class MultipleTestingRecord:
    candidate_id: str
    family: str
    experiment_id: str
    raw_p: float
    metric: str
    corpus_id: str

def build_multiple_testing_ledger(records):
    raw=[r.raw_p for r in records]
    bon=bonferroni(raw)
    bh=benjamini_hochberg(raw)
    return [
        {**asdict(r),"bonferroni_p":bon[i],"bh_fdr_p":bh[i]}
        for i,r in enumerate(records)
    ]

def cluster_bootstrap_mean_ci(cluster_records, n_bootstrap=5000, alpha=0.05, seed=24680):
    records=list(cluster_records)
    if not records:
        raise ValueError("cluster_records required")
    rng=random.Random(seed)
    boots=[]
    for _ in range(n_bootstrap):
        net=0.0; trades=0
        for _ in range(len(records)):
            _,n,t=records[rng.randrange(len(records))]
            net+=n; trades+=t
        boots.append(net/trades if trades else 0.0)
    boots.sort()
    def q(p):
        pos=(len(boots)-1)*p; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
        return boots[lo]+(boots[hi]-boots[lo])*(pos-lo)
    total_net=sum(r[1] for r in records); total_trades=sum(r[2] for r in records)
    return {"mean":total_net/total_trades,"low":q(alpha/2),"high":q(1-alpha/2),"clusters":len(records),"trades":total_trades}
