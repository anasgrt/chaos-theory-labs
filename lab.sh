#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ansible_dir="$repo_dir/ansible"
source "$repo_dir/scripts/lib/lab-env.sh"
usage() { echo "Usage: $0 provision|platform|start|ssh|stop|status|list | NN [setup|verify|reset|question|solution]" >&2; }
[[ $# -ge 1 && $# -le 2 ]] || { usage; exit 1; }
cd "$repo_dir"
export ANSIBLE_CONFIG="$ansible_dir/ansible.cfg"
case "$1" in
  provision|platform|start|ssh|stop|status)
    [[ $# -eq 1 ]] || { usage; exit 1; }
    case "$1" in
      start) exec vagrant up "$lab_machine" --provider=virtualbox --no-provision ;;
      ssh) exec vagrant ssh "$lab_machine" ;;
      stop) exec vagrant halt "$lab_machine" ;;
      status) exec vagrant status "$lab_machine" ;;
      platform) exec "$repo_dir/scripts/run-ansible.sh" platform ;;
      provision)
        command -v ansible-playbook >/dev/null || { echo 'Install Ansible on the controller first.' >&2; exit 1; }
        vagrant up "$lab_machine" --provider=virtualbox --no-provision
        exec "$repo_dir/scripts/run-ansible.sh" provision ;;
    esac
    ;;
esac
if [[ $1 == list ]]; then
  [[ $# -eq 1 ]] || { usage; exit 1; }
  lab_id=''; definition=''; action=list
else
  select_lab "$1"
  action=${2:-setup}
fi
case "$action" in setup|verify|reset|question|solution|list) ;; *) usage; exit 1 ;; esac
command -v ansible-playbook >/dev/null || { echo 'Install Ansible on the controller first.' >&2; exit 1; }
if [[ $action == verify || $action == reset ]]; then
  exec "$repo_dir/scripts/run-ansible.sh" "$lab_id" --extra-vars "lab_action=$action"
fi
text_output=$(mktemp "${TMPDIR:-/tmp}/chaos-lab-card.XXXXXX")
vars_file=$(mktemp "${TMPDIR:-/tmp}/chaos-lab-vars.XXXXXX")
log_file=$(mktemp "${TMPDIR:-/tmp}/chaos-lab-read.XXXXXX")
trap 'rm -f "$text_output" "$vars_file" "$log_file"' EXIT
{
  printf '{"lab_id":'; json_string "$lab_id"
  printf ',"lab_definition":'; json_string "$definition"
  printf ',"lab_action":'; json_string "$action"
  printf ',"lab_text_output":'; json_string "$text_output"
  printf '}\n'
} > "$vars_file"
if [[ $action == setup ]]; then
  "$repo_dir/scripts/run-ansible.sh" "$lab_id" --extra-vars "@$vars_file"
else
  if ! ansible-playbook -i localhost, "$ansible_dir/cards.yml" --extra-vars "@$vars_file" > "$log_file" 2>&1; then
    cat "$log_file" >&2
    exit 1
  fi
fi
cat "$text_output"
