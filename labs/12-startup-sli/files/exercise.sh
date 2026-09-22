#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

show_trial() {
jq '{trial,
     node: .pod.spec.nodeName,
     conditions: .pod.status.conditions,
     containers: .pod.status.containerStatuses,
     selector: .service.spec.selector,
     ready_endpoints: (if .endpointslices.diagnostic_error then null else
       [.endpointslices.items[]?.endpoints[]? | select(.conditions.ready == true)] | length end),
     diagnostic_errors: [to_entries[] | select(.value.diagnostic_error?) | {resource: .key, error: .value}],
     events: .events.items}' "$@"
}

trial() {
(
  set -euo pipefail
  cd "$HOME/labs/lab12"
  local label=$1 count=${2:-1}
  case "$label" in normal|delayed|unscheduled|selector|restored) ;; *) return 2 ;; esac
  # Remove only this case's saved evidence before attempting a new measurement.
  rm -f "evidence-$label.json" "runs-$label.txt" "$label-complete.txt"
  if bash run.sh "$count" | tee "runs-$label.txt"; then
    echo "checker exit=0"
  else
    echo 'STOP: checker did not complete; no result or SLI is valid for this attempt.' >&2
    return 1
  fi
  for n in $(seq 1 "$count"); do
    test -s "diagnostics/run-$n.json"
    cp "diagnostics/run-$n.json" "evidence-$label-$n.json"
    show_trial "evidence-$label-$n.json"
  done
  cp "diagnostics/run-1.json" "evidence-$label.json"
  cat metrics/start.prom
  printf '%s\n' "$count" > "$label-complete.txt"
)
}

startup_summary() {
(
  set -euo pipefail
  cd "$HOME/labs/lab12"
  test "$(cat restored-complete.txt)" = 3 || { echo 'STOP: complete three restored trials first.'; return 1; }
  awk '/^run=/ {n++; if ($2 == "success=1") good++}
    END {if (n == 3) printf "healthy sample: %d/%d = %.3f (%.1f%%)\n", good,n,good/n,100*good/n;
         else {print "Incomplete sample; inspect checker output"; exit 1}}' runs-restored.txt
)
}
