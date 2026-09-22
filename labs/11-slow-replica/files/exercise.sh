#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

add_delay() {
curl -fsS --max-time 5 -H 'Content-Type: application/json' -X POST "$T/proxies/slow/toxics" \
  -d "{\"name\":\"lat\",\"type\":\"latency\",\"stream\":\"upstream\",\"toxicity\":1,\"attributes\":{\"latency\":$1,\"jitter\":0}}"
}

change_delay() {
curl -fsS --max-time 5 -H 'Content-Type: application/json' -X POST "$T/proxies/slow/toxics/lat" \
  -d "{\"attributes\":{\"latency\":$1,\"jitter\":0}}"
}

remove_delay() {
curl -fsS --max-time 5 -X DELETE "$T/proxies/slow/toxics/lat"
}
