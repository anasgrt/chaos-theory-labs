#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

install_apiserver() {
case "$1" in kube-apiserver-original.yaml|kube-apiserver-profiling.yaml) ;; *) return 2 ;; esac
docker cp "$HOME/labs/lab17/$1" lab17-control-plane:/etc/kubernetes/ce-lab17-apiserver.yaml || return
docker exec lab17-control-plane chmod 600 /etc/kubernetes/ce-lab17-apiserver.yaml || return
docker exec lab17-control-plane mv /etc/kubernetes/ce-lab17-apiserver.yaml /etc/kubernetes/manifests/kube-apiserver.yaml
}

wait_profiling() {
local expected=$1 started=$SECONDS flags
for i in $(seq 1 90); do
  if k get --raw /readyz >/dev/null 2>&1 &&
     flags=$(k -n kube-system get pod kube-apiserver-lab17-control-plane -o json) &&
     printf '%s' "$flags" | jq -e --arg expected "$expected" '
       [.spec.containers[0].command[] | select(startswith("--profiling="))] ==
       (if $expected == "false" then ["--profiling=false"] else [] end)' >/dev/null; then
    printf 'Ready API and expected mirror-Pod flag observed after %ss\n' "$((SECONDS-started))"
    return 0
  fi
  sleep 2
done
echo 'STOP: API readiness and expected flag were not both observed.' >&2
return 1
}
