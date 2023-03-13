#!/bin/bash -e

set -x

python -m venv venv
pip install --no-cache-dir -r requirements.txt