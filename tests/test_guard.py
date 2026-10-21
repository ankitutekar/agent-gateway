"""Tests for the coding-agent guard hook (.claude/hooks/guard.py).

Each case is a tool call and the expected answer: "deny", "ask", or None (normal flow).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from guard import check_path, check_shell, decide

GUARD = Path(__file__).parents[1] / ".claude" / "hooks" / "guard.py"

SHELL_CASES = [
    # Azure: reads ask, changes and credentials are blocked
    ("az group list", "ask"),
    ("az account show", "ask"),
    ("az.cmd version", "ask"),
    ("az login --tenant 123", "deny"),
    ("az account get-access-token", "deny"),
    ("az keyvault secret show --name x --vault-name v", "deny"),
    ("az keyvault secret list --vault-name v", "deny"),
    ("az storage account keys list -n x", "deny"),
    ("az group delete -n rg", "deny"),
    ("az ad sp create-for-rbac", "deny"),
    ("az role assignment create --role Reader", "deny"),
    ("az rest --url https://management.azure.com/x", "ask"),
    ("az rest --method put --url https://management.azure.com/x", "deny"),
    # Terraform: offline commands allowed, plan and real init ask, the rest blocked
    ("terraform fmt -check -recursive infra", None),
    ("terraform -chdir=infra/bootstrap validate", None),
    ("terraform -chdir=infra/bootstrap init -backend=false -input=false", None),
    ("terraform init -backend-config=backend.example", "ask"),
    ("terraform plan", "ask"),
    ("terraform apply", "deny"),
    ("terraform destroy -auto-approve", "deny"),
    ("terraform state list", "deny"),
    ("terraform output", "deny"),
    ("terraform show", "deny"),
    ("terraform import x y", "deny"),
    # GitHub CLI
    ("gh pr list", None),
    ("gh pr view 4", None),
    ("gh run watch 123", None),
    ("gh pr create --title t --body b", "ask"),
    ("gh api repos/ankitutekar/agent-gateway", "ask"),
    ("gh api -X PATCH repos/o/r -f visibility=private", "deny"),
    ("gh api repos/o/r/rulesets -f name=x", "deny"),
    ("gh pr merge 5 --squash", "deny"),
    ("gh auth status", "deny"),
    ("gh auth token", "deny"),
    ("gh secret set X", "deny"),
    ("gh variable list", "deny"),
    ("gh ruleset list", "deny"),
    ("gh repo edit --visibility private", "deny"),
    ("gh -R o/r repo view", None),
    ("gh alias set x 'auth token'", "deny"),
    # git
    ("git status", None),
    ("git commit -m 'docs: update'", None),
    ("git push -u origin chore/agent-guardrails", "ask"),
    ("git push origin main", "deny"),
    ("git push origin HEAD:main", "deny"),
    ("git push --force origin feature", "deny"),
    ("git push origin +feature", "deny"),
    ("git push --force-with-lease", "deny"),
    ("git commit --no-verify -m x", "deny"),
    ("git commit -n -m x", "deny"),
    ("git add -f infra/bootstrap/x.txt", "deny"),
    ("git -c core.hooksPath=/dev/null commit -m x", "deny"),
    # Installing software
    ("winget install Hashicorp.Terraform", "ask"),
    ("pip install requests", "ask"),
    ("python -m pip install requests", "ask"),
    ("uv add httpx", "ask"),
    ("uv sync --locked", None),
    ("uv run pytest", None),
    ("npm install -g something", "ask"),
    ("Install-Module Az", "ask"),
    # make: known targets run, unknown ones ask
    ("make check", None),
    ("make tf-check", None),
    ("make up", "ask"),
    # Secret files through the shell
    ("cat infra/bootstrap/terraform.tfvars", "deny"),
    ("cat infra/bootstrap/terraform.tfvars.example", None),
    ("Get-Content infra\\bootstrap\\backend.hcl", "deny"),
    ("type D:\\x\\.env", "deny"),
    ("cat .env.example", None),
    ("cat .terraform/terraform.tfstate", "deny"),
    ("ls ~/.azure/", "deny"),
    ("cat ~/.config/gh/hosts.yml", "deny"),
    ("echo x > .env", "deny"),
    ("cat ~/.ssh/id_ed25519", "deny"),
    # Environment variables
    ("env", "deny"),
    ("printenv", "deny"),
    ("export -p", "deny"),
    ("Get-ChildItem env:", "deny"),
    ("echo $ANTHROPIC_API_KEY", "deny"),
    ("echo $env:GITHUB_TOKEN", "deny"),
    ("env FOO=1 make check", None),
    ("export FOO=1", None),
    ("echo $PWD", None),
    # Chaining, substitution and wrappers do not hide a command
    ("cd infra && az login", "deny"),
    ("make check; terraform apply", "deny"),
    ("echo ok | xargs az group list", "ask"),
    ("echo $(az account get-access-token)", "deny"),
    ('echo "$(az account get-access-token)"', "deny"),
    ("FOO=1 terraform apply", "deny"),
    ("timeout 30 terraform apply", "deny"),
    ("uv run --no-sync az group list", "ask"),
    ('bash -c "az login"', "deny"),
    ("bash -lc 'terraform apply'", "deny"),
    ('pwsh -NoProfile -Command "az login"', "deny"),
    ("powershell -ExecutionPolicy Bypass -Command az login", "deny"),
    ("cmd /c az login", "deny"),
    ("pwsh -EncodedCommand ZQBjAGgAbwA=", "deny"),
    ('Invoke-Expression "az login"', "deny"),
    ("eval 'terraform apply'", "deny"),
    ("& az login", "deny"),
    ("cd x\naz login", "deny"),
    # Heredoc bodies are data, unless a shell reads them
    ("git commit -F - <<'EOF'\nmention terraform.tfvars and az login\nEOF", None),
    ("bash <<'EOF'\naz login\nEOF", "deny"),
    # Message text is not a path
    ("git commit -m 'never read terraform.tfvars'", None),
    ("gh pr view 4 --json body", None),
    # The guard protects itself
    ("sed -i 's/deny/x/' .claude/hooks/guard.py", "ask"),
    ("echo '{}' > .claude/settings.local.json", "ask"),
    ("echo disableAllHooks", "deny"),
    # Everyday commands stay in the normal flow
    ("ls -la", None),
    ("git log --oneline -5", None),
    ("uv run ruff check .", None),
]


@pytest.mark.parametrize(("command", "expected"), SHELL_CASES)
def test_shell(command: str, expected: str | None) -> None:
    decision = check_shell(command)
    assert (decision.kind if decision else None) == expected


PATH_CASES = [
    ("D:\\repo\\infra\\bootstrap\\terraform.tfvars", False, "deny"),
    ("D:/repo/infra/bootstrap/terraform.tfvars.example", False, None),
    ("D:/repo/infra/bootstrap/backend.hcl", True, "deny"),
    ("D:/repo/infra/bootstrap/.terraform/terraform.tfstate", False, "deny"),
    ("D:/repo/.env", False, "deny"),
    ("D:/repo/.env.local", True, "deny"),
    ("D:/repo/.env.example", False, None),
    ("C:\\Users\\me\\.azure\\msal_token_cache.json", False, "deny"),
    ("C:/Users/me/.config/gh/hosts.yml", False, "deny"),
    ("D:/repo/certs/server.pem", False, "deny"),
    ("D:/repo/.claude/hooks/guard.py", True, "ask"),
    ("D:/repo/.claude/hooks/guard.py", False, None),
    ("D:/repo/.claude/settings.json", True, "ask"),
    ("C:/Users/me/.claude/settings.json", True, "ask"),
    ("C:/Users/me/.claude/projects/x/memory/note.md", True, None),
    ("D:/repo/src/agent_gateway/__init__.py", True, None),
    ("D:/repo/.venv/lib/site.py", False, None),
]


@pytest.mark.parametrize(("path", "write", "expected"), PATH_CASES)
def test_path(path: str, write: bool, expected: str | None) -> None:
    decision = check_path(path, write=write)
    assert (decision.kind if decision else None) == expected


def test_decide_routes_tools() -> None:
    read = decide({"tool_name": "Read", "tool_input": {"file_path": "/r/.env"}})
    grep = decide({"tool_name": "Grep", "tool_input": {"pattern": "x", "glob": "*.tfvars"}})
    bash = decide({"tool_name": "Bash", "tool_input": {"command": "terraform apply"}})
    pwsh = decide({"tool_name": "PowerShell", "tool_input": {"command": "az login"}})
    edit = decide({"tool_name": "Edit", "tool_input": {"file_path": "/r/README.md"}})
    assert read and read.kind == "deny"
    assert grep and grep.kind == "deny"
    assert bash and bash.kind == "deny"
    assert pwsh and pwsh.kind == "deny"
    assert edit is None


def test_decide_denies_unreadable_input() -> None:
    decision = decide({"tool_name": "Bash"})
    assert decision and decision.kind == "deny"


def test_script_contents_are_checked(tmp_path: Path) -> None:
    script = tmp_path / "deploy.sh"
    script.write_text("echo hi\nterraform apply -auto-approve\n")
    decision = check_shell("bash deploy.sh", cwd=str(tmp_path))
    assert decision and decision.kind == "deny"


def test_unreadable_script_asks(tmp_path: Path) -> None:
    decision = check_shell("./missing.sh", cwd=str(tmp_path))
    assert decision and decision.kind == "ask"


def _run_hook(stdin: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed arguments, test only
        [sys.executable, str(GUARD)], input=stdin, capture_output=True, text=True, check=False
    )


def test_hook_output_format() -> None:
    result = _run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "az login"}}))
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert result.returncode == 0
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"


def test_hook_is_silent_when_no_opinion() -> None:
    result = _run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}))
    assert result.returncode == 0
    assert result.stdout == ""


def test_hook_fails_closed_on_bad_input() -> None:
    result = _run_hook("not json")
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
