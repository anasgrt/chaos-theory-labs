#!/usr/bin/env bash
# Repeated observations only; fault commands remain on the card.
probe_state() {
  local phase=$1 snapshot
  [[ $phase =~ ^[a-z0-9-]+$ ]] || return 2
  snapshot="$HOME/labs/lab23/$phase.json"
  k get pod probe-web -o json > "$snapshot" || return
  jq '{uid:.metadata.uid, node:.spec.nodeName,
       ready:[.status.conditions[]? | select(.type=="Ready") | .status],
       containers:[.status.containerStatuses[]? | {containerID,restartCount,state,lastState}]}' "$snapshot"
  k get endpointslices -l kubernetes.io/service-name=probe-web -o yaml
}

wait_restarts() {
  local minimum=$1 count i
  [[ $minimum =~ ^[1-9][0-9]*$ ]] || return 2
  for i in {1..90}; do
    count=$(k get pod probe-web -o jsonpath='{.status.containerStatuses[0].restartCount}') || return
    if [[ $count =~ ^[0-9]+$ ]] && ((count >= minimum)); then
      printf 'Observed restartCount=%s\n' "$count"
      return 0
    fi
    sleep 2
  done
  echo 'STOP: the requested restart was not observed.' >&2
  return 1
}

probe_http() {
  k exec client -- python3 /scripts/request.py
}

wait_service() {
  local i
  for i in {1..15}; do
    if probe_http; then return 0; fi
    sleep 2
  done
  echo 'STOP: no successful Service request in 15 attempts.' >&2
  return 1
}
