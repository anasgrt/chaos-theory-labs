#!/usr/bin/env bash
set -euo pipefail

cluster_name=${1:?Supply the selected lab cluster name}
control_plane="${cluster_name}-control-plane"

case "$(uname -m)" in
  x86_64) architecture=amd64 ;;
  aarch64) architecture=arm64 ;;
  *) printf 'Unsupported architecture: %s\n' "$(uname -m)" >&2; exit 1 ;;
esac

docker inspect "$control_plane" >/dev/null 2>&1 || {
  printf 'Kind control-plane container not found: %s\n' "$control_plane" >&2
  exit 1
}

kube_version=$(docker exec "$control_plane" kubeadm version -o short)
# All lab clusters use the pinned kind release. Reuse the matching shared client.
if command -v kubectl >/dev/null &&
   installed_version=$(kubectl version --client -o json | jq -er '.clientVersion.gitVersion') &&
   [[ "$installed_version" == "$kube_version" ]]; then
  exit 0
fi
tmp_binary=$(mktemp)
tmp_checksum=$(mktemp)
staged_binary=''
cleanup() {
  rm -f "$tmp_binary" "$tmp_checksum"
  [[ -z "$staged_binary" ]] || sudo rm -f "$staged_binary"
}
trap cleanup EXIT

base_url="https://dl.k8s.io/release/${kube_version}/bin/linux/${architecture}/kubectl"
curl -fsSL -o "$tmp_binary" "$base_url"
curl -fsSL -o "$tmp_checksum" "${base_url}.sha256"
printf '%s  %s\n' "$(cat "$tmp_checksum")" "$tmp_binary" | sha256sum --check
# Replace atomically so a kubectl process in another lab can keep running.
staged_binary=$(sudo mktemp /usr/local/bin/.kubectl.XXXXXX)
sudo install -m 0755 "$tmp_binary" "$staged_binary"
sudo mv -f "$staged_binary" /usr/local/bin/kubectl
staged_binary=''
kubectl version --client
