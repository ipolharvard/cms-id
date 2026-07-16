SHELL := /bin/bash

PYTHON ?= .venv/bin/python
UV ?= uv

.PHONY: install install-dev install-docs test test-live docs docs-serve clean

install:
	$(UV) pip install --python $(PYTHON) -e .

install-dev:
	$(UV) pip install --python $(PYTHON) -e '.[dev]'

install-docs:
	$(UV) pip install --python $(PYTHON) -e '.[docs]'

test:
	$(PYTHON) -m pytest

test-live:
	$(PYTHON) -m pytest -q --tb=line -m live_cms tests/live

docs:
	$(PYTHON) -m mkdocs build --strict

docs-serve:
	$(PYTHON) -m mkdocs serve

clean:
	@rm -rf build dist site .pytest_cache .ruff_cache .coverage htmlcov
	@find . -path './data' -prune -o -path './.venv' -prune -o \
		-type d \( -name '__pycache__' -o -name '*.egg-info' \) \
		-prune -exec rm -rf {} +
