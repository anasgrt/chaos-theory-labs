#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

run_fault() {
(
  set -euo pipefail
  cd "$HOME/labs/lab01"
  sudo systemd-run --unit=ce-lab01-runner --collect --wait --pipe \
    --uid="$(id -u)" --property=RuntimeMaxSec=20s --working-directory="$PWD" \
    /bin/bash "$PWD/run.sh" "$1"
)
}

check_firewall() {
local rules
rules=$(sudo iptables -S OUTPUT) || { echo 'UNKNOWN: cannot read firewall rules.'; return 1; }
if printf '%s\n' "$rules" | grep -q -- '--comment ce-lab01'; then
  echo 'Lab 01 fault rule still present'; return 1
fi
echo 'No Lab 01 firewall rule remains'
}
