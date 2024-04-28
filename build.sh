#!/usr/bin/env -S bash -eu -o pipefail

"$(dirname "$(readlink --canonicalize-existing "$(which poetry)")")/python" -m setuptools_scm --force-write-version-files
poetry build
(cd docs && make clean html)
