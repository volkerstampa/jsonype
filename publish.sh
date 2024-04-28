#!/usr/bin/env -S bash -eu -o pipefail

PypiRepository="$1"
if [[ "${2-}" = "--build-only" ]]
then
  BuildOnly=true
else
  BuildOnly=false
fi

poetry self add poetry-setuptools-scm-plugin
if [[ "$PypiRepository" == "testpypi" ]]
then
  poetry config repositories.testpypi https://test.pypi.org/legacy/
fi
poetry config pypi-token."$PypiRepository" "${PYPI_TOKEN}"
poetry run ./build.sh
"$BuildOnly" && exit 0
if [[ "$PypiRepository" == "testpypi" ]]
then
  poetry --no-interaction publish --repository "$PypiRepository"
else
  poetry --no-interaction publish
fi
