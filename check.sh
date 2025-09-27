#!/usr/bin/env -S bash -eu -o pipefail

fix=true
spellCheck=true
while [ $# -gt 0 ]
do
  case "$1" in
    --no-fix)
      fix=false
      shift
      ;;
    --no-spellcheck)
      spellCheck=false
      shift
      ;;
  esac
done

if $fix
then
  ruffCheckArgs=( --fix --unsafe-fixes --show-fixes )
  isortArgs=()
else
  ruffCheckArgs=()
  isortArgs=( --check )
fi
if $spellCheck
then
  pylintArgs=()
else
  pylintArgs=( --disable spelling,useless-suppression )
fi

set -x
ruff check "${ruffCheckArgs[@]}"
pycodestyle
radon -v cc raw mi hal
vulture
isort "${isortArgs[@]}" .
flake8
pylint "${pylintArgs[@]}" .
mypy
pytest
set +x
[ -f jsonype/_version.py ] || echo "__version__='0'" > jsonype/_version.py
(cd docs && make doctest)
