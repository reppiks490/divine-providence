#!/usr/bin/env python3
"""Build an observed cross-asset shock propagation summary."""


def build_shock_graph(reactions):
    if not reactions:
        return {'breadth':0,'peak_asset':None,'ordered_assets':[],'propagation_score':0.0,'nodes':[]}
    nodes=[]
    for asset,row in reactions.items():
        z=float(row.get('return_z',0.0))
        lag=max(0.0,float(row.get('lag_seconds',0.0)))
        nodes.append({'asset':asset,'return_z':z,'abs_z':abs(z),'lag_seconds':lag,'channel':row.get('channel','unknown')})
    peak=max(nodes,key=lambda n:n['abs_z'])['asset']
    ordered=[n['asset'] for n in sorted(nodes,key=lambda n:(n['lag_seconds'],-n['abs_z'],n['asset']))]
    breadth=sum(1 for n in nodes if n['abs_z']>0)
    avg_mag=sum(n['abs_z'] for n in nodes)/len(nodes)
    lag_penalty=sum(min(n['lag_seconds'],600.0)/600.0 for n in nodes)/len(nodes)
    channel_diversity=len({n['channel'] for n in nodes})/max(1,len(nodes))
    propagation=max(0.0,min(1.0,(avg_mag/3.0)*0.6+channel_diversity*0.3+(1.0-lag_penalty)*0.1))
    return {'breadth':breadth,'peak_asset':peak,'ordered_assets':ordered,'propagation_score':round(propagation,6),'nodes':nodes}
