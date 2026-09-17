#!/usr/bin/env bash
set -euo pipefail

cluster_name=${1:-chaos}
shift || true
lab_images=("${@:-bloomberg/goldpinger:v3.11.3}")

case "$(uname -m)" in
  x86_64) platform=linux/amd64 ;;
  aarch64) platform=linux/arm64 ;;
  *) printf 'Unsupported architecture: %s\n' "$(uname -m)" >&2; exit 1 ;;
esac

kind get clusters | grep -Fx "$cluster_name" >/dev/null || {
  printf 'Kind cluster not found: %s\n' "$cluster_name" >&2
  exit 1
}

archive_dir=$(mktemp -d)
trap 'rm -rf "$archive_dir"' EXIT

# Docker's containerd image store keeps a pulled image's multi-platform index
# but only this VM's platform content. kind imports every platform named in an
# archive, so export only the native platform to avoid missing-digest errors.
# Docker releases without `save --platform` use the classic single-platform store.
save_supports_platform=false
[[ "$(docker save --help 2>/dev/null)" == *--platform* ]] && save_supports_platform=true

for image in "${lab_images[@]}"; do
  docker image inspect "$image" >/dev/null || {
    printf 'Required local image not found: %s. Re-run ansible/run.sh to cache it.\n' "$image" >&2
    exit 1
  }

  if [[ "$save_supports_platform" == true ]]; then
    archive="$archive_dir/image.tar"
    timeout 5m docker save --platform "$platform" -o "$archive" "$image"
    timeout 5m kind load image-archive "$archive" --name "$cluster_name"
    rm -f "$archive"
  else
    timeout 5m kind load docker-image "$image" --name "$cluster_name"
  fi
done
