#!/usr/bin/env bash
# Shared argument handling only; Vagrant and Ansible perform the lifecycle work.
lab_machine=chaos
select_lab() {
  [[ "${1:-}" =~ ^[0-9]{1,2}$ ]] || { echo 'Specify a lab number, for example 11.' >&2; return 1; }
  printf -v lab_id '%02d' "$((10#$1))"
  local matches
  shopt -s nullglob
  matches=("$repo_dir/labs/$lab_id-"*/lab.yml)
  shopt -u nullglob
  [[ ${#matches[@]} -eq 1 ]] || { echo "Lab $lab_id must have exactly one definition." >&2; return 1; }
  definition=${matches[0]}
}

json_string() {
  local value=$1
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  value=${value//$'\t'/\\t}
  printf '"%s"' "$value"
}
