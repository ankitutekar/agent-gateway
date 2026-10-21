"""PreToolUse hook: keeps the coding agent away from Azure, secrets and repository controls.

Claude Code runs this script before every matching tool call and sends the call as JSON
on stdin. The script prints nothing (the normal permission flow applies) or a decision:

- deny: the call never runs, whatever anyone approves; the human runs it instead.
- ask:  the human approves or rejects it in a prompt, even in auto mode.

The rules come from CLAUDE.md ("Who runs what"); the reasoning is in docs/adr/0004.

This is a guardrail against mistakes and drift, not a security boundary: a determined
agent can always disguise a shell command (for example inside a Python script). It fails
closed: if the script itself breaks, the call is denied.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

Kind = Literal["deny", "ask"]


@dataclass(frozen=True)
class Decision:
    kind: Kind
    reason: str


Rule = Callable[[list[str]], Decision | None]


def _deny(reason: str) -> Decision:
    return Decision("deny", reason)


def _ask(reason: str) -> Decision:
    return Decision("ask", reason)


def _worst(decisions: Iterable[Decision | None]) -> Decision | None:
    """Deny beats ask beats no opinion."""
    worst: Decision | None = None
    for decision in decisions:
        if decision is None:
            continue
        if worst is None or (decision.kind == "deny" and worst.kind == "ask"):
            worst = decision
    return worst


# --- Paths -------------------------------------------------------------------------------

# Files that hold, or may hold, secrets. Matched against lowercased text with "/" separators.
_SECRET_PATHS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\.tfstate"), "Terraform state"),
    (re.compile(r"\.tfplan\b"), "a Terraform plan file"),
    (re.compile(r"\.tfvars(?!\.example)"), "Terraform variables"),
    (re.compile(r"backend\.hcl(?!\.example)"), "Terraform backend settings"),
    (re.compile(r"(?<![\w.-])\.env(?!\.example)(?:\.[\w-]+)*(?![\w-])"), "a .env file"),
    (re.compile(r"(?<=\w)\.(?:pem|pfx|p12|key)\b"), "a key or certificate file"),
    (re.compile(r"(?<![\w-])\.azure(?![\w-])"), "the Azure CLI login cache"),
    (re.compile(r"\.config/gh\b|gh/hosts\.yml"), "the GitHub CLI login"),
    (
        re.compile(r"\.terraform\.d/credentials|terraformrc\b|(?<![\w.-])terraform\.rc\b"),
        "Terraform credentials",
    ),
    (re.compile(r"\.git-credentials|(?<![\w.-])[._]netrc\b"), "stored git credentials"),
    (re.compile(r"\.ssh/|\bid_(?:rsa|ed25519|ecdsa|dsa)\b"), "SSH keys"),
    (re.compile(r"/proc/[^/\s]+/environ"), "process environment variables"),
]

# The agent's own guardrails: settings files (which can disable hooks) and the hook scripts.
_GUARD_FILES = re.compile(r"\.claude/(?:settings[^/\s]*\.json|hooks\b)")


def _normalize(text: str) -> str:
    return text.replace("\\", "/").lower()


def _secret_label(text: str) -> str | None:
    lowered = _normalize(text)
    for pattern, label in _SECRET_PATHS:
        if pattern.search(lowered):
            return label
    return None


def check_path(path: str, *, write: bool) -> Decision | None:
    """Rules for file tools (Read, Edit, Write, NotebookEdit, Grep)."""
    label = _secret_label(path)
    if label:
        return _deny(f"{path} is {label}; the agent never reads or writes secret files.")
    if write and _GUARD_FILES.search(_normalize(path)):
        return _ask(f"Changes the agent's own guardrails ({path}).")
    return None


# --- Shell parsing -----------------------------------------------------------------------

_SHELLS = {"bash", "sh", "zsh", "dash", "pwsh", "powershell", "cmd"}
_POWERSHELLS = {"pwsh", "powershell"}
_SCRIPT_SUFFIXES = (".sh", ".bash", ".ps1", ".bat", ".cmd")
_PROGRAM_SUFFIXES = (".exe", ".cmd", ".bat", ".com", ".ps1", ".sh")
_POWERSHELL_VALUE_FLAGS = {
    "-executionpolicy",
    "-ep",
    "-workingdirectory",
    "-wd",
    "-outputformat",
    "-of",
    "-inputformat",
    "-if",
    "-windowstyle",
    "-w",
    "-configurationname",
    "-settingsfile",
}
_MAX_DEPTH = 5
_MAX_SCRIPT_BYTES = 200_000

# Commands that run another command: the guard looks through them.
_WRAPPERS = {
    "sudo",
    "command",
    "exec",
    "time",
    "nohup",
    "nice",
    "xargs",
    "watch",
    "timeout",
    "call",
    "start",
    "start-process",
    "&",
    ".",
    "noglob",
    "builtin",
}

_HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_]\w*)\1")
_SUBSTITUTION = re.compile(r"\$\(((?:[^()]|\([^()]*\))*)\)|`([^`]*)`")
_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
_SECRET_ENV_VAR = re.compile(
    r"\$(?:env:)?\{?[a-z_0-9]*(?:key|token|secret|password|passwd|credential)[a-z_0-9]*"
    r"|%[a-z_0-9]*(?:key|token|secret|password|credential)[a-z_0-9]*%"
    r"|\[environment\]::getenvironmentvariables?"
)
# Values of these flags are free text (commit messages, PR bodies), not paths.
_MESSAGE_FLAGS = {"-m", "--message", "-b", "--body", "-t", "--title", "--notes"}


def _program_name(token: str) -> str:
    name = token.strip("'\"").replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in _PROGRAM_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _strip_heredocs(command: str) -> tuple[str, list[str]]:
    """Remove here-document bodies; return the text and the bodies fed to a shell.

    A heredoc body is data (often a commit message) unless a shell reads it as commands.
    """
    out: list[str] = []
    shell_bodies: list[str] = []
    pos = 0
    while (match := _HEREDOC.search(command, pos)) is not None:
        line_end = command.find("\n", match.end())
        if line_end == -1:
            break
        delimiter = re.compile(rf"^[ \t]*{re.escape(match.group(2))}[ \t]*$", re.MULTILINE)
        end = delimiter.search(command, line_end + 1)
        body_end = end.start() if end else len(command)
        line_start = command.rfind("\n", 0, match.start()) + 1
        feeder = _split_segments(command[line_start : match.start()])
        feeder_tokens = _tokenize(feeder[-1]) if feeder else []
        if feeder_tokens and _program_name(feeder_tokens[0]) in _SHELLS:
            shell_bodies.append(command[line_end + 1 : body_end])
        out.append(command[pos : line_end + 1])
        pos = end.end() if end else len(command)
    out.append(command[pos:])
    return "".join(out), shell_bodies


def _split_segments(text: str) -> list[str]:
    """Split on command separators outside quotes: ; & | newline ( ) { } and backticks."""
    segments: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        char = text[i]
        if quote is not None:
            buf.append(char)
            if quote in ("'@", '"@'):  # PowerShell here-string, ends at a line starting '@
                if text.startswith("\n" + quote, i):
                    buf.append(quote)
                    i += len(quote)
                    quote = None
            elif char == "\\" and quote == '"' and i + 1 < len(text):
                buf.append(text[i + 1])
                i += 1
            elif char == quote:
                quote = None
        elif char == "@" and text[i + 1 : i + 2] in ("'", '"') and text[i + 2 : i + 3] == "\n":
            quote = text[i + 1] + "@"
            buf.append(char)
        elif char in "'\"":
            quote = char
            buf.append(char)
        elif char in ";&|\n(){}`":
            segments.append("".join(buf))
            buf = []
        else:
            buf.append(char)
        i += 1
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


def _tokenize(segment: str) -> list[str]:
    # Windows paths: turn backslashes into slashes so shlex does not eat them as escapes.
    text = re.sub(r"\\(?![\"'$`\s\\])", "/", segment.replace("\\\n", " "))
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def _without_messages(tokens: list[str]) -> list[str]:
    kept: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        lowered = token.lower()
        if lowered in _MESSAGE_FLAGS:
            skip = True
            continue
        if lowered.split("=", 1)[0] in _MESSAGE_FLAGS and "=" in lowered:
            continue
        kept.append(token)
    return kept


def _non_flags(args: list[str], takes_value: frozenset[str] = frozenset()) -> list[str]:
    """Positional arguments, skipping flags and the values of flags in takes_value."""
    out: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg.startswith("-"):
            skip = arg in takes_value
        else:
            out.append(arg)
    return out


# --- Shell checks ------------------------------------------------------------------------


def check_shell(command: str, cwd: str | None = None, depth: int = 0) -> Decision | None:
    """Rules for shell tools (Bash, PowerShell, Monitor)."""
    if depth > _MAX_DEPTH:
        return _deny("Commands are nested too deeply for the guard to check.")
    text, shell_bodies = _strip_heredocs(command)
    lowered = _normalize(text)
    decisions: list[Decision | None] = []
    if "disableallhooks" in lowered:
        decisions.append(_deny("Mentions disableAllHooks, which would switch off the guardrails."))
    if _SECRET_ENV_VAR.search(lowered):
        decisions.append(_deny("Reads an environment variable that looks like a secret."))
    if _GUARD_FILES.search(lowered):
        decisions.append(_ask("Touches the agent's own guardrails (.claude settings or hooks)."))
    for match in _SUBSTITUTION.finditer(text):
        inner = match.group(1) if match.group(1) is not None else match.group(2)
        decisions.append(check_shell(inner, cwd, depth + 1))
    decisions.extend(_check_segment(s, cwd, depth) for s in _split_segments(text))
    decisions.extend(check_shell(body, cwd, depth + 1) for body in shell_bodies)
    return _worst(decisions)


def _check_segment(segment: str, cwd: str | None, depth: int) -> Decision | None:
    tokens = _tokenize(segment)
    if not tokens:
        return None
    label = _secret_label(" ".join(_without_messages(tokens)))
    secret = _deny(f"Touches {label}; the agent never reads or writes secrets.") if label else None
    if any(t.lower().startswith("env:") for t in tokens):
        secret = _deny("Reads environment variables, which may hold secrets.")
    return _worst([secret, _check_command(tokens, cwd, depth)])


def _check_command(tokens: list[str], cwd: str | None, depth: int) -> Decision | None:
    # Look through wrappers and variable assignments to the command that actually runs.
    while tokens:
        name = _program_name(tokens[0])
        rest = tokens[1:]
        if _ASSIGNMENT.match(tokens[0]):
            tokens = rest
        elif name == "env":
            tokens = [t for t in rest if not t.startswith("-") and not _ASSIGNMENT.match(t)]
            if not tokens:
                return _deny("Prints all environment variables, which may hold secrets.")
        elif name in _WRAPPERS:
            # Skip the wrapper's own flags and numbers (timeout 5, nice -n 10).
            start = next(
                (i for i, t in enumerate(rest) if not t.startswith("-") and not t.isdigit()),
                len(rest),
            )
            tokens = rest[start:]
        elif name == "uv" and _non_flags(rest)[:1] == ["run"]:
            after_run = rest[rest.index("run") + 1 :]
            positional = _non_flags(after_run, _UV_VALUE_FLAGS)
            tokens = after_run[after_run.index(positional[0]) :] if positional else []
        else:
            break
    if not tokens:
        return None
    first = tokens[0]
    name = _program_name(first)
    args = tokens[1:]
    if name in {"eval", "iex", "invoke-expression"}:
        return check_shell(" ".join(args), cwd, depth + 1)
    if name in _SHELLS:
        return _check_shell_invocation(name, args, cwd, depth)
    rule = _RULES.get(name)
    if rule is not None:
        return rule(args)
    if first.lower().endswith(_SCRIPT_SUFFIXES):
        return _check_script(first, cwd, depth)
    return None


def _check_shell_invocation(
    name: str, args: list[str], cwd: str | None, depth: int
) -> Decision | None:
    """bash -c "...", pwsh -Command ..., cmd /c ...: check the inner command or script."""
    skip = False
    for i, arg in enumerate(args):
        flag = arg.lower()
        if skip:
            skip = False
            continue
        if name in _POWERSHELLS:
            if flag in _POWERSHELL_VALUE_FLAGS:
                skip = True
                continue
            if flag in ("-e", "-ec") or (len(flag) >= 3 and "-encodedcommand".startswith(flag)):
                return _deny("Runs an encoded PowerShell command the guard cannot read.")
            if flag.startswith("-c") and (
                "-command".startswith(flag) or "-commandwithargs".startswith(flag)
            ):
                return check_shell(" ".join(args[i + 1 :]), cwd, depth + 1)
            if flag in ("-f", "-file") and i + 1 < len(args):
                return _check_script(args[i + 1], cwd, depth)
        elif name == "cmd":
            if flag in ("/c", "/k"):
                return check_shell(" ".join(args[i + 1 :]), cwd, depth + 1)
        elif flag == "-c" or (flag.startswith("-") and not flag.startswith("--") and "c" in flag):
            return check_shell(" ".join(args[i + 1 :]), cwd, depth + 1)
        if not arg.startswith(("-", "/")):
            return _check_script(arg, cwd, depth)
    return None


def _check_script(path: str, cwd: str | None, depth: int) -> Decision | None:
    """A script run by a shell: read it and check its commands."""
    script = Path(path.strip("'\""))
    if not script.is_absolute() and cwd:
        script = Path(cwd) / script
    try:
        if script.stat().st_size > _MAX_SCRIPT_BYTES:
            return _ask(f"Runs {path}, which is too large for the guard to check.")
        content = script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return _ask(f"Runs {path}, which the guard could not read to check.")
    return check_shell(content, str(script.parent), depth + 1)


# --- Command rules -------------------------------------------------------------------------
# Each rule gets the arguments after the program name and returns deny, ask or None.

# az subcommands and verbs that change something, or reveal credentials.
_AZ_CHANGE_VERBS = {
    "create",
    "delete",
    "update",
    "set",
    "add",
    "remove",
    "purge",
    "recover",
    "restore",
    "import",
    "start",
    "stop",
    "restart",
    "deploy",
    "upload",
    "assign",
    "invoke",
    "reset",
    "rotate",
    "regenerate",
    "renew",
    "lock",
    "unlock",
    "move",
    "swap",
    "scale",
    "approve",
    "reject",
    "enable",
    "disable",
    "grant",
    "revoke",
    "run-command",
    "apply",
    "attach",
    "detach",
    "register",
    "unregister",
    "cancel",
}


def _az(args: list[str]) -> Decision | None:
    low = [a.lower() for a in args]
    joined = " ".join(low)
    if low[:1] == ["login"] or "get-access-token" in low:
        return _deny("Authenticates to Azure or prints an access token.")
    if "keyvault secret" in joined or "keys" in low or "--show-secrets" in low:
        return _deny("Reads or changes secrets or keys in Azure.")
    if low[:1] == ["rest"]:
        method = _flag_value(low, ("--method", "-m")) or ("post" if "--body" in low else "get")
        if method != "get":
            return _deny("Changes Azure through a raw REST call.")
        return _ask("Reads from Azure through a raw REST call.")
    for arg in _non_flags(low):
        if arg in _AZ_CHANGE_VERBS or any(arg.startswith(v + "-") for v in _AZ_CHANGE_VERBS):
            return _deny("Changes Azure resources or settings.")
    return _ask("Reads from Azure.")


_TERRAFORM_ALLOWED = {"fmt", "validate", "version", "help", "providers", "graph", "get"}


def _terraform(args: list[str]) -> Decision | None:
    low = [a.lower() for a in args]
    positional = _non_flags(low)
    if not positional:
        return None
    sub = positional[0]
    if sub in _TERRAFORM_ALLOWED:
        return None
    if sub == "init":
        if "-backend=false" in low:
            return None
        return _ask("Connects Terraform to the real state backend in Azure.")
    if sub == "plan":
        return _ask("Runs terraform plan, which reads the real Azure state.")
    return _deny(f"terraform {sub} changes Azure or reads state that may hold secrets.")


_GH_DENIED_GROUPS = {"auth", "secret", "variable", "ruleset", "gpg-key", "ssh-key"}
_GH_READ_ONLY_GROUPS = {"search", "status", "browse", "help", "version", "completion"}
_GH_READ_ACTIONS = {"list", "view", "status", "checks", "diff", "watch", "checkout"}
_GH_VALUE_FLAGS = frozenset({"-r", "--repo"})


def _gh(args: list[str]) -> Decision | None:
    low = [a.lower() for a in args]
    positional = _non_flags(low, _GH_VALUE_FLAGS)
    if not positional:
        return None
    group = positional[0]
    action = positional[1] if len(positional) > 1 else ""
    if group in _GH_DENIED_GROUPS or (group == "alias" and action in ("set", "import")):
        return _deny(f"gh {group} handles credentials, secrets or repository rules.")
    if group == "repo" and action in (
        "edit",
        "delete",
        "rename",
        "archive",
        "unarchive",
        "deploy-key",
    ):
        return _deny(f"gh repo {action} changes repository settings.")
    if group == "pr" and action == "merge":
        return _deny("Merging is the human's call.")
    if group == "api":
        method = _flag_value(low, ("-x", "--method"))
        has_fields = any(
            a in ("-f", "--field", "--raw-field", "--input")
            or a.startswith(("--field=", "--raw-field=", "--input="))
            for a in low
        )
        if (method or ("post" if has_fields else "get")) != "get":
            return _deny("Changes GitHub through a raw API call.")
        return _ask("Reads from the GitHub API.")
    if group in _GH_READ_ONLY_GROUPS or action in _GH_READ_ACTIONS:
        return None
    return _ask(f"gh {group} {action} acts on GitHub.".replace("  ", " "))


_GIT_VALUE_FLAGS = frozenset({"-c", "--git-dir", "--work-tree"})  # -c and -C, lowercased
_PROTECTED_BRANCHES = {"main", "master"}


def _git(args: list[str]) -> Decision | None:
    low = [a.lower() for a in args]
    if "--no-verify" in low or any("core.hookspath" in a for a in low):
        return _deny("Skips or redirects git hooks.")
    positional = _non_flags(low, _GIT_VALUE_FLAGS)
    if not positional:
        return None
    sub = positional[0]
    after = low[low.index(sub) + 1 :]
    if sub == "commit" and "-n" in after:
        return _deny("git commit -n skips git hooks.")
    if sub == "add" and ({"-f", "--force"} & set(after)):
        return _deny("Force-adds files git ignores, which is where secrets live.")
    if sub == "push":
        if {"-f", "--force", "--mirror", "--all"} & set(after) or any(
            a.startswith(("--force-with-lease", "--force-if-includes", "+")) for a in after
        ):
            return _deny("Force-pushes or pushes every branch.")
        for ref in _non_flags(after):
            target = ref.rsplit(":", 1)[-1].removeprefix("refs/heads/")
            if target in _PROTECTED_BRANCHES:
                return _deny("Pushes to main, which only changes through reviewed PRs.")
        return _ask("Pushes to GitHub.")
    return None


_MAKE_SAFE_TARGETS = {"install", "fmt", "lint", "typecheck", "test", "tf-check", "check", "help"}


def _make(args: list[str]) -> Decision | None:
    targets = [
        t
        for t in _non_flags(args, frozenset({"-C", "-f", "--directory", "--file", "-j"}))
        if "=" not in t
    ]
    unknown = [t for t in targets if t not in _MAKE_SAFE_TARGETS]
    if unknown:
        return _ask(f"Runs make {' '.join(unknown)}, which the guard does not know is safe.")
    return None


def _install(what: str) -> Rule:
    def rule(args: list[str]) -> Decision | None:
        return _ask(f"Installs software ({what}).")

    return rule


def _pip(args: list[str]) -> Decision | None:
    if _non_flags([a.lower() for a in args])[:1] in (["install"], ["download"]):
        return _ask("Installs Python packages outside the project's lockfile.")
    return None


def _python(args: list[str]) -> Decision | None:
    low = [a.lower() for a in args]
    if "-m" in low and low[low.index("-m") + 1 : low.index("-m") + 2] == ["pip"]:
        return _pip(args[low.index("-m") + 2 :])
    return None


_UV_VALUE_FLAGS = frozenset(
    {
        "--with",
        "--python",
        "-p",
        "--directory",
        "--project",
        "--package",
        "--extra",
        "--group",
        "--env-file",
        "--index",
    }
)


def _uv(args: list[str]) -> Decision | None:
    positional = _non_flags([a.lower() for a in args], _UV_VALUE_FLAGS)
    if positional[:1] in (["add"], ["remove"]):
        return _ask(f"Changes the project's dependencies (uv {positional[0]}).")
    if positional[:2] in (
        ["pip", "install"],
        ["tool", "install"],
        ["tool", "run"],
        ["python", "install"],
        ["self", "update"],
    ):
        return _ask(f"Installs software (uv {' '.join(positional[:2])}).")
    return None


def _node(args: list[str]) -> Decision | None:
    if _non_flags([a.lower() for a in args])[:1] in (["install"], ["i"], ["add"], ["ci"]):
        return _ask("Installs JavaScript packages.")
    return None


def _env_dump(name: str) -> Rule:
    def rule(args: list[str]) -> Decision | None:
        low = [a.lower() for a in args]
        if name == "printenv" or not low or low[0] in ("-p", "-x"):
            return _deny("Prints environment variables, which may hold secrets.")
        return None

    return rule


def _flag_value(low: list[str], names: tuple[str, ...]) -> str | None:
    for i, arg in enumerate(low):
        if arg in names and i + 1 < len(low):
            return low[i + 1]
        for name in names:
            if arg.startswith(name + "="):
                return arg.split("=", 1)[1]
    return None


_RULES: dict[str, Rule] = {
    "az": _az,
    "terraform": _terraform,
    "tofu": _terraform,
    "gh": _gh,
    "git": _git,
    "make": _make,
    "pip": _pip,
    "pip3": _pip,
    "python": _python,
    "python3": _python,
    "py": _python,
    "uv": _uv,
    "uvx": _install("uvx runs downloaded tools"),
    "npm": _node,
    "pnpm": _node,
    "yarn": _node,
    "npx": _install("npx runs downloaded packages"),
    "winget": _install("winget"),
    "choco": _install("choco"),
    "scoop": _install("scoop"),
    "msiexec": _install("msiexec"),
    "pipx": _install("pipx"),
    "apt": _install("apt"),
    "apt-get": _install("apt-get"),
    "brew": _install("brew"),
    "install-module": _install("Install-Module"),
    "install-package": _install("Install-Package"),
    "install-script": _install("Install-Script"),
    "add-appxpackage": _install("Add-AppxPackage"),
    "printenv": _env_dump("printenv"),
    "set": _env_dump("set"),
    "export": _env_dump("export"),
    "declare": _env_dump("declare"),
}


# --- Entry point -------------------------------------------------------------------------

# File tools and the input fields that hold paths. Glob only lists names, so it is not here.
_PATH_FIELDS: dict[str, tuple[str, ...]] = {
    "Read": ("file_path",),
    "Edit": ("file_path",),
    "Write": ("file_path",),
    "NotebookEdit": ("notebook_path",),
    "Grep": ("path", "glob"),
}
_WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}


def decide(event: object) -> Decision | None:
    """Decide on one tool call, given the hook's JSON input."""
    if not isinstance(event, dict):
        return _deny("The guard could not read the tool call.")
    data = cast(dict[str, object], event)
    tool = data.get("tool_name")
    tool_input = data.get("tool_input")
    if not isinstance(tool, str) or not isinstance(tool_input, dict):
        return _deny("The guard could not read the tool call.")
    fields = cast(dict[str, object], tool_input)
    cwd = data.get("cwd")
    command = fields.get("command")
    if isinstance(command, str):
        return check_shell(command, cwd if isinstance(cwd, str) else None)
    write = tool in _WRITE_TOOLS
    return _worst(
        check_path(value, write=write)
        for key in _PATH_FIELDS.get(tool, ())
        if isinstance(value := fields.get(key), str)
    )


def main() -> int:
    try:
        decision = decide(json.loads(sys.stdin.read()))
    except Exception as error:  # fail closed: a broken guard must not let calls through
        decision = _deny(f"The guard hook failed ({type(error).__name__}).")
    if decision is None:
        return 0
    if decision.kind == "deny":
        reason = (
            f"Blocked by the agent guardrails (.claude/hooks/guard.py): {decision.reason} "
            "Do not retry or work around this; give the human the exact command to run."
        )
    else:
        reason = f"Agent guardrails: {decision.reason} Approve only if you expected this."
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision.kind,
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
