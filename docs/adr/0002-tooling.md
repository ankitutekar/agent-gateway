# 2. Project tooling and CI

- **Status:** Accepted
- **Date:** 2026-10-13

## Context

Code in this repository is largely written by coding agents. Quality gates from the first commit keep that code honest, and the same checks must run locally and in CI so a green laptop means a green pipeline.

## Decisions

| Concern | Choice | Alternatives considered | Why |
|---|---|---|---|
| Language | Python 3.12 | Go, TypeScript | Fastest to build in; agent SDKs and MCP are Python-first |
| Package manager | uv, with `uv.lock` committed | Poetry, pip-tools | Fast, manages the Python version too, one tool |
| Formatter and linter | ruff (format + lint, including `S` security rules) | black + flake8 + isort | One fast tool replacing three |
| Type checker | pyright, strict mode | mypy | Faster, checks unannotated code, same engine as the VS Code editor (Pylance) |
| Tests | pytest | unittest | The standard |
| Local runner | Makefile (`make check` = what CI runs) | pre-commit hooks | Smallest setup; pre-commit can be added later |
| Secret scanning | gitleaks in CI **and** GitHub push protection | either alone | Push protection stops known token formats before they reach GitHub; gitleaks catches more patterns and scans full history |
| Dependency updates | Dependabot, weekly, for uv and GitHub Actions | Renovate | Built into GitHub, no extra app |

Supporting rules:

- Dev tools are pinned to exact versions in `pyproject.toml`; the lockfile pins everything else.
- GitHub Actions are pinned to commit SHAs (tag in a comment), so a moved or compromised tag cannot change what runs. Dependabot keeps the pins current.
- CI runs on a pinned runner image (`ubuntu-24.04`, not `ubuntu-latest`), upgraded deliberately rather than when GitHub moves the label.
- Workflows run with `contents: read` only, and checkout does not persist credentials.
- Line endings are normalised to LF (`.gitattributes`), since CI and containers run on Linux.

## Deferred

Which checks *block* a merge (branch protection) is not decided yet. Until it is, CI runs all checks but nothing is enforced on `main`.

## Consequences

- `make` must be installed on Windows (done via winget, `ezwinports.make`).
- Strict pyright will be noisy with poorly typed libraries; suppressions must be targeted and commented, never a global relaxation.

## Revisit if

Strict typing slows work disproportionately, or Astral's `ty` matures enough to replace pyright inside the same toolchain.
