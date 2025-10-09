#!/usr/bin/env -S bash -eu -o pipefail

PypiRepository="$1"
if [[ "${2-}" = "--build-only" ]]
then
  BuildOnly=true
else
  BuildOnly=false
fi

uv run ./build.sh
PublishArgs=()
"$BuildOnly" && PublishArgs+=( "--dry-run" )
[[ "$PypiRepository" == "testpypi" ]] && PublishArgs+=( --index "$PypiRepository" )
uv publish "${PublishArgs[@]}"
