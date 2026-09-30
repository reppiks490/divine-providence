from __future__ import annotations
import hashlib, json, sqlite3
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

def _canonical(obj: Any) -> bytes:
    if is_dataclass(obj): obj=asdict(obj)
    return json.dumps(
        obj,sort_keys=True,separators=(",",":"),default=str,allow_nan=False
    ).encode()

class MarketFabricLedger:
    """Append-only hash-chained journal for NEXUS market-fabric products.

    This is not AION evidence memory. It provides reproducible low-level frame/event hashes
    that AION may cite. Updates/deletes are intentionally not exposed.
    """
    def __init__(self, path: str | Path):
        self.path=str(path)
        self.db=sqlite3.connect(self.path)
        self.db.execute('''CREATE TABLE IF NOT EXISTS journal(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            visible_ns INTEGER NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            entry_hash TEXT NOT NULL UNIQUE
        )''')
        self.db.commit()

    def append(self, visible_ns:int, kind:str, payload:Any) -> str:
        if type(visible_ns) is not int or visible_ns < 0:
            raise ValueError("visible_ns must be a non-negative integer")
        if not isinstance(kind,str) or not kind.strip():
            raise ValueError("kind must be a non-empty string")
        kind=kind.strip()
        raw=_canonical(payload); payload_json=raw.decode()
        row=self.db.execute("SELECT entry_hash FROM journal ORDER BY seq DESC LIMIT 1").fetchone()
        prev=row[0] if row else "0"*64
        h=hashlib.sha256(prev.encode()+b"|"+str(int(visible_ns)).encode()+b"|"+kind.encode()+b"|"+raw).hexdigest()
        self.db.execute("INSERT INTO journal(visible_ns,kind,payload_json,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(int(visible_ns),kind,payload_json,prev,h))
        self.db.commit(); return h

    def verify(self) -> bool:
        prev="0"*64
        for visible_ns,kind,payload_json,stored_prev,entry_hash in self.db.execute("SELECT visible_ns,kind,payload_json,prev_hash,entry_hash FROM journal ORDER BY seq"):
            if stored_prev != prev: return False
            raw=payload_json.encode()
            expected=hashlib.sha256(prev.encode()+b"|"+str(int(visible_ns)).encode()+b"|"+kind.encode()+b"|"+raw).hexdigest()
            if expected != entry_hash: return False
            prev=entry_hash
        return True

    def tail(self, n:int=20):
        if type(n) is not int or n < 0:
            raise ValueError("n must be a non-negative integer")
        rows=self.db.execute("SELECT seq,visible_ns,kind,payload_json,entry_hash FROM journal ORDER BY seq DESC LIMIT ?",(n,)).fetchall()
        return list(reversed(rows))

    def head_hash(self)->str:
        row=self.db.execute("SELECT entry_hash FROM journal ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else "0"*64

    def count(self)->int:
        return int(self.db.execute("SELECT COUNT(*) FROM journal").fetchone()[0])

    def close(self): self.db.close()
