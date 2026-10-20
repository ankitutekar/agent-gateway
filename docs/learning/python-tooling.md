# Python tooling

## uv and the lockfile · step 0.2

`pyproject.toml` says which packages are wanted; `uv.lock` records the exact versions resolved, so every install (laptop or CI) is identical. uv also installs the Python version itself, separate from any system or Anaconda Python.

## ruff · step 0.2

Formatter and linter in one. Formatting removes style debates; linting catches likely bugs, and its `S` rules flag security smells (hard-coded passwords, `eval`, insecure temp files).

## Type checking (pyright, strict) · step 0.2

Python ignores type hints at runtime; a type checker reads them and finds mismatches before the code runs. Strict mode also complains about code it cannot fully understand, which keeps agent-written code honest. pyright is also the engine behind VS Code's Pylance, so the editor and CI agree.

## Local checks · step 0.2

`make check` runs the same commands as CI, so a green laptop predicts a green pipeline. Run it before every commit.
