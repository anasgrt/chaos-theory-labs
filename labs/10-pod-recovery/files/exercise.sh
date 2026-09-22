#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

sample_http() {
source ~/labs/lab10/env.sh
NODE_IP=$(docker inspect -f '{{.NetworkSettings.Networks.kind.IPAddress}}' lab10-control-plane)
for i in $(seq 1 100); do
  code=$(curl -s --max-time 1 -o /dev/null -w '%{http_code}' "http://$NODE_IP:30080/healthz")
  printf '%s %s\n' "$(date --iso-8601=ns)" "$code"
  sleep 0.2
done | tee ~/labs/lab10/probes.log
}

summarize_http() {
samples=$(wc -l < ~/labs/lab10/probes.log)
if [ "$samples" -eq 100 ]; then
  awk '{n++; if ($2 == "200") good++} END {printf "successes=%d/%d failed=%d availability=%.1f%%\n", good,n,n-good,100*good/n}' ~/labs/lab10/probes.log
  grep -v ' 200$' ~/labs/lab10/probes.log | head
else
  echo "Only $samples/100 samples recorded; wait for terminal 2 to finish before counting."
fi
}
