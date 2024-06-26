#!/usr/bin/env -S bash -eu -o pipefail

pylama
ruff check
mypy
pytest
[ -f jsonype/_version.py ] || echo "__version__='0'" > jsonype/_version.py
(cd docs && make doctest)
