SHELL := /bin/bash

PYTHON ?= .venv/bin/python
UV ?= uv

.PHONY: install install-dev test test-live clean

install:
	$(UV) pip install --python $(PYTHON) -e .

install-dev:
	$(UV) pip install --python $(PYTHON) -e '.[dev]'

test:
	$(PYTHON) -m pytest

test-live:
	$(PYTHON) -m pytest -q --tb=line -m live_cms tests/live

clean:
	@rm -rf build dist .pytest_cache .ruff_cache .coverage htmlcov
	@find . -path './data' -prune -o -path './.venv' -prune -o \
		-type d \( -name '__pycache__' -o -name '*.egg-info' \) \
		-prune -exec rm -rf {} +
