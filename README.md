# jsonype

## Usage

See [documentation](https://jsonype.readthedocs.io).

## Similar tools

- [typedload](https://github.com/ltworf/typedload) is also a package to 
  "Load and dump json-like data into typed data structures in Python3". It uses 
  a less permissive license.
- [Pydantic](https://docs.pydantic.dev) is a widely used data validation library for Python.
  It is often used for converting to and from JSON, but offers much more than that. Unlike in case of
  jsonype classes that should be converted from/to JSON need to inherit from a base class (`BaseModel`).

## Development

### Prerequisites

- Python >= 3.11:
  Can be installed with [pyenv](https://github.com/pyenv/pyenv):
  - `pyenv install 3.11`
- [Poetry](https://python-poetry.org/) >=1.2: Can be installed with [pipx](https://pipx.pypa.io/):
  - `pipx install poetry`

  See [Poetry's documentation](https://python-poetry.org/docs/#installation)
  for alternative installation options, but make sure that poetry plugins can be installed.
- [make](https://www.gnu.org/software/make/) for building documentation
- enchant for spell checking with 
- [Pylint](https://pylint.readthedocs.io/en/stable/user_guide/installation/command_line_installation.html#command-line-installation)
  including a dictionary for `en`. In Debian based systems this can be installed with:
  - `sudo apt install enchant-2 aspell-en`

### Setup virtual env

```bash
poetry self add poetry-setuptools-scm-plugin@latest
poetry install
poetry self add poetry-plugin-shell # only required for poetry >= 2
poetry shell
```

All commands below assume that they are executed in a corresponding
virtual environment (e.g. in a shell started by `poetry shell`) and the
current directory is set to the project's root folder.

### Run checks

```bash
./check.sh
```

This does not only check, but it also applies fixes that can be applied automatically.
To run checks only:

```bash
./check.sh --no-fix
```

Checks include spell checking by default which requires 
[`enchant`](https://rrthomas.github.io/enchant/) to be installed. If this is not available
you can run:

```bash
./check.sh --no-spellcheck
```

### Run build

```bash
./build.sh
```

### Release

```bash
./release.sh [#.#.#]
git push [GITHUB-REPO] v[#.#.#]
```

### Documentation

#### Add new modules/packages

```bash
cd docs
sphinx-apidoc -o source ../jsonype/
```
