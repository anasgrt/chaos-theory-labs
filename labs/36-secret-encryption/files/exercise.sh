#!/usr/bin/env bash
# Keep static-Pod replacement and repeated observation outside the learner's commands.
install_provider() {
  local mode=$1
  case "$mode" in key1|key2) ;; *) return 2 ;; esac
  docker cp "$HOME/labs/lab36/apiserver-$mode.json" lab36-control-plane:/etc/kubernetes/ce-lab36-next-apiserver.json || return
  docker exec lab36-control-plane chmod 600 /etc/kubernetes/ce-lab36-next-apiserver.json || return
  docker exec lab36-control-plane mv /etc/kubernetes/ce-lab36-next-apiserver.json /etc/kubernetes/manifests/kube-apiserver.yaml
}

wait_provider() {
  local mode=$1 state i
  case "$mode" in key1|key2) ;; *) return 2 ;; esac
  for i in {1..90}; do
    if k get --raw /livez >/dev/null 2>&1 &&
       state=$(k -n kube-system get pod kube-apiserver-lab36-control-plane -o json 2>/dev/null) &&
       printf '%s' "$state" | jq -e --arg mode "$mode" '
         .metadata.annotations["chaos-labs/provider"] == $mode and
         .status.containerStatuses[0].state.running != null and
         any(.spec.containers[0].command[];
             . == ("--encryption-provider-config=/etc/kubernetes/ce-lab36/provider-" + $mode + ".json"))' >/dev/null; then
      printf 'Live API and running mirror Pod observed with provider=%s\n' "$mode"
      return 0
    fi
    sleep 2
  done
  echo 'STOP: the API and requested provider configuration did not converge.' >&2
  return 1
}

stored_secret() {
  python3 "$HOME/labs/lab36/storage_probe.py" "$@"
}

secret_value() {
  local name=$1 value
  case "$name" in legacy|fresh) ;; *) return 2 ;; esac
  value=$(k get secret "$name" -o json) || return
  printf '%s' "$value" | jq -r '.data.password | @base64d'
}

provider_summary() {
  local mode=$1
  case "$mode" in key1|key2) ;; *) return 2 ;; esac
  jq '{resources: [.resources[] | {resources, providers:
       [.providers[] | if has("aescbc") then {aescbc_key_names: [.aescbc.keys[].name]} else . end]}]}' \
     "$HOME/labs/lab36/provider-$mode.json"
}
