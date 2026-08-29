#!/usr/bin/env bash
# Drive a deploy script on the KaliVM through the operator's jump chain.
# All connection details are variables - nothing about hosts or keys is hardcoded
# beyond these documented defaults, which mirror the fleet's standing setup.
#
# Usage:
#   deploy/remote-run.sh <script-to-run-on-kali> [args...]
# Environment overrides:
#   KALI_USER=adi            user on the KaliVM
#   KALI_HOST=kali.cyber-sec.ro   address of the VM as seen from the jump host
#   KALI_JUMP_HOST=adi@adi1  "user@jumphost" (empty string = direct connection)
#   KALI_SSH_KEY=~/.ssh/kali_pentest_ed25519

set -euo pipefail

KALI_USER="${KALI_USER:-adi}"
KALI_HOST="${KALI_HOST:-kali.cyber-sec.ro}"
KALI_JUMP_HOST="${KALI_JUMP_HOST:-adi@adi1}"
KALI_SSH_KEY="${KALI_SSH_KEY:-$HOME/.ssh/kali_pentest_ed25519}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$KALI_SSH_KEY" ]; then
  printf 'remote-run: missing SSH key %s (KaliVM credential). See deploy/FLEET.md.\n' "$KALI_SSH_KEY" >&2
  exit 3
fi

if [ "$#" -lt 1 ]; then
  printf 'remote-run: usage: deploy/remote-run.sh <bootstrap|inventory|path-to-script> [args...]\n' >&2
  exit 2
fi

script="$1"; shift

case "$script" in
  bootstrap) script="$ROOT/deploy/bootstrap-kali.sh" ;;
  inventory) script="$ROOT/deploy/kali-inventory.sh" ;;
esac

if [ ! -f "$script" ]; then
  printf 'remote-run: script not found: %s\n' "$script" >&2
  exit 2
fi

jump_args=()
if [ -n "$KALI_JUMP_HOST" ]; then
  jump_args=(-J "$KALI_JUMP_HOST")
fi

dest="${KALI_USER}@${KALI_HOST}"

# Copy script to a private temp path on the target, execute, clean up.
remote_tmp="$(ssh "${jump_args[@]}" -i "$KALI_SSH_KEY" "$dest" 'mktemp')"
scp -q "${jump_args[@]}" -i "$KALI_SSH_KEY" "$script" "$dest:$remote_tmp"
ssh "${jump_args[@]}" -t -i "$KALI_SSH_KEY" "$dest" \
  "chmod +x '$remote_tmp' && '$remote_tmp' $*; rc=\$?; rm -f '$remote_tmp'; exit \$rc"
