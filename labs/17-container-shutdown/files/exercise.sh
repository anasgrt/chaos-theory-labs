#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

start_worker() {
local container=$1
docker cp "$HOME/labs/lab17/worker.py" "$container:/worker.py" || return
docker start "$container" || return
for i in $(seq 1 30); do
  if docker logs "$container" 2>&1 | grep -q '^ready '; then
    docker logs "$container"; return
  fi
  sleep 0.2
done
echo 'STOP: worker did not become ready.' >&2
return 1
}
