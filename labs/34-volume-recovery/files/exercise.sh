#!/usr/bin/env bash
# Print native storage objects and retain each phase for later comparison.
storage_state() {
  local phase=$1
  [[ $phase =~ ^[a-z0-9-]+$ ]] || return 2
  k get pv ce-lab34-data -o yaml > "$HOME/labs/lab34/$phase-pv.yaml" || return
  k get pvc data --ignore-not-found -o yaml > "$HOME/labs/lab34/$phase-pvc.yaml" || return
  k get pod store --ignore-not-found -o yaml > "$HOME/labs/lab34/$phase-pod.yaml" || return
  k get pv ce-lab34-data
  k get pvc data --ignore-not-found
  k get pod store --ignore-not-found -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,NODE:.spec.nodeName,PHASE:.status.phase'
}
