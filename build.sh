#!/usr/bin/env bash

set -eu -o pipefail

uv build
(cd docs && make clean html)
