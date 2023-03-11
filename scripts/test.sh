#!/bin/sh -e

set -x
./scripts/check.sh

pytest --doctest-modules --doctest-glob="*md" docs
pytest