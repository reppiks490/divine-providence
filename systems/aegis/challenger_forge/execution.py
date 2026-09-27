
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class CostScenario:
    spread_points: float = 0.25
    slippage_points: float = 0.25
    fee_points_equivalent: float = 0.0
    latency_bars: int = 1

    @property
    def round_trip_cost_points(self):
        return 2.0*(self.spread_points/2.0 + self.slippage_points) + self.fee_points_equivalent

def next_bar_shadow_pnl(close, signals, contracts=None, sessions=None, cost=None):
    if cost is None:
        cost=CostScenario()
    pnl=[]
    latency=max(1,int(cost.latency_bars))
    for i,s in enumerate(signals):
        if not s or not s.get("direction"):
            continue
        j=i+latency
        if j>=len(close):
            continue
        if contracts is not None and contracts[j]!=contracts[i]:
            continue
        if sessions is not None and sessions[j]!=sessions[i]:
            continue
        raw=s["direction"]*(close[j]-close[i])
        pnl.append({
            "signal_index":i,
            "exit_index":j,
            "direction":s["direction"],
            "raw_points":raw,
            "cost_points":cost.round_trip_cost_points,
            "net_points":raw-cost.round_trip_cost_points
        })
    return pnl

def stressed_partial_fill_pnl(close, signals, contracts=None, sessions=None,
                              latency_bars=(1,2,3), fill_fractions=(1.0,0.75,0.5),
                              cost_points=(1.0,1.5,2.0)):
    scenarios=[]
    for latency in latency_bars:
        for fill in fill_fractions:
            for cost in cost_points:
                trades=[]
                for i,s in enumerate(signals):
                    if not s or not s.get("direction"): continue
                    j=i+latency
                    if j>=len(close): continue
                    if contracts is not None and contracts[j]!=contracts[i]: continue
                    if sessions is not None and sessions[j]!=sessions[i]: continue
                    raw=s["direction"]*(close[j]-close[i])
                    trades.append(fill*raw-fill*cost)
                scenarios.append({"latency_bars":latency,"fill_fraction":fill,"cost_points":cost,
                                  "trades":len(trades),"avg_net":sum(trades)/len(trades) if trades else None,
                                  "total_net":sum(trades)})
    return scenarios
