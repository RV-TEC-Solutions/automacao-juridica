#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8007}"
FRONTEND_PORT="${FRONTEND_PORT:-3002}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Ambiente Python ausente. Execute os passos de instalação do README.md."
  exit 1
fi
if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Dependências do frontend ausentes. Execute npm install em frontend/."
  exit 1
fi

if [[ "${1:-}" == "setup" ]]; then
  "$PYTHON_BIN" "$ROOT_DIR/backend-automacao/manage.py" migrate
  "$PYTHON_BIN" "$ROOT_DIR/backend-automacao/manage.py" configurar_app
  exit 0
fi

"$PYTHON_BIN" "$ROOT_DIR/backend-automacao/manage.py" migrate --noinput
PIDS=()
cleanup() {
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"$PYTHON_BIN" "$ROOT_DIR/backend-automacao/manage.py" runserver "$BACKEND_HOST:$BACKEND_PORT" & PIDS+=("$!")
"$PYTHON_BIN" "$ROOT_DIR/backend-automacao/manage.py" processar_coletas & PIDS+=("$!")
npm --prefix "$ROOT_DIR/frontend" run dev -- --port "$FRONTEND_PORT" & PIDS+=("$!")

echo "Painel de Expedientes disponível em http://localhost:$FRONTEND_PORT (API em http://$BACKEND_HOST:$BACKEND_PORT)"
wait -n "${PIDS[@]}"
