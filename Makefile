SHELL := /bin/bash

PYTHON ?= .venv/bin/python
UV ?= uv

.PHONY: install install-dev install-docs test test-live test-live-catalog \
	test-live-current test-live-historical test-live-exhaustive docs docs-serve clean

install:
	$(UV) pip install --python $(PYTHON) -e .

install-dev:
	$(UV) pip install --python $(PYTHON) -e '.[dev]'

install-docs:
	$(UV) pip install --python $(PYTHON) -e '.[docs]'

test:
	$(PYTHON) -m pytest

test-live:
	$(PYTHON) -m pytest -q --tb=line \
		-m 'live_catalog or live_current or live_historical' tests/live

test-live-catalog:
	$(PYTHON) -m pytest -q --tb=line -m live_catalog tests/live

test-live-current:
	$(PYTHON) -m pytest -q --tb=line -m live_current tests/live

test-live-historical:
	$(PYTHON) -m pytest -q --tb=line -m live_historical tests/live

test-live-exhaustive:
	$(PYTHON) -m pytest -q --tb=line -m live_exhaustive tests/live

docs:
	$(PYTHON) -m mkdocs build --strict

docs-serve:
	$(PYTHON) -m mkdocs serve

clean:
	@rm -rf build dist site .pytest_cache .ruff_cache .coverage htmlcov
	@find . -path './data' -prune -o -path './.venv' -prune -o \
		-type d \( -name '__pycache__' -o -name '*.egg-info' \) \
		-prune -exec rm -rf {} +
