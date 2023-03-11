#!/bin/sh -e

set -x

python -m venv venv
pip install --no-cache-dir ".[dev]"