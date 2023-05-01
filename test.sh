#!/usr/bin/env bash

set -eu -o pipefail

ProjectRoot="$(cd "$(dirname "$0")" && pwd -P)"

python -m unittest discover --start-directory "$ProjectRoot"/tests --top-level-directory "$ProjectRoot"