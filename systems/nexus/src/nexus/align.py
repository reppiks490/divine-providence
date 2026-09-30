from __future__ import annotations
import pandas as pd

class AlignmentError(ValueError): pass

class CausalAligner:
    """Backward-as-of align streams without inventing future observations.

    Inputs require `event_ns`, `source_sequence`, and a value column. Repeated event times are
    allowed only when source_sequence is unique. Driver rows remain intact.
    """
    def __init__(self, max_age_ns:int|None=None, allow_exact_matches:bool=True):
        if max_age_ns is not None and int(max_age_ns) < 0:
            raise ValueError("max_age_ns must be non-negative or None")
        if type(allow_exact_matches) is not bool:
            raise TypeError("allow_exact_matches must be bool")
        self.max_age_ns=None if max_age_ns is None else int(max_age_ns)
        self.allow_exact_matches=allow_exact_matches

    @staticmethod
    def _validate(df:pd.DataFrame,name:str,time_col:str="event_ns"):
        required={time_col,'source_sequence'}
        if not required.issubset(df.columns): raise AlignmentError(f"{name}: missing {required-set(df.columns)}")
        if (df[time_col].diff().dropna()<0).any(): raise AlignmentError(f"{name}: backward timestamps")
        if df.duplicated([time_col,'source_sequence']).any(): raise AlignmentError(f"{name}: duplicate time+sequence identity")

    def align(self, driver:pd.DataFrame, others:dict[str,pd.DataFrame], value_col:str='close', time_col:str='event_ns') -> pd.DataFrame:
        self._validate(driver,'driver',time_col)
        if value_col not in driver: raise AlignmentError(f"driver missing {value_col}")
        out=driver[[time_col,'source_sequence',value_col]].copy().rename(columns={value_col:'driver'})
        # merge_asof needs one row per right key. For repeated source event_ns, the final source_sequence
        # is the last known state at that exact clock instant; identity remains available in source data.
        for name,df in others.items():
            self._validate(df,name,time_col)
            if value_col not in df: raise AlignmentError(f"{name}: missing {value_col}")
            right=df[[time_col,'source_sequence',value_col]].copy()
            right=right.sort_values([time_col,'source_sequence'],kind='stable').groupby(time_col,as_index=False,sort=False).tail(1)
            right=right.rename(columns={value_col:name,'source_sequence':f'{name}:sequence'})
            out=pd.merge_asof(
                out.sort_values(time_col,kind='stable'), right.sort_values(time_col,kind='stable'),
                on=time_col, direction='backward', tolerance=self.max_age_ns,
                allow_exact_matches=self.allow_exact_matches,
            )
        return out
