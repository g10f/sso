#!/bin/bash
tag=1.0.14
docker buildx build --platform linux/amd64,linux/arm64 -t g10f/sso:$tag -t g10f/sso:latest --push .
