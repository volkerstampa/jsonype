# jsont

TODO: - add scripts for checking (mypy, tests, other linters)
Check pylama https://github.com/klen/pylama
or https://realpython.com/python-code-quality/

## development

### prerequisites

- python 3.11:
  Can be installed with [pyenv](https://github.com/pyenv/pyenv):
    - pyenv install $(pyenv install -l | grep "^\s*3.11" | tail -1)
- [pipenv](https://pipenv.pypa.io/en/latest/)

### setup virtual env

```bash
# in project root execute
pipenv shell
pipenv install --dev
```

All commands below assume that they are execute in a corresponding
virtual environment (e.g. in a shell started by `pipenv shell`) and the
current directory is set to the project's root folder.

### run tests

```bash
pytest
```

### run checks

```bash
mypy
```

### build package

