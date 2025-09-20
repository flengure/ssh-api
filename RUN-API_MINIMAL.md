# RUN-API — Minimal Personal Edition (HISTORICAL)

> **⚠️ DEPRECATED**: This document describes an earlier, minimal version of ssh-api.
> For the current production-ready version with security features, MCP support, and comprehensive documentation, see [README.md](README.md).

**Historical Goal (minimal):**
Expose a single HTTP endpoint that accepts a command and runs it on a remote host over SSH using a user-provided `~/.ssh` folder. The runner is a minimal Docker image which mounts your dedicated `.ssh` directory as the runner user's `~/.ssh`, runs the command, prints structured JSON, and exits.

This was intentionally *minimal* for personal use. No database, no JWT, no policy engine. The system trusted the caller.

## Evolution to Current Version

The current ssh-api project has evolved significantly from this minimal concept:

- ✅ **Security**: Added JWT/API key authentication, input validation, and security headers
- ✅ **MCP Support**: Model Context Protocol for AI assistant integration
- ✅ **Production Ready**: Comprehensive error handling, logging, and monitoring
- ✅ **Container Security**: Read-only filesystem, proper isolation
- ✅ **Documentation**: Complete API docs, examples, and deployment guides

For current usage, please refer to the main [README.md](README.md).

---

## Architecture (very small)

```
Client (curl, CI, app)
  → POST /run (JSON: { host, user, port, command })
    → API (Flask) ---- launches ----> docker run --rm -v /path/to/dedicated_ssh:/home/runner/.ssh:ro ghcr.io/you/ssh-runner:latest
                                         (runner mounts .ssh, runs ssh, prints JSON)
    ← API captures runner stdout (JSON) and returns it to client
```

---

## Behaviour

- The user *must* provide a local folder to act as the `.ssh` directory for the runner (e.g. `/home/tg/ssh-bundles/my-ssh`).
- That folder should contain any required private keys, `known_hosts`, and optional `config`.
- The API accepts the command body and forwards it into the runner which runs `ssh user@host "command"` using the mounted `~/.ssh`.
- The runner returns a small JSON blob: `{ "exit_code": int, "stdout": "…", "stderr": "…" }`.
- The runner then exits. No state is stored.

---

## Minimal API (Flask) — quick example

Save as `api_simple.py`:

```python
from flask import Flask, request, jsonify
import subprocess, shlex, uuid, time, os

app = Flask(__name__)
RUNNER_IMAGE = os.environ.get("RUNNER_IMAGE", "ghcr.io/you/ssh-runner:latest")
SSH_BUNDLE_PATH = os.environ.get("SSH_BUNDLE_PATH", "/host/ssh-bundle")  # host path to mount

@app.route("/run", methods=["POST"])
def run():
    j = request.get_json(force=True)
    host = j.get("host")
    user = j.get("user", "root")
    port = int(j.get("port", 22))
    command = j.get("command")
    if not host or not command:
        return jsonify({"error":"host and command required"}), 400

    request_id = str(uuid.uuid4())
    start = time.time()

    docker_cmd = [
      "docker", "run", "--rm",
      "-v", f"{SSH_BUNDLE_PATH}:/home/runner/.ssh:ro",
      "-e", f"SSH_USER={user}",
      "-e", f"SSH_HOST={host}",
      "-e", f"SSH_PORT={port}",
      "-e", f"SSH_CMD={command}",
      RUNNER_IMAGE
    ]

    try:
        out = subprocess.check_output(docker_cmd, stderr=subprocess.STDOUT, timeout=60)
        duration = time.time() - start
        # runner prints JSON to stdout
        return (out, 200, {"Content-Type":"application/json"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error":"runner_failed", "output": e.output.decode(errors="replace")}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error":"timeout"}), 504

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

- Set `SSH_BUNDLE_PATH` to the **host** folder you want to use as `.ssh` (mounted read-only into runner).
- This API simply shells out to `docker run` and returns the runner's stdout (expected to be JSON).

---

## Minimal Runner image (OpenSSH client) — Dockerfile & script

**Dockerfile**

```dockerfile
FROM alpine:3.20
RUN apk add --no-cache openssh-client bash jq
RUN adduser -D -h /home/runner runner
USER runner
WORKDIR /home/runner
COPY run-ssh.sh /usr/local/bin/run-ssh
RUN chmod +x /usr/local/bin/run-ssh
ENTRYPOINT ["/usr/local/bin/run-ssh"]
```

**run-ssh.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${SSH_USER:?need SSH_USER}"
: "${SSH_HOST:?need SSH_HOST}"
SSH_PORT="${SSH_PORT:-22}"
: "${SSH_CMD:?need SSH_CMD}"

# Ensure .ssh perms
if [ -d "/home/runner/.ssh" ]; then
  chmod 700 /home/runner/.ssh || true
  find /home/runner/.ssh -type f -name 'id_*' ! -name '*.pub' -exec chmod 600 {} \; || true
  [ -f /home/runner/.ssh/known_hosts ] && chmod 644 /home/runner/.ssh/known_hosts || true
fi

OPTS=(-p "${SSH_PORT}" -o BatchMode=yes -o UserKnownHostsFile=/home/runner/.ssh/known_hosts -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)

# If mounted ssh config exists, use it
if [ -f /home/runner/.ssh/config ]; then
  OPTS+=(-F /home/runner/.ssh/config)
fi

# Run command and capture
set +e
stdout="$(ssh "${OPTS[@]}" "${SSH_USER}@${SSH_HOST}" -- "${SSH_CMD}" 2> /tmp/errbuf)"
code=$?
set -e

stderr="$(cat /tmp/errbuf || true)"

# Output JSON
jq -n --argjson code "$code" --arg out "$stdout" --arg err "$stderr" '{ exit_code: $code, stdout: $out, stderr: $err }'
```

Notes:
- `StrictHostKeyChecking=accept-new` will add new host keys automatically on first connect (change to `yes` if you prefer known_hosts management).
- The image expects environment variables: `SSH_USER`, `SSH_HOST`, `SSH_PORT`, `SSH_CMD`.

---

## Build & run locally (example)

1. Build the runner image:
```bash
# in runner/ directory with Dockerfile and run-ssh.sh
docker build -t ssh-runner:local .
```

2. Prepare your dedicated ssh folder:
```bash
mkdir -p /home/tg/ssh-bundle
# copy your keys, known_hosts, config into /home/tg/ssh-bundle
chmod 700 /home/tg/ssh-bundle
chmod 600 /home/tg/ssh-bundle/id_*
```

3. Start the API (example):
```bash
export SSH_BUNDLE_PATH=/home/tg/ssh-bundle
export RUNNER_IMAGE=ssh-runner:local
python3 api_simple.py
```

4. Call the API:
```bash
curl -sS -X POST http://localhost:8080/run -H "Content-Type: application/json" \
  -d '{"host":"10.0.0.10","user":"ubuntu","port":22,"command":"uptime"}'
```

You should get a JSON response like:
```json
{ "exit_code": 0, "stdout": " 14:55:01 up 10 days ...", "stderr": "" }
```

---

## Caveats & notes

- This design deliberately trusts the HTTP caller. Anyone with network access can trigger arbitrary SSH commands using the mounted key material. Only use in trusted networks or behind your own reverse proxy/firewall.
- Don't expose this API to the public internet unless you later add authentication/authorization.
- The runner mounts the host's `.ssh` folder read-only, so be careful with permissions and who can read the host folder.
- Timeouts and resource limits are minimal; tune the API/docker timeouts to your needs.

---

## Next steps (if you want to add later)
- Add simple token-based auth (static API key in header).
- Add minimal allowlist for hosts/commands (local config file).
- Replace `accept-new` with strict host key checking and pre-populate `known_hosts`.
- Add logging/audit (append to a local file).

