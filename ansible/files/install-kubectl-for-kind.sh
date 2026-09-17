#!/usr/bin/env bash
set -euo pipefail

cluster_name=${1:-chaos}
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
tmp_binary=$(mktemp)
tmp_checksum=$(mktemp)
cleanup() {
  rm -f "$tmp_binary" "$tmp_checksum"
}
trap cleanup EXIT

base_url="https://dl.k8s.io/release/${kube_version}/bin/linux/${architecture}/kubectl"
curl -fsSL -o "$tmp_binary" "$base_url"
curl -fsSL -o "$tmp_checksum" "${base_url}.sha256"
printf '%s  %s\n' "$(cat "$tmp_checksum")" "$tmp_binary" | sha256sum --check
sudo install -m 0755 "$tmp_binary" /usr/local/bin/kubectl
kubectl version --client
