#!/usr/bin/env -S bash -eu -o pipefail

pylama
ruff check
pytest
