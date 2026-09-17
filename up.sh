#!/usr/bin/env bash
# Create the VM, then configure it.
set -euo pipefail
cd "$(dirname "$0")"

vagrant up --provider=virtualbox
./ansible/run.sh
