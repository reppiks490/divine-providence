# Dependencies

Derived from an AST scan of every subsystem's actual imports (not only declared manifests).

| Subsystem | Third-party runtime imports |
|---|---|
| nexus | numpy, pandas (pyarrow optional: `ParquetBarStore` only) |
| daedalus | numpy, pandas, scikit-learn, scipy (+ joblib via its manifest) |
| infrastructure | cryptography |
| janus | cryptography |
| supermesh_x | cryptography, PyYAML |
| ascension | cryptography |
| aion, argus, athena, aegis, oracle, prometheus | standard library only |
| hub (`divine_providence`) | mcp; pytest (the MCP server runs suites) |

Verified versions (Python 3.10.11, Windows 11): numpy 2.2.6, pandas 2.3.3, scipy 1.15.3,
scikit-learn 1.7.2, joblib 1.6.0, cryptography 46.0.7, PyYAML 6.0.3, mcp 2.2.0, pytest 9.1.1.

Cross-subsystem imports happen only in tests and hub drivers, and are always resolved
from `systems/` by path: ORACLE tests → AION/ARGUS/ATHENA/DAEDALUS; NEXUS sibling
validation → the same four; hub drivers → NEXUS, ORACLE, PROMETHEUS, ASCENSION.
No subsystem imports a sibling at runtime.

Declared `requires-python`: PROMETHEUS and some siblings declare `>=3.11` in their own
manifests, but the whole build was validated on 3.10.11. The hub declares `>=3.10`.
