.PHONY: help install fmt lint typecheck test check tf-check up down eval

TF_ROOTS := infra/bootstrap

help:
	@echo "install    install dependencies (uv sync)"
	@echo "fmt        format code and apply safe lint fixes"
	@echo "lint       check formatting and lint"
	@echo "typecheck  run pyright (strict)"
	@echo "test       run tests"
	@echo "tf-check   terraform fmt check + validate (no Azure access needed)"
	@echo "check      lint + typecheck + test + tf-check (what CI runs)"

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

tf-check:
	terraform fmt -check -recursive infra
	for root in $(TF_ROOTS); do \
		terraform -chdir=$$root init -backend=false -input=false >/dev/null && \
		terraform -chdir=$$root validate || exit 1; \
	done

check: lint typecheck test tf-check

up down eval:
	@echo "'$@' is not implemented yet"
