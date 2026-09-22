#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ansible_dir="$repo_dir/ansible"
source "$repo_dir/scripts/lib/lab-env.sh"
if [[ ${1:-} == provision ]]; then
  lab_id=''; definition=''; playbook="$ansible_dir/provision.yml"
else
  select_lab "${1:-}"
  playbook="$ansible_dir/labs.yml"
fi
shift
if [[ ${1:-} == --playbook ]]; then
  [[ -f ${2:-} ]] || { echo 'Supply an existing playbook.' >&2; exit 1; }
  playbook=$2
  shift 2
fi
for executable in vagrant ansible-playbook; do
  command -v "$executable" >/dev/null || { echo "Required command not found: $executable" >&2; exit 1; }
done
cd "$repo_dir"
state=$(vagrant status "$lab_machine" --machine-readable | awk -F, -v machine="$lab_machine" '$2 == machine && $3 == "state" {print $4; exit}')
[[ $state == running ]] || { echo 'The shared VM is not running. Use ./lab.sh provision for first use, or ./lab.sh start to resume it.' >&2; exit 1; }
ssh_config=$(mktemp "${TMPDIR:-/tmp}/chaos-lab-ssh.XXXXXX")
inventory=$(mktemp "${TMPDIR:-/tmp}/chaos-lab-inventory.XXXXXX")
vars_file=$(mktemp "${TMPDIR:-/tmp}/chaos-lab-connection.XXXXXX")
trap 'rm -f "$ssh_config" "$inventory" "$vars_file"' EXIT
vagrant ssh-config "$lab_machine" > "$ssh_config"
printf '[chaos_labs]\n%s ansible_host=%s ansible_connection=ssh\n' "$lab_machine" "$lab_machine" > "$inventory"
{
  printf '{"lab_id":'; json_string "$lab_id"
  printf ',"lab_definition":'; json_string "$definition"
  printf ',"ansible_ssh_common_args":'; json_string "-F '$ssh_config'"
  printf '}\n'
} > "$vars_file"
export ANSIBLE_CONFIG="$ansible_dir/ansible.cfg"
ansible-playbook -i "$inventory" "$playbook" "$@" --limit "$lab_machine" --extra-vars "@$vars_file"
