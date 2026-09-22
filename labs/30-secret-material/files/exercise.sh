#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

wait_secret() {
local expected=$1 current started=$SECONDS
for i in $(seq 1 30); do
  if current=$(k exec file-consumer -- cat /etc/app-credentials/password) && [ "$current" = "$expected" ]; then
    printf 'Mounted value=%s observed after %ss\n' "$current" "$((SECONDS-started))"
    return 0
  fi
  sleep 5
done
echo 'STOP: expected mounted value not observed in 30 checks.' >&2
return 1
}
