#!/usr/bin/env bash
#
# Creates a new release.
#
#   ./set-version.sh patch      5.4.9 -> 5.4.10
#   ./set-version.sh minor      5.4.9 -> 5.5.0
#   ./set-version.sh major      5.4.9 -> 6.0.0
#   ./set-version.sh 5.6.0      explicit version
#
# What it does:
#   1. checks that the repository is ready for a release
#   2. computes the new version and checks that it is valid
#   3. writes the new version to __init__.py, commits it as "release X.Y.Z" and creates the git tag X.Y.Z
#   4. sets the new version in the theme repositories (without committing)
#
# Afterwards push with "git push --follow-tags". The pushed tag starts the CI build and deployment.
#
# Releases are normally made from main. For a hotfix release from another branch add --hotfix:
#   ./set-version.sh patch --hotfix

set -euo pipefail

VERSION_FILE=apps/sso/__init__.py

fail() {
  echo "error: $1" >&2
  exit 1
}

bump=${1:-}
hotfix=false
if [ "${2:-}" = "--hotfix" ]; then
  hotfix=true
fi

# all paths are relative to the repository root
cd "$(dirname "$0")"


# --- 1. check that the repository is ready for a release ---------------------------------------------

# everything must be committed, so that the release contains exactly what is in git
if ! git diff --quiet HEAD; then
  fail "there are uncommitted changes"
fi

branch=$(git branch --show-current)
if [ "$branch" != "main" ] && [ "$hotfix" = false ]; then
  fail "you are on branch '$branch', releases are made from main (use --hotfix for a hotfix release)"
fi

# fetch release tags that exist on GitHub but not yet locally
if ! git fetch --quiet --tags origin; then
  echo "warning: could not fetch tags from origin" >&2
fi

# The branch must contain the latest release, otherwise the changes of that release would be missing
# in the new one. This happens e.g. on a hotfix branch that was started before the latest release.
latest_release=$(git tag --list '[0-9]*.[0-9]*.[0-9]*' --sort=-version:refname | head -n1)
if [ -n "$latest_release" ] && ! git merge-base --is-ancestor "$latest_release" HEAD; then
  if [ "$hotfix" = true ]; then
    echo "warning: the new release will not contain the changes of release $latest_release" >&2
  else
    fail "release $latest_release is not contained in branch '$branch' (use --hotfix if this is intended)"
  fi
fi


# --- 2. compute the new version and check that it is valid -------------------------------------------

# current version, e.g. 1.13.4 from the line: __version__ = '1.13.4'
current=$(sed -n "s/^__version__ = '\(.*\)'$/\1/p" "$VERSION_FILE")
major=$(echo "$current" | cut -d. -f1)
minor=$(echo "$current" | cut -d. -f2)
patch=$(echo "$current" | cut -d. -f3)

case "$bump" in
  major)
    new="$((major + 1)).0.0"
    ;;
  minor)
    new="$major.$((minor + 1)).0"
    ;;
  patch)
    new="$major.$minor.$((patch + 1))"
    ;;
  *)
    if [[ ! $bump =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      fail "usage: $0 <major|minor|patch|X.Y.Z> [--hotfix]"
    fi
    new=$bump
    ;;
esac

# the new version must be greater than the current one
# (sort -V sorts version numbers, so the greater version comes last)
greater=$(printf '%s\n%s\n' "$current" "$new" | sort -V | tail -n1)
if [ "$new" = "$current" ] || [ "$greater" != "$new" ]; then
  fail "the new version $new is not greater than the current version $current"
fi

# every version can only be released once
if git rev-parse --quiet --verify "refs/tags/$new" >/dev/null; then
  fail "the tag $new already exists"
fi


# --- 3. write the new version, commit and tag --------------------------------------------------------

sed -i "s/^__version__ = .*/__version__ = '$new'/" "$VERSION_FILE"
git commit --quiet -m "release $new" "$VERSION_FILE"

# an annotated tag (-a) is pushed together with the commit by "git push --follow-tags"
git tag -a "$new" -m "release $new"


# --- 4. update the theme repositories ----------------------------------------------------------------
#
# The theme repositories next to this one build on the sso image. Their Dockerfile (FROM ...) and
# __version__ are set to the new version. The changes are NOT committed: commit them in the theme
# repositories once the CI has built the image ghcr.io/g10f/sso:<new version>.

update_theme() {
  local theme_dir=$1
  local package=$2

  if [ ! -d "$theme_dir" ]; then
    echo "warning: $theme_dir not found, skipped" >&2
    return
  fi
  if [ -f "$theme_dir/Dockerfile" ]; then
    sed -i "s#FROM ghcr\.io/g10f/sso:.*#FROM ghcr.io/g10f/sso:$new#" "$theme_dir/Dockerfile"
  fi
  if [ -f "$theme_dir/$package/__init__.py" ]; then
    sed -i "s/^__version__ = .*/__version__ = '$new'/" "$theme_dir/$package/__init__.py"
  fi
  echo "updated $theme_dir (not committed)"
}

# theme repositories are found by their name: ../sso-<name>-theme contains the package sso_<name>_theme
for theme_dir in ../sso-*-theme; do
  if [ ! -d "$theme_dir" ]; then
    continue  # no theme repository checked out
  fi
  name=${theme_dir#../sso-}  # ../sso-dwbn-theme -> dwbn-theme
  name=${name%-theme}        # dwbn-theme -> dwbn
  update_theme "$theme_dir" "sso_${name}_theme"
done

echo "Created release $new (previous version: $current)."
echo "Push it to start the build and deployment:"
echo "  git push --follow-tags origin $branch"
