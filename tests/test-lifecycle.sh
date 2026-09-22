#!/usr/bin/env bash
# Exercise the real wrappers; stub only external Vagrant/Ansible executables.
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin" "$work/temp with spaces"
export CALLS="$work/calls" TMPDIR="$work/temp with spaces"
export PATH="$work/bin:$PATH"
cat > "$work/bin/vagrant" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'vagrant' >> "$CALLS"; printf ' <%s>' "$@" >> "$CALLS"; printf '\n' >> "$CALLS"
case "$1" in
  status) printf '0,%s,state,%s\n' "$2" "${VM_STATE:-running}" ;;
  ssh-config) printf 'Host %s\n  HostName 127.0.0.1\n  User vagrant\n' "$2" ;;
  up) exit "${UP_RC:-0}" ;;
esac
SH
cat > "$work/bin/ansible-playbook" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf 'ansible' >> "$CALLS"; printf ' <%s>' "$@" >> "$CALLS"; printf '\n' >> "$CALLS"
output=''; id=''; previous=''
for arg in "$@"; do
  if [[ $previous == --extra-vars && $arg == @* ]]; then
    jq -e . "${arg#@}" >/dev/null
    next=$(jq -r '.lab_text_output // empty' "${arg#@}")
    [[ -z $next ]] || output=$next
    next=$(jq -r '.lab_id // empty' "${arg#@}")
    [[ -z $next ]] || id=$next
    if jq -e 'has("ansible_ssh_common_args")' "${arg#@}" >/dev/null; then
      if [[ -n $id ]]; then
        jq -e --arg id "$id" '.lab_definition | endswith("/lab.yml") and contains("/labs/" + $id + "-")' "${arg#@}" >/dev/null
      fi
    fi
  fi
  if [[ $previous == -i && $arg != localhost, ]]; then
    test "$(tail -n 1 "$arg")" = 'chaos ansible_host=chaos ansible_connection=ssh'
    test "$(wc -l < "$arg")" -eq 2
  fi
  previous=$arg
done
[[ ${ANSIBLE_RC:-0} == 0 ]] || exit "$ANSIBLE_RC"
[[ -z $output ]] || printf 'CARD %s\n' "$id" > "$output"
SH
chmod +x "$work/bin/"*
cd "$root"
run() { : > "$CALLS"; bash lab.sh "$@" > "$work/out" 2>&1; }
contains() { grep -F -- "$1" "$CALLS" >/dev/null; }
lab_count=0
for definition in "$root"/labs/[0-9][0-9]-*/lab.yml; do
  directory=${definition%/lab.yml}
  number=${directory##*/}
  number=${number%%-*}
  lab_count=$((lab_count + 1))
  export EXPECTED_ID=$number
  run "$number" setup
  contains 'vagrant <status> <chaos> <--machine-readable>'
  contains 'vagrant <ssh-config> <chaos>'
  contains '<--limit> <chaos>'
  ! grep -E '<up>|<destroy>|provision.yml' "$CALLS"
  test "$(grep -c '^vagrant' "$CALLS")" -eq 2
  test "$(grep -c '^ansible' "$CALLS")" -eq 1
  grep -Fx "CARD $number" "$work/out" >/dev/null
  run "$number" reset
  contains '<lab_action=reset>'
  contains '/labs.yml>'
  contains '<--limit> <chaos>'
  ! grep -E '<up>|<destroy>|<halt>|provision.yml' "$CALLS"
done
export EXPECTED_ID=02
run 2 verify
contains '<--limit> <chaos>'
contains '<lab_action=verify>'
for action in start ssh stop status; do
  run "$action"
  test "$(wc -l < "$CALLS")" -eq 1
  contains '<chaos>'
done
run provision
contains 'vagrant <up> <chaos> <--provider=virtualbox> <--no-provision>'
contains '/provision.yml>'
test "$(grep -c '^ansible' "$CALLS")" -eq 1
run platform
contains '/platform.yml>'
contains '<--limit> <chaos>'
! grep -E '<up>|<destroy>|<halt>|provision.yml' "$CALLS"
for action in question solution; do
  run 02 "$action"
  ! grep '^vagrant' "$CALLS"
  grep -Fx 'CARD 02' "$work/out" >/dev/null
done
run list
! grep '^vagrant' "$CALLS"
for bad in '' 27 28 29 30 31 32 33 34 35 36 37 99 100 -1 x 0x10 '../04' '04;false'; do
  for action in setup verify reset question solution; do
    if run "$bad" "$action"; then echo "Accepted invalid ID: $bad ($action)" >&2; exit 1; fi
    test ! -s "$CALLS"
  done
done
if run 02 unknown; then exit 1; fi
test ! -s "$CALLS"
export UP_RC=9
if run provision; then exit 1; fi
test "$(wc -l < "$CALLS")" -eq 1
unset UP_RC
export VM_STATE=poweroff
if run 02 verify; then exit 1; fi
! grep '^ansible' "$CALLS"
if run 02 reset; then exit 1; fi
! grep '^ansible' "$CALLS"
unset VM_STATE
export ANSIBLE_RC=7
if run 02 setup; then exit 1; fi
! grep '^CARD' "$work/out"
if run 02 question; then exit 1; fi
unset ANSIBLE_RC
# Resolve the checkout from the script location, including spaces, not the CWD.
mkdir -p "$work/repo with spaces"
cp -R "$root/lab.sh" "$root/ansible" "$root/labs" "$root/scripts" "$root/config" "$work/repo with spaces/"
cd "$work"
: > "$CALLS"
bash "$work/repo with spaces/lab.sh" 02 setup > "$work/out" 2>&1
contains '<--limit> <chaos>'
grep -Fx 'CARD 02' "$work/out" >/dev/null
# Duplicate IDs must fail before Vagrant can select a machine.
mkdir "$work/repo with spaces/labs/02-duplicate"
cp "$root/labs/02-external-network-injection/lab.yml" "$work/repo with spaces/labs/02-duplicate/lab.yml"
: > "$CALLS"
if bash "$work/repo with spaces/lab.sh" 02 reset > "$work/out" 2>&1; then exit 1; fi
test ! -s "$CALLS"
test -z "$(find "$TMPDIR" -mindepth 1 -print -quit)"
echo "Lifecycle tests passed: one VM, $lab_count independent actions, offline cards, out-of-range/invalid IDs, failures and temporary-file cleanup."
