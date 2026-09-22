#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

wait_backend_removed() {
local endpoints
for i in $(seq 1 30); do
  if endpoints=$(ksys get endpointslices -l kubernetes.io/service-name=kube-dns -o json) &&
     printf '%s' "$endpoints" | jq -e '([.items[]?.endpoints[]?] | length) == 0' >/dev/null; then
    ksys get endpointslices -l kubernetes.io/service-name=kube-dns -o yaml
    return
  fi
  sleep 1
done
echo 'STOP: expected endpoint state was not observed.' >&2
return 1
}

wait_backend_ready() {
local endpoints
for i in $(seq 1 30); do
  if endpoints=$(ksys get endpointslices -l kubernetes.io/service-name=kube-dns -o json) &&
     printf '%s' "$endpoints" | jq -e 'any(.items[]?.endpoints[]?; .conditions.ready == true)' >/dev/null; then
    ksys get endpointslices -l kubernetes.io/service-name=kube-dns -o yaml
    return
  fi
  sleep 1
done
echo 'STOP: expected endpoint state was not observed.' >&2
return 1
}
