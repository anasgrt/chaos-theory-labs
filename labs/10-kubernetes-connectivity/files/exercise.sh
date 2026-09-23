#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

wait_endpoint_port() {
local port=$1 endpoints i
for i in $(seq 1 30); do
  if endpoints=$(k get endpointslices -l kubernetes.io/service-name=web -o json) &&
     printf '%s' "$endpoints" | jq -e --argjson port "$port" '(.items | length) > 0 and all(.items[]; any(.ports[]; .port == $port))' >/dev/null; then
    return 0
  fi
  sleep 1
done
echo "Endpoint port did not become $port; stop and inspect the Service and EndpointSlices." >&2
return 1
}

wait_service() {
for i in $(seq 1 10); do
  probe http://web.ce-lab10.svc.cluster.local/ && return 0
  sleep 1
done
echo 'STOP: Service HTTP did not recover.' >&2
return 1
}

probe_local() {
for i in $(seq 1 10); do
  k exec web -- python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8080/",timeout=3).status)' && return 0
  sleep 1
done
echo 'STOP: local listener did not answer.' >&2
return 1
}
