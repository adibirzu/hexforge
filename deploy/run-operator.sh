#!/usr/bin/env bash
# Start HexForge v6.5 on the operator host (adi1).
#
# Never writes, retargets, or kills /home/adi/GitHub/hexstrike-ai (live QLoRA clone).
# Never kills an existing listener. If :8888 is already bound, this process binds
# HEXSTRIKE_PORT (default 8889) and leaves the legacy listener running.
#
# Usage (from the hexforge repo root):
#   deploy/run-operator.sh
#   HEXSTRIKE_PORT=8889 deploy/run-operator.sh
#
# Environment:
#   HEXSTRIKE_PORT   bind port (auto 8889 when 8888 is occupied and unset)
#   HEXSTRIKE_HOST   flask bind host (default: 127.0.0.1)
#   HEXSTRIKE_VENV   virtualenv directory (default: ./hexstrike-env)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$ROOT" == /home/adi/GitHub/hexstrike-ai || "$ROOT" == /home/adi/GitHub/hexstrike-ai/* ]]; then
  printf 'run-operator: refusing to run from the live hexstrike-ai training clone\n' >&2
  exit 2
fi

VENV="${HEXSTRIKE_VENV:-$ROOT/hexstrike-env}"

port_in_use() {
  local p="$1"
  ss -H -tln 2>/dev/null | grep -Eq ":${p}[[:space:]]" && return 0
  return 1
}

if [ -z "${HEXSTRIKE_PORT:-}" ]; then
  if port_in_use 8888; then
    HEXSTRIKE_PORT=8889
    printf 'run-operator: :8888 is occupied; binding HEXSTRIKE_PORT=%s (legacy listener left running)\n' "$HEXSTRIKE_PORT"
  else
    HEXSTRIKE_PORT=8888
  fi
fi

if port_in_use "$HEXSTRIKE_PORT"; then
  printf 'run-operator: port %s is already in use; not replacing it. Probe /health/identity.\n' "$HEXSTRIKE_PORT" >&2
  exit 3
fi

if [ ! -x "$VENV/bin/python" ]; then
  printf 'run-operator: creating venv at %s\n' "$VENV"
  python3 -m venv "$VENV"
fi

# GPU stays with the live QLoRA job unless the operator explicitly overrides.
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES-}"
export HEXSTRIKE_PORT

mkdir -p "$ROOT/data"
PIDFILE="$ROOT/data/hexstrike-operator.pid"
LOGFILE="$ROOT/hexstrike.log"

if [ -f "$PIDFILE" ]; then
  oldpid="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "${oldpid:-}" ] && kill -0 "$oldpid" 2>/dev/null; then
    printf 'run-operator: already running as pid %s (pidfile %s)\n' "$oldpid" "$PIDFILE" >&2
    exit 4
  fi
  rm -f "$PIDFILE"
fi

nohup "$VENV/bin/python" -u "$ROOT/hexstrike_server.py" --port "$HEXSTRIKE_PORT" \
  >>"$LOGFILE" 2>&1 &
echo $! >"$PIDFILE"

printf 'run-operator: started pid %s on :%s (log %s)\n' "$(cat "$PIDFILE")" "$HEXSTRIKE_PORT" "$LOGFILE"
printf 'run-operator: identity probe: curl -sS http://127.0.0.1:%s/health/identity\n' "$HEXSTRIKE_PORT"
printf 'run-operator: full health:     curl -sS http://127.0.0.1:%s/health\n' "$HEXSTRIKE_PORT"
