#!/usr/bin/env -S bash -eu -o pipefail

ruffCheckArgs=( --fix --unsafe-fixes --show-fixes )
isortArgs=()

# Unfortunately we cannot make spellcheck the default and just disable it here on demand
# Problem is that a spelling-dict in the config file that does not exist in an environment
# without enchant makes it impossible to start pylint even when the spelling-dict is overwritten
# on commandline.
# it's a single ,-separated arg
# shellcheck disable=SC2054
pylintArgs=( --spelling-dict en --enable useless-suppression )

pytestArgs=( --cov-report html )
while [ $# -gt 0 ]
do
  case "$1" in
    --no-fix)
      ruffCheckArgs=()
      isortArgs=( --check )
      shift
      ;;
    --no-spellcheck)
      pylintArgs=()
      shift
      ;;
    --cov)
      pytestArgs=( --cov-report "$2" )
      shift 2
      ;;
    --no-cov)
      pytestArgs=( --no-cov )
      shift
      ;;
  esac
done

set -x
ruff check "${ruffCheckArgs[@]}"
vulture
isort "${isortArgs[@]}" .
flake8
pylint "${pylintArgs[@]}" .
mypy
pytest "${pytestArgs[@]}"
set +x
[ -f jsonype/_version.py ] || echo "__version__='0'" > jsonype/_version.py
(cd docs && make doctest)
