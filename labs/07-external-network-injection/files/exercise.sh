#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

net() {
sudo nsenter --target "$(docker inspect -f '{{.State.Pid}}' ce-lab07)" --net -- tc "$@"
}

compare_delay() {
cd ~/labs/lab07
python3 - <<'PY'
import pathlib, re
def mean(phase, count):
    text = pathlib.Path(f'{phase}-{count}.txt').read_text()
    match = re.search(r'mean_ms=([0-9.]+)', text)
    if not match:
        raise SystemExit(f'Missing successful probe: {phase}-{count}.txt')
    return float(match[1])
for count in (1, 4):
    baseline = mean('baseline', count)
    for phase, dose in (('control', 1), ('delayed', 25), ('recovered', 0)):
        added = mean(phase, count) - baseline
        print(f'{phase}: exchanges={count} added_ms={added:.2f} expected_approximately_ms={count * dose}')
PY
}
