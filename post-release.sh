#!/usr/bin/env bash
#
# Run by "git release" after the release X.Y.Z of this repository is pushed. Can also be run by hand:
#
#   ./post-release.sh X.Y.Z
#
# The theme repositories next to this one build on the image of this repository (Dockerfile:
# FROM <IMAGE>:<version>). For each of them this script
#   1. waits until the CI has built the image <IMAGE>:X.Y.Z (the push of the tag has just started it),
#   2. sets the FROM line to X.Y.Z and commits it as "<name> X.Y.Z",
#   3. runs "git release X.Y.Z" in the theme: it writes the version into the theme's __version__, creates the
#      tag and pushes. The CI of the theme builds that tag and decides where it is deployed.
#
# A theme repository with a file .skip-release is skipped. A theme that is not ready for a release (not on
# main, uncommitted changes, behind origin) is reported and skipped, the other themes are released anyway;
# the script then ends with an error, so that the skipped theme is not overlooked. Running it again releases
# the themes that are still missing (a theme that already has the release X.Y.Z is left alone).
#
# This file is the same in the base repositories (sso, blog-site), only IMAGE and NAME differ.

set -euo pipefail

IMAGE=ghcr.io/g10f/sso
NAME=sso                # the commit message in a theme is "$NAME X.Y.Z"
WAIT_MINUTES=30         # how long to wait for the CI to build the image

fail() {
  echo "error: $1" >&2
  exit 1
}

version=${1:-}
if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  fail "usage: $0 X.Y.Z"
fi

# all paths are relative to the repository root
cd "$(dirname "$0")"


# --- the theme repositories ----------------------------------------------------------------------------

# A theme repository is a git repository next to this one whose Dockerfile builds on IMAGE.
themes=()
for theme_dir in ../*/; do
  theme_dir=${theme_dir%/}
  if [ ! -d "$theme_dir/.git" ] || ! grep -q "^FROM ${IMAGE//./\\.}:" "$theme_dir/Dockerfile" 2>/dev/null; then
    continue  # not a theme repository
  fi
  if [ -f "$theme_dir/.skip-release" ]; then
    echo "skipped $theme_dir (.skip-release present)"
    continue
  fi
  themes+=("$theme_dir")
done

if [ ${#themes[@]} -eq 0 ]; then
  echo "no theme repositories next to this one, nothing to do"
  exit 0
fi
echo "themes to release with $NAME $version: ${themes[*]}"


# --- 1. wait for the image -----------------------------------------------------------------------------

# The image is public on ghcr.io; the registry API still wants an (anonymous) token.
repository=${IMAGE#ghcr.io/}
image_exists() {
  local token
  token=$(curl -fsS "https://ghcr.io/token?scope=repository:$repository:pull" | jq -r .token) || return 1
  curl -fsS -o /dev/null -I \
    -H "Authorization: Bearer $token" \
    -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json" \
    "https://ghcr.io/v2/$repository/manifests/$version" 2>/dev/null
}

echo "waiting for $IMAGE:$version (up to $WAIT_MINUTES minutes) ..."
deadline=$((SECONDS + WAIT_MINUTES * 60))
until image_exists; do
  if [ $SECONDS -ge $deadline ]; then
    fail "$IMAGE:$version does not exist after $WAIT_MINUTES minutes, the themes were not released. Check the CI of this repository, then run ./post-release.sh $version again."
  fi
  sleep 30
done
echo "$IMAGE:$version exists"


# --- 2. and 3. release each theme ----------------------------------------------------------------------

skipped=()
for theme_dir in "${themes[@]}"; do
  echo
  echo "--- $theme_dir"

  # The release must contain exactly what is on origin/main plus the new FROM line.
  branch=$(git -C "$theme_dir" branch --show-current)
  if [ "$branch" != main ]; then
    echo "not released: $theme_dir is on branch '$branch', not on main" >&2
    skipped+=("$theme_dir")
    continue
  fi
  if ! git -C "$theme_dir" diff --quiet HEAD; then
    echo "not released: $theme_dir has uncommitted changes" >&2
    skipped+=("$theme_dir")
    continue
  fi
  if ! git -C "$theme_dir" fetch --quiet --tags origin \
      || ! git -C "$theme_dir" merge-base --is-ancestor origin/main HEAD; then
    echo "not released: $theme_dir is behind origin/main (or origin could not be fetched), pull first" >&2
    skipped+=("$theme_dir")
    continue
  fi
  if git -C "$theme_dir" rev-parse --quiet --verify "refs/tags/$version" >/dev/null; then
    echo "$theme_dir already has the release $version, nothing to do"
    continue
  fi

  sed -i "s#^FROM ${IMAGE//./\\.}:.*#FROM $IMAGE:$version#" "$theme_dir/Dockerfile"
  if ! git -C "$theme_dir" diff --quiet -- Dockerfile; then
    git -C "$theme_dir" commit --quiet -m "$NAME $version" -- Dockerfile
  fi

  # git release checks the theme once more, writes __version__, tags and pushes (asks nothing with --yes)
  if ! (cd "$theme_dir" && git release "$version" --yes); then
    echo "not released: git release failed in $theme_dir (the commit \"$NAME $version\" is local only)" >&2
    skipped+=("$theme_dir")
  fi
done

echo
if [ ${#skipped[@]} -gt 0 ]; then
  fail "these themes were not released with $NAME $version: ${skipped[*]}. Fix them, then run ./post-release.sh $version again."
fi
echo "all themes are released with $NAME $version"
