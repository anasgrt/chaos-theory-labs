#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

sample_node() {
: > ~/labs/lab06/samples.tsv
for i in $(seq 1 18); do
  timestamp=$(date +%s)
  node_json=$(k get node "$NODE" -o json) &&
  pods_json=$(k get pods -l app=node-web -o json) &&
  lease=$(kubectl --kubeconfig="$HOME/labs/lab06/kubeconfig" --context=kind-lab06 -n kube-node-lease --request-timeout=5s get lease "$NODE" -o jsonpath='{.spec.renewTime}') || {
    echo "sample $i: API observation failed; no state inferred"
    sleep 10
    continue
  }
  ready=$(printf '%s' "$node_json" | jq -r '[.status.conditions[]? | select(.type == "Ready") | .status][0] // "-"')
  tainted=$(printf '%s' "$node_json" | jq '[.spec.taints[]? | select(.effect == "NoExecute" and (.key == "node.kubernetes.io/not-ready" or .key == "node.kubernetes.io/unreachable"))] | length > 0')
  replacement=$(printf '%s' "$pods_json" | jq -r --arg uid "$OLD_UID" '[.items[] | select(.metadata.uid != $uid and .metadata.deletionTimestamp == null) | .metadata.uid] | if length == 0 then "-" else join(",") end')
  original_running=unknown
  if runtime_ids=$(docker exec "$NODE" crictl ps --name web -q); then
    original_running=no
    if printf '%s\n' "$runtime_ids" | grep -Fxq "$OLD_CID"; then original_running=yes; fi
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$timestamp" "$ready" "$tainted" "$replacement" "$lease" "$original_running" >> ~/labs/lab06/samples.tsv
  date --date="@$timestamp" --iso-8601=seconds
  printf 'Ready=%s NoExecute=%s replacement=%s Lease=%s original-running=%s\n' "$ready" "$tainted" "$replacement" "$lease" "$original_running"
  printf '%s' "$pods_json" | jq '.items[] | {name: .metadata.name, uid: .metadata.uid, node: .spec.nodeName, deleting: .metadata.deletionTimestamp}'
  sleep 10
done | tee ~/labs/lab06/timeline.txt
}

node_intervals() {
STOP_EPOCH=$(cat ~/labs/lab06/stopped-at.txt)
awk -F '\t' -v stopped="$STOP_EPOCH" '
  $2 != "True" && $2 != "-" && !unavailable {unavailable=$1}
  $3 == "true" && !tainted {tainted=$1}
  $4 != "-" && !replacement {replacement=$1}
  END {
    if (unavailable) printf "stop-command completion to first unavailable sample: %d s\n", unavailable-stopped;
    else print "node unavailable: not observed";
    if (tainted && replacement && replacement >= tainted) printf "first taint sample to first replacement sample: %d s\n", replacement-tainted;
    else if (tainted && replacement) print "taint-to-replacement interval: inconclusive observation order";
    else print "taint-to-replacement interval: not observed";
  }' ~/labs/lab06/samples.tsv
}
