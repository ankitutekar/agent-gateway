# Learning log

One entry per step: the concepts it introduced, what I learned, and what surprised me.

## 0.1 Name, repository and plan location (2026-10-13)

**Concepts**

- **ADR (architecture decision record):** a short file per decision recording context, options, the choice and when to revisit it. It stops settled questions being reopened by accident, and gives coding agents the "why" along with the "what".
- **Monorepo vs multiple repos:** separate repos show clean boundaries (the gateway is usable by any agent) but cost coordination (versioned contracts, several CI setups). Starting with one repo and splitting later is cheap; merging later is harder.
- **Public-repo hygiene:** every commit carries an author email. GitHub's noreply address (`ID+username@users.noreply.github.com`) keeps the real one private; it was set per repo before the first push.
- **Licence:** MIT lets anyone use the code with attribution; Apache-2.0 adds an explicit patent grant.

**Prompt:** what would have pushed me to a monorepo instead?
**Answer:**

## 0.2 Project scaffolding and CI (2026-10-13)

**Concepts**

- **uv and the lockfile:** `pyproject.toml` says which packages are wanted; `uv.lock` records the exact versions resolved, so every install (laptop or CI) is identical. uv also installs the Python version itself.
- **ruff:** formatter and linter in one. Formatting removes style debates; linting catches likely bugs, and its `S` rules flag security smells (hard-coded passwords, `eval`, insecure temp files).
- **Type checking (pyright, strict):** Python ignores type hints at runtime; a type checker reads them and finds mismatches before the code runs. Strict mode also complains about code it cannot fully understand, which keeps agent-written code honest.
- **Local checks vs CI:** `make check` runs the same commands as CI, so a green laptop predicts a green pipeline. CI is the referee that cannot be skipped.
- **Two layers of secret scanning:** GitHub push protection rejects a push containing a *recognised* token format (a GitHub `ghp_` token was blocked before reaching GitHub). gitleaks in CI also catches *generic* secrets by pattern and randomness (a made-up `api_key` passed push protection but failed CI). Each layer covers the other's gap.
- **Supply-chain safety in CI:** a GitHub Action tag like `v7` can be moved to different code by whoever controls that repo; a commit SHA cannot. Actions are pinned by SHA, Dependabot proposes updates, and workflows get only `contents: read`.
- **Branch rulesets:** `main` only changes through a PR with both checks green, with no bypass even for the admin. Surprise: pushing a PR's own already-checked commit straight to `main` counted as merging that PR, so the first "is it blocked?" test proved nothing; a commit outside any PR was the real test.
- **Reproducible environments:** the CI runner image is pinned (`ubuntu-24.04`, not `ubuntu-latest`) so the platform does not change underneath; line endings are normalised to LF for Linux.

**Prompt:** which check caught something real first?
**Answer:**

## 0.3 Terraform bootstrap root (2026-10-20)

**Concepts**

- **Terraform state:** Terraform's memory of which real Azure resource belongs to which block of code. Lose it and Terraform can no longer update or delete what it created. It lives in the storage account so it is shared, backed up (versioning, 30-day soft delete) and protected.
- **The bootstrap chicken-and-egg:** the storage account that holds state is created by the same Terraform that needs it. Solution: first apply with local state (a temporary, git-ignored `backend_override.tf`), then `terraform init -migrate-state` to move it, then confirm with a `plan` showing "No changes".
- **Secrets and state:** state can contain secrets in plain text for some resources. So secrets are kept out of Terraform entirely (the model key is set with `az` directly) and the state account is locked to Entra identities only.
- **Shared keys disabled:** a storage account normally has two master keys that open everything. With them disabled, access needs an Entra identity plus an RBAC data role, so there is no single key to leak.
- **RBAC vs access policies (Key Vault):** RBAC uses the same role model as the rest of Azure and can be scoped down to one secret. Surprise: in RBAC mode even the vault's creator gets no access until a role is explicitly assigned.
- **Object ID:** every identity in Entra ID (user, app, managed identity) has a fixed object ID per tenant. Role assignments point at object IDs, not emails. Terraform reads the signed-in user's ID and grants that identity access.
- **Soft delete and purge protection:** a deleted vault is recoverable for 90 days and cannot be purged early. The persistent root never purges on destroy. Random name suffixes avoid clashes with soft-deleted names and satisfy global uniqueness (names become public URLs).
- **Cost control on pay-as-you-go:** there is no spending limit, and budgets only send alerts (with hours of lag). Real protection needs automation that acts, planned as the automatic cost stop in step 3.7.
- **Test the alert path:** an action group email failed until the address was verified. Without the test, the first real budget alert would have gone nowhere.
- **Region by feature availability:** East US 2 was chosen because preview services (Content Safety Task Adherence, APIM AI Gateway tier) are not available in India regions.
- **MFA for management access:** Azure requires MFA for Resource Manager; signing in with `az login --tenant <id>` triggered it.
- **Provider lock file:** `.terraform.lock.hcl` pins provider versions and checksums; it was generated for both Windows and Linux so CI verifies the same binaries.

**Prompt:** what surprised me about Terraform state and secrets?
**Answer:**
