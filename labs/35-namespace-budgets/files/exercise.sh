#!/usr/bin/env bash
# Wait for observed quota accounting, never assume it is synchronous.
wait_budget() {
  local hard=$1 used=$2 state i
  case "$hard:$used" in 200m:0|200m:100m|200m:200m|100m:200m) ;; *) return 2 ;; esac
  for i in {1..60}; do
    state=$(k get resourcequota budget -o json) || return
    if printf '%s' "$state" | jq -e --arg hard "$hard" --arg used "$used" \
      '.status.hard["requests.cpu"] == $hard and .status.used["requests.cpu"] == $used' >/dev/null; then
      k describe resourcequota budget
      return
    fi
    sleep 2
  done
  echo 'STOP: the requested quota accounting was not observed.' >&2
  return 1
}
