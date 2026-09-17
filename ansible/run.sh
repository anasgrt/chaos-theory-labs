#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ansible_dir="$root_dir/ansible"
ssh_config=$(mktemp "${TMPDIR:-/tmp}/chaos-labs-vagrant-ssh.XXXXXX")
playbook="$ansible_dir/playbook.yml"

if [[ "${1:-}" == "--playbook" ]]; then
  [[ -n "${2:-}" ]] || {
    printf 'Missing playbook after --playbook.\n' >&2
    exit 1
  }
  playbook=$2
  shift 2
fi

[[ -f "$playbook" ]] || {
  printf 'Playbook not found: %s\n' "$playbook" >&2
  exit 1
}

cleanup() {
  rm -f "$ssh_config"
}
trap cleanup EXIT

for command in vagrant ansible-playbook; do
  command -v "$command" >/dev/null || {
    printf 'Required command not found: %s\n' "$command" >&2
    exit 1
  }
done

cd "$root_dir"
machine_state=$(vagrant status default --machine-readable | awk -F, '$2 == "default" && $3 == "state" { print $4; exit }')
[[ "$machine_state" == "running" ]] || {
  printf 'The chaos-labs VM is not running. Run vagrant up first.\n' >&2
  exit 1
}

vagrant ssh-config default > "$ssh_config"
export ANSIBLE_CONFIG="$ansible_dir/ansible.cfg"

ansible-playbook \
  -i "$ansible_dir/inventory/vagrant.ini" \
  "$playbook" \
  --extra-vars "{\"ansible_ssh_common_args\": \"-F $ssh_config\"}" \
  "$@"
