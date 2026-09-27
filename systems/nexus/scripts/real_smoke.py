from pathlib import Path
import json, numpy as np, pandas as pd
from nexus.csvio import load_ohlcv
from nexus.align import CausalAligner
from nexus.ensemble import AdaptiveFactorEnsemble, EnsembleDefinition
from nexus.topology import RollingTopology
from nexus.novelty import TrailingNovelty
from nexus.ablation import SensorAblationEngine
from nexus.synthetic import SyntheticTickerDefinition

import os, sys
# CSV corpus root: first CLI argument, else NEXUS_CSV_ROOT (the corpus is not shipped in this repo).
_root=sys.argv[1] if len(sys.argv)>1 else os.environ.get('NEXUS_CSV_ROOT')
if not _root or not Path(_root).is_dir():
    raise SystemExit('usage: real_smoke.py <csv-root>  (or set NEXUS_CSV_ROOT); expected TradingView exports such as "CME_MINI_DL_NQ1!, 60.csv"')
root=Path(_root)
files={
 'NQ':root/'CME_MINI_DL_NQ1!, 60.csv',
 'ES':root/'CME_MINI_DL_ES1!, 60.csv',
 'VIX':root/'TVC_VIX, 60.csv',
 'DXY':root/'TVC_DXY, 60.csv',
 'VXN':root/'CBOE_DLY_VXN, 60.csv',
}
frames={k:load_ohlcv(v) for k,v in files.items()}
# Anchor to NQ; require context no older than four hours of event time.
aligned=CausalAligner(max_age_ns=4*3600*1_000_000_000).align(frames['NQ'],{k:v for k,v in frames.items() if k!='NQ'})
values=aligned.set_index('event_ns')[['driver','ES','VIX','DXY','VXN']].rename(columns={'driver':'NQ'}).dropna()
# Keep last 4000 synchronized states for smoke performance while preserving causal mechanics.
values=values.tail(4000)
defn=EnsembleDefinition('NEXUS:MARKET_STATE',tuple(values.columns),window=120,min_periods=50,rebalance_every=10)
factor=AdaptiveFactorEnsemble().build(values,defn)
returns=np.log(values).diff()
topo=RollingTopology(window=240,min_periods=80,edge_floor=.2).snapshot(returns)
nov_input=pd.DataFrame({'factor':factor['value'],'disagreement':factor['method_disagreement'],'confidence':factor['confidence']}).dropna()
nov=TrailingNovelty(window=250,min_periods=80).score(nov_input)
abl=SensorAblationEngine().evaluate(values,SyntheticTickerDefinition('NEXUS:MARKET_STATE',tuple(values.columns),method='equal',window=120,min_periods=50,rebalance_every=10))
report={
 'files':{k:str(v.name) for k,v in files.items()},
 'source_rows':{k:len(v) for k,v in frames.items()},
 'synchronized_rows':len(values),
 'factor_rows':len(factor),
 'factor_last':None if factor.empty else float(factor['value'].iloc[-1]),
 'factor_confidence_last':None if factor.empty else float(factor['confidence'].iloc[-1]),
 'method_disagreement_last':None if factor.empty else float(factor['method_disagreement'].iloc[-1]),
 'novelty_last':None if nov.dropna().empty else float(nov.dropna().iloc[-1]),
 'topology_entropy':topo.entropy,
 'centrality':topo.centrality,
 'strongest_edges':[list(x) for x in topo.strongest_edges[:10]],
 'ablation':[a.__dict__ for a in abl],
 'note':'Research/data-fabric smoke only. No predictive or trading claim.',
}
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/real_smoke.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
