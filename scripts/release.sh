#!/bin/sh -e

set -x

VERSION=$(hatch version patch)
NEW_VERSION=$(python -c "print('''$VERSION'''.split('New: ')[1], end='')")
echo $NEW_VERSION

git add aioreq/__init__.py
git commit -m "New version commit"
git tag "v$NEW_VERSION"
hatch build
hatch publish
