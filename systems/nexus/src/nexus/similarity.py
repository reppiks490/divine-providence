from __future__ import annotations
from dataclasses import dataclass
import math
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
    """Detect content-level near duplicates without deleting either lineage entry.

    Repeated event timestamps require source_sequence on both inputs. Joining repeated
    timestamps without sequence identity would create a Cartesian product and inflate
    apparent overlap/identity.
    """

    def __init__(
        self,
        min_overlap:int=100,
        identical_threshold:float=.98,
        corr_threshold:float=.9999,
    ):
        if type(min_overlap) is not int or min_overlap < 1:
            raise ValueError("min_overlap must be a positive integer")
        for name,value in (
            ("identical_threshold",identical_threshold),
            ("corr_threshold",corr_threshold),
        ):
            v=float(value)
            if not math.isfinite(v) or not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be finite and in [0,1]")
        self.min_overlap=min_overlap
        self.identical_threshold=float(identical_threshold)
        self.corr_threshold=float(corr_threshold)

    @staticmethod
    def _prepare(name:str, frame:pd.DataFrame) -> tuple[pd.DataFrame,list[str]]:
        required={"event_ns","open","high","low","close"}
        missing=required-set(frame.columns)
        if missing:
            raise ValueError(f"{name}: missing required columns {sorted(missing)}")
        cols=["event_ns","open","high","low","close"]
        repeated=bool(frame["event_ns"].duplicated(keep=False).any())
        if repeated:
            if "source_sequence" not in frame.columns:
                raise ValueError(
                    f"{name}: repeated event_ns requires source_sequence for unambiguous overlap"
                )
            if frame.duplicated(["event_ns","source_sequence"]).any():
                raise ValueError(f"{name}: duplicate event_ns+source_sequence identity")
            cols.insert(1,"source_sequence")
            return frame[cols].copy(),["event_ns","source_sequence"]
        if "source_sequence" in frame.columns:
            cols.insert(1,"source_sequence")
        return frame[cols].copy(),["event_ns"]

    def compare(
        self,left_name:str,left:pd.DataFrame,right_name:str,right:pd.DataFrame
    )->NearDuplicateResult:
        a,left_keys=self._prepare(left_name,left)
        b,right_keys=self._prepare(right_name,right)

        repeated = (
            bool(a["event_ns"].duplicated(keep=False).any())
            or bool(b["event_ns"].duplicated(keep=False).any())
        )
        if repeated:
            if "source_sequence" not in a.columns or "source_sequence" not in b.columns:
                raise ValueError(
                    "repeated event_ns comparison requires source_sequence on both inputs"
                )
            keys=["event_ns","source_sequence"]
        else:
            keys=["event_ns"]

        z=a.merge(b,on=keys,suffixes=("_l","_r"),how="inner",validate="one_to_one")
        if not len(z):
            return NearDuplicateResult(left_name,right_name,0,0.0,float("nan"),False)

        same=pd.Series(True,index=z.index)
        for col in ["open","high","low","close"]:
            same &= z[f"{col}_l"].eq(z[f"{col}_r"])

        if len(z)>1 and z["close_l"].std(ddof=0)>0 and z["close_r"].std(ddof=0)>0:
            corr=float(z["close_l"].corr(z["close_r"]))
        else:
            corr=float("nan")
        frac=float(same.mean())
        corr_ok=math.isfinite(corr) and corr>=self.corr_threshold
        likely=len(z)>=self.min_overlap and (
            frac>=self.identical_threshold or corr_ok
        )
        return NearDuplicateResult(
            left_name,right_name,len(z),frac,corr,likely
        )
