.PHONY: help install fmt lint typecheck test check up down eval

help:
	@echo "install    install dependencies (uv sync)"
	@echo "fmt        format code and apply safe lint fixes"
	@echo "lint       check formatting and lint"
	@echo "typecheck  run pyright (strict)"
	@echo "test       run tests"
	@echo "check      lint + typecheck + test (what CI runs)"

install:
	uv sync --locked

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run pyright

test:
	uv run pytest

check: lint typecheck test

up down eval:
	@echo "'$@' is not implemented yet"
