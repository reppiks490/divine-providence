# Receiver Checklist

Before modifying JANUS or integrating it into Icarus:

- [ ] Read README.md.
- [ ] Read MASTER_HANDOFF.md.
- [ ] Read specs/JANUS_ARCHITECTURE.md.
- [ ] Read docs/ICARUS_CONTEXT_SEED.md.
- [ ] Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
- [ ] Seed a local twin from `examples/icarus_seed_manifest.json`.
- [ ] Confirm the historical 80 -> 117 NEXUS test evolution is not misclassified as a contradiction.
- [ ] Confirm a same-valid-time conflicting fact is detected.
- [ ] Confirm state digest is stable across repeated reads.
- [ ] If a live repo is available, snapshot before mutation.
- [ ] Reconcile the live repo against the latest available handoff/capsule.
- [ ] Do not claim live integration if only the offline capsule was tested.
- [ ] Preserve subsystem authority boundaries.
- [ ] Leave a new proof-carrying handoff at the end.
