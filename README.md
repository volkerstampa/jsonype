# jsont

## Development

### Prerequisites

- python 3.11:
  Can be installed with [pyenv](https://github.com/pyenv/pyenv):
    - pyenv install $(pyenv install -l | grep "^\s*3.11" | tail -1)
- [pipenv](https://pipenv.pypa.io/en/latest/)
- [make](https://www.gnu.org/software/make/) for building documentation

### Setup virtual env

```bash
# in project root execute
pipenv shell
pipenv install --dev
```

All commands below assume that they are execute in a corresponding
virtual environment (e.g. in a shell started by `pipenv shell`) and the
current directory is set to the project's root folder.

### Run tests

```bash
./test.sh
```

### Run checks

```bash
pylama
```

### Build package

### Documentation

#### Build

```bash
cd docs
make
```

#### Add new modules/packages

```bash
cd docs
sphinx-apidoc -o source ../jsont/
```




