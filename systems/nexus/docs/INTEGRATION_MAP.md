# NEXUS Integration Map

```text
CSV archives / future feeds
        |
        v
+-----------------------------+
| NEXUS Adaptive Market Fabric|
| identity | clock | replay   |
| factors  | topology | drift |
+-----------------------------+
   |         |         |        \
   v         v         v         v
 AION      ARGUS    DAEDALUS   ATHENA
 memory    micro-    proof/     state/
 replay    structure validation supervisor
   \         |          |         /
    +--------+----------+--------+
                 |
                 v
              ICARUS
        controlled execution only
```

Boundary rules:
- NEXUS does not overwrite sibling source trees.
- AION remains authoritative for durable evidence memory/atlas.
- ARGUS remains authoritative for true depth/trade/order-flow semantics and execution physics.
- DAEDALUS remains authoritative for scientific validation and promotion.
- ATHENA remains authoritative for uncertainty-aware world state, expert routing, advisory risk and abstention.
- Icarus remains authoritative for production decisions, broker state and orders.
