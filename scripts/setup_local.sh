#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BOOTSTRAP=(python3)
elif command -v python >/dev/null 2>&1; then
  PYTHON_BOOTSTRAP=(python)
elif command -v py >/dev/null 2>&1; then
  PYTHON_BOOTSTRAP=(py -3)
else
  echo "[setup] Python 3.12+ is required but no launcher was found."
  exit 1
fi

if [[ ! -f "config.json" ]]; then
  cp config.example.json config.json
  echo "[setup] Created config.json from config.example.json"
fi

resolve_venv_python() {
  if [[ -x "${ROOT_DIR}/venv/bin/python" ]]; then
    echo "${ROOT_DIR}/venv/bin/python"
  elif [[ -x "${ROOT_DIR}/venv/Scripts/python.exe" ]]; then
    echo "${ROOT_DIR}/venv/Scripts/python.exe"
  fi
}

PYTHON_BIN="$(resolve_venv_python)"
if [[ -z "$PYTHON_BIN" ]]; then
  "${PYTHON_BOOTSTRAP[@]}" -m venv venv
  echo "[setup] Created virtual environment at venv/"
  PYTHON_BIN="$(resolve_venv_python)"
fi

"$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 || true
"$PYTHON_BIN" -m pip install --disable-pip-version-check -r requirements.txt

echo "[setup] Running local preflight..."
"$PYTHON_BIN" scripts/preflight_local.py || true

echo ""
echo "[setup] Done."
if [[ "$PYTHON_BIN" == *"/Scripts/python.exe" ]]; then
  echo "[setup] Start app with: ./venv/Scripts/python.exe src/main.py"
else
  echo "[setup] Start app with: source venv/bin/activate && python src/main.py"
fi
