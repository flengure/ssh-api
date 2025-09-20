#!/usr/bin/env bash
set -euo pipefail

: "${SSH_USER:?need SSH_USER}"
: "${SSH_HOST:?need SSH_HOST}"
SSH_PORT="${SSH_PORT:-22}"
: "${SSH_CMD:?need SSH_CMD}"

# fix perms
if [ -d "/home/runner/.ssh" ]; then
  chmod 700 /home/runner/.ssh || true
  find /home/runner/.ssh -type f -name 'id_*' ! -name '*.pub' -exec chmod 600 {} \; || true
  [ -f /home/runner/.ssh/known_hosts ] && chmod 644 /home/runner/.ssh/known_hosts || true
fi

OPTS=(-p "${SSH_PORT}" -o BatchMode=yes -o ConnectTimeout=10)

[ -f /home/runner/.ssh/config ] && OPTS+=(-F /home/runner/.ssh/config)

set +e
stdout="$(ssh "${OPTS[@]}" "${SSH_USER}@${SSH_HOST}" -- "${SSH_CMD}" 2> /tmp/errbuf)"
code=$?
set -e

stderr="$(cat /tmp/errbuf || true)"

jq -n --argjson code "$code" --arg out "$stdout" --arg err "$stderr" \
  '{ exit_code: $code, stdout: $out, stderr: $err }'
