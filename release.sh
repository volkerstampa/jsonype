#!/usr/bin/env bash

set -eu -o pipefail

ProjectRoot="$(readlink --canonicalize-existing "$(dirname "$0")" 2>/dev/null)"

version="${1:?Provide non-empty version string as first arg}"

Readme="README.md"
Changelog="CHANGELOG.md"

checkVersion() {
  local -r version="$1"

  if [[ ! "$version" =~ ^[0-9]+(\.[0-9]+){2}$ ]]
  then
    echo "Version must be a version number in the format #.#.# but is '$version'" >&2
    return 1
  fi
}

checkGitPreconditions() {
  if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]
  then
    echo Switch to main first >&2
    return 1
  fi
  for repo in $(git remote)
  do
    git fetch --prune "$repo"
    if  [ "$(git merge-base main "$repo/main")" != "$(git rev-parse "$repo/main")" ]
    then
      echo $repo/main is ahead of main or diverged >&2
      return 1
    fi
  done
}

replaceNextInChangelog() {
  local -r version="$1" file="$2"

  sed --in-place "s/^## next$/## $version/" "$file"
}

linkToVersionedDocumentationInReadme() {
  local -r version="$1" file="$2"

  sed --in-place \
    "s!\[documentation\](https://jsonype.readthedocs.io)![documentation](https://jsonype.readthedocs.io/v$version/)!" \
    "$file"
}

commit() {
  local -r message="$1"
  shift

  for file in "$@"
  do
    if git diff --exit-code --no-patch "$file"
    then
      echo "'$file' has no changes. Aborting." >&2
      return 1
    fi
  done
  git add "$@"
  git commit -m "$message"
  git show HEAD
}

tag() {
  local -r version="$1"

  git tag "v$version"
}

addNextToChangelog() {
  local -r version="$1" file="$2"

  sed --in-place --regexp-extended 's/^(## '"$version"'$)/## next\n\n\1/' "$file"
}

linkToLatestDocumentationInReadme() {
  local -r version="$1" file="$2"

  sed --in-place \
    "s!\[documentation\](https://jsonype.readthedocs.io/v$version/)![documentation](https://jsonype.readthedocs.io)!" \
    "$file"
}

cd "$ProjectRoot"
checkVersion "$version"
checkGitPreconditions
echo "Use '$version' in $Readme and $Changelog"
replaceNextInChangelog "$version" "$Changelog"
linkToVersionedDocumentationInReadme "$version" "$Readme"
commit "Set version to $version" "$Changelog" "$Readme"
echo "Tag '$version'"
tag "$version"
echo "Switch back to next/latest"
addNextToChangelog "$version" "$Changelog"
linkToLatestDocumentationInReadme "$version" "$Readme"
commit "Prepare next release" "$Changelog" "$Readme"
