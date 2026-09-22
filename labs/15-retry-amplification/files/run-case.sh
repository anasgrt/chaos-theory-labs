#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
retries=${1:?Use 0 or 1 client retries}
[[ "$retries" == 0 || "$retries" == 1 ]] || exit 2
# Prevent concurrent cases from sharing counters, ports or the failure marker.
exec 9>case.lock
flock -n 9 || { echo 'Another Lab 15 case is running.' >&2; exit 1; }
children=()
cleanup() {
  rm -f fail
  for pid in "${children[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${children[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT
trap 'exit 130' INT TERM
rm -f fail
mkdir -p nginx
: > arrivals-9001.log
: > arrivals-9002.log
python3 upstream.py 9001 > upstream-9001.log 2>&1 & children+=("$!")
python3 upstream.py 9002 > upstream-9002.log 2>&1 & children+=("$!")
nginx -p "$PWD/nginx/" -c "$PWD/nginx.conf" -g 'daemon off;' > nginx.log 2>&1 & children+=("$!")
ready=0
for i in $(seq 1 20); do
  if curl --noproxy '*' -fs --max-time 1 -o /dev/null http://127.0.0.1:9001/healthz &&
     curl --noproxy '*' -fs --max-time 1 -o /dev/null http://127.0.0.1:9002/healthz &&
     curl --noproxy '*' -fs --max-time 1 -o /dev/null http://127.0.0.1:8090/healthz; then
    ready=1; break
  fi
  sleep 0.2
done
kill -0 "${children[@]}"
[[ "$ready" == 1 ]] || { echo 'Fixture did not become ready; inspect logs.' >&2; exit 1; }
python3 client.py baseline "$retries"
touch fail
python3 client.py fault "$retries"
rm fail
python3 client.py recovered "$retries"
