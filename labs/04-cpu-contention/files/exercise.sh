#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

measure_baseline() {
cd ~/labs/lab04
for run in 1 2 3; do taskset -c "$CPU" python3 work.py | tee "baseline-$run.txt"; done
awk 'NR==1 {min=max=$2} {sum+=$2; if ($2<min) min=$2; if ($2>max) max=$2} END {printf "baseline mean=%.4fs range=%.4f-%.4fs\n", sum/NR, min, max}' baseline-1.txt baseline-2.txt baseline-3.txt
}

wait_neighbour_stopped() {
for i in $(seq 1 10); do
  systemctl list-units --all --plain --no-legend ce-lab04.service | grep -q . || break
  sleep 1
done
}

measure_quota() {
path=$(systemctl show ce-lab04 -p ControlGroup --value)
if [ -n "$path" ] && systemctl is-active --quiet ce-lab04; then
  echo 'Neighbour active before measurement'
  sudo cat "/sys/fs/cgroup$path/cpu.max"
  sudo cat "/sys/fs/cgroup$path/cpu.stat" | tee quota-before.txt
  taskset -c "$CPU" python3 work.py | tee quota.txt
  if systemctl is-active --quiet ce-lab04; then
    echo 'Neighbour still active after measurement'
    sudo cat "/sys/fs/cgroup$path/cpu.stat" | tee quota-after.txt
    awk 'NR==FNR {before[$1]=$2; next} $1 ~ /^(nr_throttled|throttled_usec)$/ {print $1 " increase=" $2-before[$1]}' quota-before.txt quota-after.txt
  else
    echo 'Inconclusive: the neighbour ended before the measurement finished.'
  fi
else
  echo 'STOP: no active neighbour cgroup; this phase was not measured.'
fi
}

compare_times() {
awk 'NR==1 {min=max=$2} {sum+=$2; if ($2<min) min=$2; if ($2>max) max=$2} END {printf "baseline mean=%.4fs range=%.4f-%.4fs\n", sum/NR, min, max}' baseline-1.txt baseline-2.txt baseline-3.txt
for f in loaded.txt quota.txt recovered.txt; do
  awk -v f="$f" 'NR==1 {min=max=$2} {sum+=$2; if ($2<min) min=$2; if ($2>max) max=$2} END {printf "%s mean=%.4fs range=%.4f-%.4fs\n", f, sum/NR, min, max}' "$f"
done
}
