from __future__ import annotations
from typing import Any

class ExecutionAuthorityError(PermissionError): pass

_FORBIDDEN_KEYS={"broker","broker_id","account_id","order_id","order_type","quantity","qty","position_size","limit_price","stop_price","send_order","place_order","cancel_order","execution_authorized","production_authorized"}
_FORBIDDEN_ACTIONS={"BUY","SELL","SHORT","COVER","PLACE_ORDER","CANCEL_ORDER","MODIFY_ORDER"}

def assert_no_execution_authority(payload: Any, *, path: str="root") -> None:
    if isinstance(payload,dict):
        for k,v in payload.items():
            lk=str(k).lower()
            if lk in _FORBIDDEN_KEYS:
                if lk=="production_authorized" and v is False: pass
                else: raise ExecutionAuthorityError(f"forbidden execution field at {path}.{k}")
            if lk in {"action","command"} and str(v).upper() in _FORBIDDEN_ACTIONS:
                raise ExecutionAuthorityError(f"forbidden execution command at {path}.{k}")
            assert_no_execution_authority(v,path=f"{path}.{k}")
    elif isinstance(payload,(list,tuple)):
        for i,v in enumerate(payload): assert_no_execution_authority(v,path=f"{path}[{i}]")

def research_envelope(payload: dict[str,Any], *, schema: str, purpose: str)->dict[str,Any]:
    assert_no_execution_authority(payload)
    return {"schema":schema,"purpose":purpose,"production_authorized":False,"payload":payload}
