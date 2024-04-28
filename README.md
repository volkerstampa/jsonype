# jsont

## Usage

See [documentation](https://jsont.readthedocs.io).

## Development

### Prerequisites

- python >= 3.11:
  Can be installed with [pyenv](https://github.com/pyenv/pyenv):
  - pyenv install 3.11
- [Poetry](https://python-poetry.org/) >=1.2
  On Ubuntu can be installed with `sudo apt install python3-poetry`. See
  [Poetry's documentation](https://python-poetry.org/docs/#installation)
  for alternative installation options.
- [make](https://www.gnu.org/software/make/) for building documentation

### Setup virtual env

```bash
poetry self add poetry-setuptools-scm-plugin@latest
poetry install
poetry shell
```

All commands below assume that they are executed in a corresponding
virtual environment (e.g. in a shell started by `poetry shell`) and the
current directory is set to the project's root folder.

### Run checks

```bash
./check.sh
```

### Run build

```bash
./build.sh
```

### Documentation

#### Add new modules/packages

```bash
cd docs
sphinx-apidoc -o source ../jsont/
```
