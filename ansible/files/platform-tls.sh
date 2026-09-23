#!/usr/bin/env bash
# Root-only persistent lab CA; reruns retain identity and renew the leaf if needed.
set -euo pipefail
directory=${1:?Supply the TLS directory}
hostname=${2:?Supply the Rancher DNS hostname}
[[ "$directory" == /* && "$hostname" =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]] || exit 1
umask 077
mkdir -p "$directory"
cd "$directory"
if [[ ! -e ca.crt && ! -e ca.key ]]; then
  openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 3650 \
    -keyout ca.key -out ca.crt -subj '/CN=Chaos Labs Rancher CA' \
    -addext 'basicConstraints=critical,CA:TRUE' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign'
  echo 'changed: created lab CA'
fi
# Never silently replace an incomplete, expired or mismatched CA.
test -s ca.key && test -s ca.crt
openssl x509 -in ca.crt -checkend 2592000 -noout
test "$(openssl pkey -in ca.key -pubout 2>/dev/null)" = "$(openssl x509 -in ca.crt -pubkey -noout)"
renew=true
if [[ -s tls.crt && -s tls.key ]] &&
   openssl verify -CAfile ca.crt -verify_hostname "$hostname" tls.crt >/dev/null 2>&1 &&
   openssl x509 -in tls.crt -checkend 2592000 -noout >/dev/null &&
   [[ "$(openssl pkey -in tls.key -pubout 2>/dev/null)" == "$(openssl x509 -in tls.crt -pubkey -noout)" ]]; then
  renew=false
fi
if "$renew"; then
  staging=$(mktemp -d "$directory/.leaf.XXXXXX")
  trap 'rm -rf "$staging"' EXIT
  openssl req -new -newkey rsa:3072 -nodes -keyout "$staging/tls.key" \
    -out "$staging/tls.csr" -subj "/CN=$hostname"
  printf 'subjectAltName=DNS:%s\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$hostname" > "$staging/extensions"
  openssl x509 -req -in "$staging/tls.csr" -CA ca.crt -CAkey ca.key \
    -set_serial "0x$(openssl rand -hex 16)" -days 365 -sha256 \
    -extfile "$staging/extensions" -out "$staging/tls.crt"
  openssl verify -CAfile ca.crt -verify_hostname "$hostname" "$staging/tls.crt"
  mv "$staging/tls.key" tls.key
  mv "$staging/tls.crt" tls.crt
  echo 'changed: issued Rancher certificate'
fi
