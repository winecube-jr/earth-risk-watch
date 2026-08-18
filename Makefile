.PHONY: install test lint typecheck security check demo

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy src

security:
	bandit -q -r src

check: lint typecheck security test

demo:
	earth-risk demo --output data/products/demo
