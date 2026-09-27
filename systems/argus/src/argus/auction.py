from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuctionProfile:
    poc: float
    value_low: float
    value_high: float
    hvn: tuple[float, ...]
    lvn: tuple[float, ...]


def volume_profile(prices: list[float], volumes: list[float], tick_size: float, value_fraction: float = 0.70) -> AuctionProfile:
    if len(prices)!=len(volumes) or not prices or tick_size<=0:
        raise ValueError("valid equal-length prices/volumes and positive tick_size required")
    bins: dict[float,float]={}
    for p,v in zip(prices,volumes):
        k=round(round(p/tick_size)*tick_size, 10)
        bins[k]=bins.get(k,0.0)+max(0.0,float(v))
    poc=max(bins,key=bins.get)
    target=sum(bins.values())*value_fraction
    chosen=[]; cum=0.0
    for k,v in sorted(bins.items(), key=lambda kv:kv[1], reverse=True):
        chosen.append(k); cum+=v
        if cum>=target: break
    vals=list(bins.values()); mean=sum(vals)/len(vals)
    hvn=tuple(sorted(k for k,v in bins.items() if v>=1.5*mean))
    lvn=tuple(sorted(k for k,v in bins.items() if v<=0.5*mean))
    return AuctionProfile(poc,min(chosen),max(chosen),hvn,lvn)
