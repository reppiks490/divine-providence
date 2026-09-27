from __future__ import annotations
from dataclasses import dataclass
import hashlib
import pandas as pd

@dataclass(frozen=True)
class NearDuplicateResult:
    left:str
    right:str
    overlap_rows:int
    identical_fraction:float
    close_correlation:float
    likely_near_duplicate:bool

class NearDuplicateDetector:
    """Detect content-level near duplicates without deleting either lineage entry."""
    def __init__(self,min_overlap:int=100,identical_threshold:float=.98,corr_threshold:float=.9999):
        self.min_overlap=min_overlap; self.identical_threshold=identical_threshold; self.corr_threshold=corr_threshold

    def compare(self,left_name:str,left:pd.DataFrame,right_name:str,right:pd.DataFrame)->NearDuplicateResult:
        cols=['event_ns','open','high','low','close']
        a=left[cols].copy(); b=right[cols].copy()
        z=a.merge(b,on='event_ns',suffixes=('_l','_r'),how='inner')
        if not len(z): return NearDuplicateResult(left_name,right_name,0,0.0,float('nan'),False)
        same=pd.Series(True,index=z.index)
        for c in ['open','high','low','close']:
            same &= (z[f'{c}_l']==z[f'{c}_r'])
        if len(z)>1 and z['close_l'].std(ddof=0)>0 and z['close_r'].std(ddof=0)>0:
            corr=float(z['close_l'].corr(z['close_r']))
        else:
            corr=float('nan')
        frac=float(same.mean())
        corr_ok = pd.notna(corr) and corr >= self.corr_threshold
        likely=len(z)>=self.min_overlap and (frac>=self.identical_threshold or corr_ok)
        return NearDuplicateResult(left_name,right_name,len(z),frac,corr,likely)
