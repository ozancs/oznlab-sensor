#!/bin/bash
# release.sh v0.9.10 -> tags the current commit and pushes main + tag.
# Moonraker's update manager only follows tags, so a tag that points at an older commit ships old
# code no matter what main says. This script refuses the usual ways that happens.
set -e
TAG="$1"
[ -n "$TAG" ] || { echo "usage: ./release.sh v0.9.10"; exit 1; }
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$REPO"

VER=$(grep -o '^VERSION = "[^"]*"' oznlab_sensor.py | cut -d'"' -f2)
[ "v$VER" = "$TAG" ] || { echo "oznlab_sensor.py says VERSION = \"$VER\", tag is $TAG - fix one of them"; exit 1; }
grep -q "^## $TAG" CHANGELOG.md || { echo "CHANGELOG.md has no '## $TAG' entry"; exit 1; }
[ "$(git branch --show-current)" = "main" ] || { echo "not on main"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "uncommitted changes - commit them first:"; git status --short; exit 1; }
git fetch -q origin
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "main is not pushed (or behind origin) - git push first"; exit 1; }
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    [ "$(git rev-parse "$TAG^{commit}")" = "$(git rev-parse HEAD)" ] || {
        echo "$TAG already exists and points at $(git rev-parse --short "$TAG^{commit}"), not HEAD. Delete it first:"
        echo "  git tag -d $TAG && git push origin :refs/tags/$TAG"; exit 1; }
else
    git tag "$TAG"
fi
git push origin "$TAG"
REMOTE=$(git ls-remote --tags origin "refs/tags/$TAG" | cut -f1)
[ "$REMOTE" = "$(git rev-parse HEAD)" ] || { echo "the tag on GitHub ($REMOTE) is not HEAD - check by hand"; exit 1; }
echo "$TAG = $(git rev-parse --short HEAD) on GitHub. Users get it with the Update button."
