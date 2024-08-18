#!/usr/bin/env bash

set -eu -o pipefail

poetrysPython() {
    local poetryAbsolutePath

    if ! poetryAbsolutePath="$(readlink --canonicalize-existing "$(which poetry)" 2>/dev/null)"
    then
        # fallback for Mac/BSD without gnu-utils
        poetryAbsolutePath="$(stat -f %R "$(which poetry)")"
    fi
    "$(dirname "$poetryAbsolutePath")/python" "$@"
}

# expects that poetry-setuptools-scm-plugin is added to poetry
# with: poetry self add poetry-setuptools-scm-plugin
poetrysPython -m setuptools_scm --force-write-version-files
poetry install
poetry build
(cd docs && make clean html)
