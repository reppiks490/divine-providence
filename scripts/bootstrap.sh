#!/usr/bin/env sh
# Divine Providence bootstrap (Linux/macOS; also Git Bash on Windows).
#   scripts/bootstrap.sh [--validate] [--register-mcp]
set -eu
VALIDATE=0; REGISTER=0
for arg in "$@"; do
  case "$arg" in
    --validate) VALIDATE=1 ;;
    --register-mcp) REGISTER=1 ;;
    *) echo "unknown option: $arg (expected --validate and/or --register-mcp)" >&2; exit 2 ;;
  esac
done
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
[ -d .venv ] || "$PYTHON" -m venv .venv
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; else PY="$ROOT/.venv/Scripts/python.exe"; fi
export PYTHONIOENCODING=utf-8
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -e .
"$PY" -m pytest tests
[ "$VALIDATE" -eq 1 ] && "$PY" -m divine_providence.validate
if [ "$REGISTER" -eq 1 ]; then
  claude mcp remove icarus-engine --scope user >/dev/null 2>&1 || true
  # 'claude mcp add -e' stores the token in the user-scope Claude config, never in this repository.
  if [ -n "${ICARUS_ENGINE_TOKEN:-}" ]; then
    claude mcp add icarus-engine --scope user -e PYTHONIOENCODING=utf-8 -e ICARUS_ENGINE_TOKEN="$ICARUS_ENGINE_TOKEN" -- "$PY" -m divine_providence.mcp_server
  else
    claude mcp add icarus-engine --scope user -e PYTHONIOENCODING=utf-8 -- "$PY" -m divine_providence.mcp_server
  fi
  # 'claude mcp list' health-checks without printing the server's environment (unlike 'mcp get').
  claude mcp list | grep icarus-engine
fi
echo done.
