#!/usr/bin/env bash

cg() {
  local pid relative_path
  pid=$(docker inspect -f '{{.State.Pid}}' "$1") || return
  [ "$pid" -gt 1 ] || { echo 'Container must be running' >&2; return 1; }
  relative_path=$(sudo awk -F: '$1 == "0" {print $3}' "/proc/$pid/cgroup") || return
  printf '/sys/fs/cgroup%s\n' "$relative_path"
}

measure() {
  local url=$1 count=${2:-10}
  for ((i = 1; i <= count; i++)); do
    curl --noproxy '*' -sS --connect-timeout 2 --max-time 10 -o /dev/null \
      -w '%{http_code} %{time_total}\n' "$url"
  done
}

k() {
  kubectl --kubeconfig="$HOME/labs/chaos.kubeconfig" \
    --context=kind-chaos --namespace=chaos-labs --request-timeout=10s "$@"
}
