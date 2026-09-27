from __future__ import annotations

from .contracts import EvidenceTier, MicrostructureFeature


def candle_pressure(*, event_time_ns:int, source_id:str, open_:float, high:float, low:float, close:float, volume:float|None=None) -> list[MicrostructureFeature]:
    if high < low:
        raise ValueError("high below low")
    rng=max(high-low,1e-12)
    body=(close-open_)/rng
    close_loc=((close-low)/rng)*2-1
    vol=float(volume) if volume is not None else 0.0
    return [
        MicrostructureFeature("candle_body_pressure",max(-1,min(1,body)),EvidenceTier.CANDLE_PROXY,event_time_ns,source_id,"OHLC proxy; not trade flow"),
        MicrostructureFeature("close_location_pressure",max(-1,min(1,close_loc)),EvidenceTier.CANDLE_PROXY,event_time_ns,source_id,"OHLC proxy; not L2"),
        MicrostructureFeature("reported_volume",vol,EvidenceTier.CANDLE_PROXY,event_time_ns,source_id,"bar-level volume only"),
    ]
