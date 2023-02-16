#!/bin/bash
tag=$(python3 apps/version.py)
DOCKER_BUILDKIT=1
# docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/g10f/sso:$tag -t g10f/sso:latest --push .
# docker buildx build --pull --platform linux/amd64 -t ghcr.io/g10f/sso:$tag -t g10f/sso:latest --load .
