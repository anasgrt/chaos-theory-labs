#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

save_revision() {
local revision
revision=$(k get deployment config-web -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}') || return
test -n "$revision" || { echo 'STOP: no deployment revision found.' >&2; return 1; }
printf '%s\n' "$revision" | tee "$HOME/labs/lab11/stable-revision.txt"
}
