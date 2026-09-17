#!/usr/bin/env bash
set -euo pipefail

ansible_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

usage() {
  printf 'Usage: %s list | <0-16> [setup|verify|question|solution|reset]\n' "$(basename "$0")"
}

if [[ "${1:-}" == "list" ]]; then
  for definition in "$ansible_dir"/labs/[0-9][0-9]-*.yml; do
    printf '%s  %s\n' "$(basename "$definition" | cut -d- -f1)" "$(sed -n 's/^title: //p' "$definition")"
  done
  exit 0
fi

[[ "${1:-}" =~ ^[0-9]{1,2}$ ]] || { usage >&2; exit 1; }
printf -v lab_id '%02d' "$((10#$1))"
(( 10#$lab_id <= 16 )) || { usage >&2; exit 1; }
action=${2:-setup}
case "$action" in setup|verify|question|solution|reset) ;; *) usage >&2; exit 1 ;; esac

definition=$(find "$ansible_dir/labs" -maxdepth 1 -name "$lab_id-*.yml" -print -quit)
[[ -n "$definition" ]] || { printf 'Lab %s is not defined.\n' "$lab_id" >&2; exit 1; }

if [[ "$action" == verify || "$action" == reset ]]; then
  exec "$ansible_dir/run.sh" --playbook "$ansible_dir/labs.yml" \
    --extra-vars "{\"lab_definition\": \"$definition\", \"lab_action\": \"$action\"}" \
    "${@:3}"
fi

# The playbook renders the task or solution to a local file so it prints as
# plain text instead of JSON-escaped debug output.
text_output=$(mktemp "${TMPDIR:-/tmp}/chaos-labs-$action.XXXXXX")
trap 'rm -f "$text_output"' EXIT
extra_vars="{\"lab_definition\": \"$definition\", \"lab_action\": \"$action\", \"lab_text_output\": \"$text_output\"}"

if [[ "$action" == setup ]]; then
  # Keep setup progress visible; the task prints last so it stays on screen.
  "$ansible_dir/run.sh" --playbook "$ansible_dir/labs.yml" --extra-vars "$extra_vars" "${@:3}"
elif ! ansible_log=$("$ansible_dir/run.sh" --playbook "$ansible_dir/labs.yml" \
  --extra-vars "$extra_vars" "${@:3}" 2>&1); then
  printf '%s\n' "$ansible_log" >&2
  exit 1
fi
cat "$text_output"
