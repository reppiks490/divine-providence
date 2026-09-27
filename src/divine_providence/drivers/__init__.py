"""Cross-system connection drivers.

Each driver runs as ``python -m divine_providence.drivers.<name>`` in its own
process (see ``divine_providence.runner.run_json_driver``) with only the import
roots of the systems it connects, and prints one JSON object on its last line.
Drivers only read or validate sibling-owned contracts; none grants authority.
"""
