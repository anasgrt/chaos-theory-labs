#!/usr/bin/env bash
# Destroy the VM and its snapshots without asking for confirmation.
set -euo pipefail
cd "$(dirname "$0")"

vagrant destroy -f default
