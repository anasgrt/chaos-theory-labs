#!/usr/bin/env bash
# Supplied measurement helpers; source from the lab shell.

record_versions() {
cd ~/labs/lab00
{
  cat ~/labs/book-commit.txt ~/labs/versions.txt
  for image in python:3.12-slim ubuntu:24.04 busybox:1.36 nginx:1.27 ghcr.io/shopify/toxiproxy:2.12.0 bloomberg/goldpinger:3.11.3; do
    printf '%s ' "$image"
    docker image inspect "$image" --format 'id={{.Id}} digests={{json .RepoDigests}}'
  done
} 2>&1 | tee versions-images.txt
}
