#!/usr/bin/env bash
# Maintainer checks only; never connects to or changes the teaching VM.
set -euo pipefail
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"

for executable in bash jq openssl python3 ansible-playbook; do
  command -v "$executable" >/dev/null || {
    echo "Required command not found: $executable" >&2
    exit 1
  }
done
[[ -e /proc/self/exe ]] || {
  echo 'Run full validation on Linux or WSL; process-identity tests require /proc.' >&2
  exit 1
}
python3 -c 'import yaml, jinja2' || {
  echo 'Install the authoring dependencies from requirements-dev.txt.' >&2
  exit 1
}
export ANSIBLE_CONFIG="$repo_dir/ansible/ansible.cfg"

python3 scripts/check-labs.py
bash tests/test-lifecycle.sh
for playbook in provision platform browser-export labs cards reset-all; do
  ansible-playbook -i ansible/inventory/vagrant.ini "ansible/$playbook.yml" --syntax-check
done
ansible-playbook -i localhost, tests/ansible/identity.yml
python3 -m unittest discover -s tests -v
echo 'Local validation passed. Live VM and Kubernetes acceptance must be checked separately.'
