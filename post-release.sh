#!/usr/bin/env bash
#
# Run by "git release" after the release X.Y.Z is pushed. Can also be run by hand:
#
#   ./post-release.sh 5.6.2
#
# The theme repositories next to this one build on the sso image. Their Dockerfile (FROM ...) and
# __version__ are set to the new version. The changes are NOT committed: commit them in the theme
# repositories once the CI has built the image ghcr.io/g10f/sso:<version>.
#
# A theme repository with a file .skip-release is skipped.

set -euo pipefail

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

update_theme() {
  local theme_dir=$1
  local package=$2

  if [ -f "$theme_dir/Dockerfile" ]; then
    sed -i "s#FROM ghcr\.io/g10f/sso:.*#FROM ghcr.io/g10f/sso:$version#" "$theme_dir/Dockerfile"
  fi
  if [ -f "$theme_dir/$package/__init__.py" ]; then
    sed -i "s/^__version__ = .*/__version__ = '$version'/" "$theme_dir/$package/__init__.py"
  fi
  echo "updated $theme_dir (not committed)"
}

# theme repositories are found by their name: ../sso-<name>-theme contains the package sso_<name>_theme
for theme_dir in ../sso-*-theme; do
  if [ ! -d "$theme_dir" ]; then
    continue  # no theme repository checked out
  fi
  if [ -f "$theme_dir/.skip-release" ]; then
    echo "skipped $theme_dir (.skip-release present)"
    continue  # theme opted out of release bumps
  fi
  name=${theme_dir#../sso-}  # ../sso-<name>-theme -> <name>-theme
  name=${name%-theme}        # <name>-theme -> <name>
  update_theme "$theme_dir" "sso_${name}_theme"
done
