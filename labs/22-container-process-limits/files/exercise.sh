#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

start_process_container() {
local container=$1
for file in reaper.py orphan-maker.py fork-burst.py procreport.py; do
  docker cp "$HOME/labs/lab22/$file" "$container:/$file" || return
done
docker start "$container" || return
for i in $(seq 1 30); do
  if docker logs "$container" 2>&1 | grep -q 'reaping='; then
    docker logs "$container"; return
  fi
  sleep 0.2
done
echo 'STOP: process container did not become ready.' >&2
return 1
}
