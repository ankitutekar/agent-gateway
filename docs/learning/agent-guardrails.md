# Agent guardrails

## Prompt rules vs enforced rules · chore (before 0.5)

A rule written in the agent's instructions (`CLAUDE.md`) only holds while the model chooses to follow it. A rule enforced by code outside the model holds whatever the model decides. This is the project's first principle ("enforce in code, never in the prompt") applied to the coding agent that builds the project.

## Hooks · chore (before 0.5)

Claude Code runs a hook script at fixed points. A **PreToolUse** hook runs before every tool call, gets the call as JSON on stdin (`{"tool_name": "Bash", "tool_input": {"command": "..."}}`) and can answer `deny` (the call never runs) or `ask` (the human gets a prompt, even in auto mode). Printing nothing leaves the normal permission flow in charge. The agent cannot skip a hook; it only sees the refusal.

It is the same pattern as the gateway: the agent proposes an action, a policy point outside the agent decides, and the decision carries a reason.

## Blocklists and why they leak · chore (before 0.5)

The guard recognises dangerous commands by their text. Text can be disguised: `bash -c "az login"`, `$(...)`, a script file, Python calling `subprocess`. The guard looks through the common wrappers, but no text check catches everything. So a blocklist is a **guardrail** (stops mistakes and drift), not a **boundary** (stops an adversary). A boundary removes the capability instead: a sandbox that hides the credential files, or an identity that holds no rights.

## Fail closed · chore (before 0.5)

When a security check itself breaks, it can let the action through (fail open) or block it (fail closed). The guard fails closed: a crash or unreadable input means deny. Failing open would mean any bug in the guard silently disables it.

## Defence in depth · chore (before 0.5)

Secret file paths are blocked twice: by the hook and by Claude Code's built-in permission deny rules. Either layer can have a bug; both would have to fail together.

## The agent runs as you · chore (before 0.5)

The coding agent runs under your Windows account, so it inherits your `az login` session and `gh` token. That is why reading `~/.azure` and `~/.config/gh` is blocked, and why signing out of Azure when not working shrinks what any bypass could reach. Phase 3 solves the same problem for the project's own agents by giving each its own narrow identity.

## Guarding the guard · chore (before 0.5)

If the agent can edit its own guard, the guard is advisory. Edits to `.claude/settings*.json` and `.claude/hooks/` ask for approval, and `disableAllHooks` in a command is blocked.
