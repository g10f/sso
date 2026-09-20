#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?usage: ./set-version.sh <version>, e.g. ./set-version.sh 5.4.5}"

sed -i "s/__version__ =.*/__version__ = '${VERSION}'/" apps/sso/__init__.py

# update any sibling theme repos that are checked out next to this one.
# they are auto-discovered by the naming convention ../sso-<name>-theme with an
# inner package sso_<name>_theme, so no theme names are hard-coded here.
# the directory name alone is not enough: only a theme whose Dockerfile is built
# FROM ghcr.io/g10f/sso follows our version line, others have their own.
for dir in ../sso-*-theme; do
  [ -d "$dir" ] || continue
  grep -q "^FROM ghcr\.io/g10f/sso:" "$dir/Dockerfile" 2>/dev/null || continue
  name="${dir#../sso-}"; name="${name%-theme}"
  sed -i "s#FROM ghcr\.io/g10f/sso:.*#FROM ghcr.io/g10f/sso:${VERSION}#" "$dir/Dockerfile"
  [ -f "$dir/sso_${name}_theme/__init__.py" ] && \
    sed -i "s/__version__ =.*/__version__ = '${VERSION}'/" "$dir/sso_${name}_theme/__init__.py"
done

git add apps/sso/__init__.py
git commit -m "release ${VERSION}"
# annotated tag so that "git push --follow-tags" pushes it together with the commit
git tag -a "${VERSION}" -m "release ${VERSION}"

echo "tagged ${VERSION}. push commit and tag with: git push --follow-tags"
