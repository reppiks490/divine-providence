# Run 031 Lineage Reconciliation

The sealed Run 031 ZIP SHA-256 is `b80770a71af3ea1f06e6443111484efd2a9467e9dc1a5e2d299086e97524c6c4`, matching the recorded checkpoint. The sealed `tests/test_janus.py` SHA-256 is `a75bb0717e5c4f6601986d83258c6fe6b3678cea52a4d77962d7111a6bed05f3`, also matching the recorded checkpoint.

A fresh `PYTHONPATH=src pytest -q` over those exact sealed bytes collected and passed **116 tests**, while `STATE_CAPSULE_RUN_031.md` states **115/115 PASS**. Because both artifact and test-file hashes match the sealed lineage, Run 032 classifies this as stale checkpoint metadata rather than code drift. The original capsule is preserved unchanged; this reconciliation note carries the correction forward.
