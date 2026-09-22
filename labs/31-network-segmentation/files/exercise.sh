#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

wait_network_recovery() {
local result
for i in $(seq 1 15); do
  if result=$(probe client http server) && [[ "$result" == *'ok status=200'* ]]; then
    printf '%s\n' "$result"; return 0
  fi
  sleep 2
done
echo 'STOP: client HTTP did not recover after policy removal.' >&2
return 1
}
