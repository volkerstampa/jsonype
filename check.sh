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
  # Unfortunately we cannot make spellcheck the default and just disable it here on demand
  # Problems is that a spelling-dict in the config file that does not exist in an environment
  # without enchant makes it impossible to start pylint event when the spelling-dict is overwritten
  # on commandline.
  # its a single ,-separated arg
  # shellcheck disable=SC2054
  pylintArgs=( --spelling-dict en --enable useless-suppression )
else
  pylintArgs=( )
fi

set -x
ruff check "${ruffCheckArgs[@]}"
pycodestyle
vulture
isort "${isortArgs[@]}" .
flake8
pylint "${pylintArgs[@]}" .
mypy
pytest
set +x
[ -f jsonype/_version.py ] || echo "__version__='0'" > jsonype/_version.py
(cd docs && make doctest)
