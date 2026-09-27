from __future__ import annotations
from dataclasses import fields,is_dataclass
from enum import Enum
from .contracts import digest
def contract_fingerprint(items):
    sig={}
    for name,cls in sorted(items.items()):
        if is_dataclass(cls): sig[name]={"module":cls.__module__,"name":cls.__qualname__,"fields":[(f.name,str(f.type),repr(f.default)) for f in fields(cls)]}
        elif issubclass(cls,Enum): sig[name]={"module":cls.__module__,"name":cls.__qualname__,"members":[(m.name,m.value) for m in cls]}
        else: sig[name]={"module":cls.__module__,"name":cls.__qualname__}
    return digest(sig)
