#!/bin/bash -e

set -x
flake8 aioreq
flake8 tests
mypy aioreq
black --check --diff .
isort --check --diff .