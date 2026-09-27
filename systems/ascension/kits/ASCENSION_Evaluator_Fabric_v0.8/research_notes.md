# Research notes — Evaluator Fabric v0.8

Exact first-party Deep Research was checked at cycle start but was not exposed/callable: **DEEP RESEARCH ACTUALLY INVOKED = NO**.

Exa research was used across three targeted search workstreams (24 returned results total). The primary authority used for the implementation contract was RFC 9162 from the RFC Editor/IETF.

Key standard properties applied:
- Merkle leaf domain separation: `HASH(0x00 || data)`.
- Internal-node domain separation: `HASH(0x01 || left || right)`.
- Inclusion verification rejects `leaf_index >= tree_size`.
- Proof orientation is derived from `leaf_index` and `tree_size`; it is not caller-supplied metadata.
- Verification fails if the path ends before `sn == 0`, contains nodes after `sn == 0`, or reconstructs a root different from the advertised root.
- RFC example for a seven-leaf tree gives proof lengths of 3 nodes for d0/d3/d4 and 2 nodes for d6; these are covered by focused tests.

A mature implementation/test search was used only as corroboration; it was not treated as normative over the RFC.

Important comparative finding: Evaluator Fabric v0.6 range-checks the declared index but its side-labelled proof fold does not use that index. In the seven-leaf probe, all 42 false in-range relabels were accepted by v0.6. v0.8 rejects all 42 because path geometry/orientation is derived from the declared index and size.
