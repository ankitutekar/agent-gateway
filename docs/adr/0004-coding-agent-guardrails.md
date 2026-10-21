# 4. Guardrails for the coding agent

- **Status:** Accepted
- **Date:** 2026-10-21

## Context

Most code here is written by a coding agent (Claude Code) running on the maintainer's machine, as the maintainer. It inherits whatever the maintainer is signed in to: the Azure CLI session, the GitHub CLI token, every file the user can read. Until now the only thing keeping it away from Azure, secrets and repository settings was a paragraph in the workspace instructions (`CLAUDE.md`). That is a control enforced in the prompt, which this project's first principle rules out.

## Decision

A **PreToolUse hook** checks every shell, read and edit call the agent makes before it runs, and sorts it into one of three categories:

| Category | Effect | Examples |
|---|---|---|
| Blocked | The call never runs, whoever approves; the human runs it | `az login`, access tokens, `az` changes, `terraform apply/destroy/import/state/output/show`, reading or writing `*.tfstate`, `*.tfvars`, `backend.hcl`, `.env`, `~/.azure`, `gh auth/secret/variable/ruleset`, `gh pr merge`, push to `main`, force-push, `--no-verify`, dumping environment variables |
| Ask | The human gets a prompt, in every permission mode including auto | `az ... list/show`, `terraform plan`, `terraform init` with the real backend, `git push` of a feature branch, `gh pr create`, `gh api` reads, installing software, `uv add`, edits to the guardrails themselves |
| Normal | Claude Code's usual permission flow | `make check`, `terraform fmt/validate`, local git, editing code |

- **Where:** `.claude/hooks/guard.py` and `.claude/settings.json` in this repository, so the guard is versioned, reviewed through PRs and tested by `make check` like any other code. Sessions start in the repository so the settings load.
- **How:** a standard-library Python script. It splits chained commands (`&&`, `;`, pipes, `$(...)`), looks through wrappers (`bash -c`, `pwsh -Command`, `env`, `xargs`, `uv run`, `eval`), reads shell scripts before they run, and skips heredoc bodies that are only data (commit messages). The most severe decision wins.
- **Fails closed:** if the script crashes or cannot parse its input, the call is denied (`onFailure: block`).
- **Second layer:** permission deny rules for the same secret paths, so one bug in the script does not open everything.
- **Self-protection:** edits to `.claude/settings*.json` and `.claude/hooks/` ask, so the agent cannot quietly switch off its own guard. Mentioning `disableAllHooks` in a shell command is blocked.
- **Change to the rules:** reading Azure (`az ... list/show`, `terraform plan`) moves from "human runs" to "ask". The human still sees and approves every such call, and the output stays on the machine. `CLAUDE.md` is updated to match.

## Alternatives considered

- **Instructions only (`CLAUDE.md`).** Already in place; not a control.
- **Permission rules only** (`permissions.deny/ask` in settings). Good for file paths, but command rules match on prefixes, so `cd x && az login` or `bash -c "az login"` are hard to catch. Kept as the second layer.
- **An allowlist (deny everything not listed).** Safer in principle, but most everyday commands would need a prompt, which trains the human to approve without reading. Revisit if the blocklist keeps missing things.
- **OS-level sandbox** (Claude Code's sandbox, hiding `~/.azure` and tokens from every command). The only option that is a real boundary, since it does not depend on recognising commands. On Windows it needs extra setup; deferred.

## Consequences

- The rules in `CLAUDE.md` are enforced in code, with a test for each rule (`tests/test_guard.py`).
- **It is a guardrail, not a boundary.** A command disguised well enough gets past a text check: Python code that calls `subprocess`, a string built at runtime, a downloaded tool. It stops mistakes and drift; it does not stop a determined adversary. The same limit applies to the gateway's own argument checks later, which is why the gateway's real controls are identity and credentials the agent never holds.
- The agent still runs as the maintainer. Signing out of Azure when not working (`az logout`) limits what any bypass could reach.
- Hooks do not apply to commands the human runs with `!`.
- Every shell call now starts a small Python process; the cost is tens of milliseconds.

## Revisit if

A blocked command gets through in practice, prompts become so frequent that approving turns automatic, or the sandbox becomes easy to run on Windows.
