from __future__ import annotations
import hashlib
from .contracts import FinancialState,Hypothesis

def from_anomaly(state:FinancialState, *, family:str, target:str, horizon:str, anomaly_name:str, anomaly_value:float, threshold:float, created_ns:int)->Hypothesis:
    direction="above" if anomaly_value>=threshold else "below"
    statement=f"When {anomaly_name} is {direction} {threshold:g} in state {state.state_id}, {target} exhibits a repeatable conditional response over {horizon}."
    spec=f"{state.state_id}|{family}|{target}|{horizon}|{anomaly_name}|{threshold}|{created_ns}"
    hid="HYP-"+hashlib.sha256(spec.encode()).hexdigest()[:16]
    fals=("No out-of-sample improvement over unconditional baseline", "Effect fails temporal/regime stress tests", "Effect disappears after realistic latency/cost perturbation", "Effect is dominated by one source/representation")
    return Hypothesis(hid,family,statement,target,horizon,fals,created_ns,state.state_id,tags=("auto_generated",anomaly_name))
