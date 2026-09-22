#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

inspect_host_processes() {
k exec privileged -- python -u -c 'from pathlib import Path
pids = [int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()]
names = {Path(f"/proc/{pid}/comm").read_text().strip() for pid in pids if Path(f"/proc/{pid}/comm").exists()}
print("visible_pids", len(pids))
print("pid1", Path("/proc/1/cmdline").read_bytes().decode().replace(chr(0), " ").strip()[:60])
print("node_processes", sorted(n for n in names if n in {"kubelet", "containerd", "containerd-shim", "systemd"}))'
}

inspect_hardening() {
k exec hardened -- python -u -c 'import os
from pathlib import Path
status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
print("uid", os.getuid(), "capeff", status["CapEff"].strip(), "nonewprivs", status["NoNewPrivs"].strip(), "seccomp", status["Seccomp"].strip())'
}
