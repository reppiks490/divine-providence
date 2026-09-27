# CONTINUATION / EXECUTION INSTRUCTIONS

Create/use sibling repo `helios-prime`; isolated worktree/branch; never implement on main/master; never auto-merge/deploy.

Order: H1 Tasks 1-12 -> H2 -> H3 -> H4 -> H5 -> H6.

For every task: write focused failing test; run and observe RED; implement minimum; run focused GREEN; run full regression; refactor while green; commit; record SHA and exact output in `.superpowers/sdd/<plan>/progress.md`.

Non-negotiable: no broker/orders, no execution credentials, no ICARUS webhook/admin writes, no source self-certification, no invented knowledge timestamps, no correlated-evidence inflation, no blind retry of uncertain external effects, no silent integrity repair.

Final standard verification:
pytest -q
pytest -W error::ResourceWarning -q
python -m compileall -q src tests
PRAGMA quick_check;

AST/static review for: icarus_bridge, ExecutionEngine, Broker, submit_order, submit_market, submit_stop, submit_bracket, place_order, close_position, /webhook, /admin/, webhook_secret, admin_token, broker private credentials, execution_authorized=True.
