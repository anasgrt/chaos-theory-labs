#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

retry_case() {
(
  set -euo pipefail
  cd "$HOME/labs/lab15"
  case "$1" in 0) file=no-client-retry.txt ;; 1) file=one-client-retry.txt ;; *) return 2 ;; esac
  sudo systemd-run --unit=ce-lab15 --collect --wait --pipe --uid="$(id -u)" \
    --property=RuntimeMaxSec=60s --working-directory="$PWD" /bin/bash "$PWD/run-case.sh" "$1" | tee "$file"
)
}
