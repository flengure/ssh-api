import subprocess, time, os

EPHEMERAL_DEFAULTS = [
    "-o", "BatchMode=yes",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "StrictHostKeyChecking=no",
    "-o", "CheckHostIP=no",
    "-o", "LogLevel=ERROR",
]

def exec_ssh(host, command, *, user=None, port=None, ssh_dir=None,
             strict_host_key_checking=None, proxy_jump=None,
             allocate_tty=False, extra_opts=None, timeout=60):
    """
    Non-interactive SSH exec with ephemeral & quiet defaults.
    Returns dict: {exit_code, stdout, stderr, duration_seconds}
    """
    opts = list(EPHEMERAL_DEFAULTS)

    if port:
        opts += ["-p", str(port)]

    if ssh_dir:
        ssh_dir = os.path.expanduser(ssh_dir)
        if os.path.isdir(ssh_dir):
            cfg = os.path.join(ssh_dir, "config")
            if os.path.exists(cfg):
                opts += ["-F", cfg]

    if strict_host_key_checking:
        opts += ["-o", f"StrictHostKeyChecking={strict_host_key_checking}"]
    if proxy_jump:
        opts += ["-J", proxy_jump]
    if allocate_tty:
        opts += ["-t"]
    if extra_opts:
        opts += [str(x) for x in extra_opts]

    target = f"{user}@{host}" if user else host

    start = time.time()
    proc = subprocess.Popen(
        ["ssh"] + opts + [target, "--", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=int(timeout))
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"exit_code": 124, "stdout": "", "stderr": "timeout",
                "duration_seconds": round(time.time()-start, 3)}

    return {
        "exit_code": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "duration_seconds": round(time.time() - start, 3),
    }
