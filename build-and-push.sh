#!/bin/bash
tag=$(python apps/version.py)
DOCKER_BUILDKIT=1
docker buildx create --use
docker buildx build --platform linux/amd64 -t g10f/sso:$tag -t g10f/sso:latest --load .
