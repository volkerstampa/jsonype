#!/usr/bin/env bash

set -euo pipefail

if grep --extended-regexp --line-number --color '^from jsonype import' jsonype/*.py
then
  echo -"-> Check import statements listed above"
fi

if grep --perl-regexp --line-number --color --regexp '^from jsonype\S+ import (?!.*(_co|_contra)).*$' tests/jsonype/*.py
then
  echo -"-> Check import statements listed above"
fi

