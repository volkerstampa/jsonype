#!/usr/bin/env -S bash -eu -o pipefail

PypiRepository="$1"
if [[ "${2-}" = "--build-only" ]]
then
  BuildOnly=true
else
  BuildOnly=false
fi

uv run ./build.sh
PublishArgs=""
"$BuildOnly" && PublishArgs="--dry-run"
if [[ "$PypiRepository" == "testpypi" ]]
then
  uv publish $PublishArgs --index "$PypiRepository"
else
  uv publish $PublishArgs
fi
