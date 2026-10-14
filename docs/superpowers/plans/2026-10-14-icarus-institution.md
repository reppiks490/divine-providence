# Implementation plan

1. Add bounded corpus/feed ingestion, provenance, and a fixed context identity.
2. Add isolated DAEDALUS/ORACLE driver with development-only tournament,
   falsification diagnostics, and typed hypotheses.
3. Add durable memory, a graph projection, briefs, JSON APIs, and an HTML viewer.
4. Add a trusted-main data publisher and read/write-separated daily workflow.
5. Test holdout separation, memory reuse/retry, timestamps, publisher integrity,
   and run real owned data. Run root regression tests and actionlint.
6. Merge, verify the first main research run, and deploy the existing private
   dashboard with automatic research/Observatory views.
