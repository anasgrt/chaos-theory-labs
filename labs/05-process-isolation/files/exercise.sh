#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

sandbox_limits() {
path=$(systemctl show ce-lab05.scope -p ControlGroup --value)
if [ -n "$path" ] && systemctl is-active --quiet ce-lab05.scope; then
  sudo cat "/sys/fs/cgroup$path/cpu.max" "/sys/fs/cgroup$path/memory.max" "/sys/fs/cgroup$path/pids.max"
  sudo lsns -t pid
else
  echo 'STOP: no active sandbox scope. Restart the sandbox before reading its limits.'
fi
}

sandbox_throttling() {
cd ~/labs/lab05
path=$(systemctl show ce-lab05.scope -p ControlGroup --value)
if [ -n "$path" ] && systemctl is-active --quiet ce-lab05.scope; then
  sudo cat "/sys/fs/cgroup$path/cpu.stat" | tee cpu-before.txt
  sleep 5
  sudo cat "/sys/fs/cgroup$path/cpu.stat" | tee cpu-after.txt
  awk 'NR==FNR {before[$1]=$2; next} $1 ~ /^(nr_throttled|throttled_usec)$/ {print $1 " increase=" $2-before[$1]}' cpu-before.txt cpu-after.txt
else
  echo 'STOP: no active sandbox scope. Restart the sandbox before observing enforcement.'
fi
}
