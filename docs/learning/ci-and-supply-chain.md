# CI and supply chain

## CI as the referee · step 0.2

CI runs the checks nobody can skip. Here it runs on pull requests only (not on pushes to `main`, since `main` only changes through PRs). GitHub Actions is free for public repositories.

## Two layers of secret scanning · step 0.2

- **GitHub push protection** rejects a push containing a *recognised* token format before it reaches GitHub. A fake GitHub `ghp_` token was blocked.
- **gitleaks in CI** also catches *generic* secrets by pattern and randomness. A made-up `api_key` passed push protection but failed CI.

Each layer covers the other's gap.

## Pinning actions by commit SHA · step 0.2

A GitHub Action tag like `v7` can be moved to different code by whoever controls that repo; a commit SHA cannot. Actions are pinned by SHA (tag in a comment) and Dependabot proposes updates. The same idea pins the runner image (`ubuntu-24.04`, not `ubuntu-latest`) so the platform does not change underneath.

## Least-privilege workflows · step 0.2

Workflows get only `contents: read`, and checkout does not keep credentials on disk. A compromised step can then do very little.

## Branch rulesets · step 0.2

`main` only changes through a PR with both checks green, with no bypass even for the admin, so the rules are real rather than advisory.

Surprise: pushing a PR's own already-checked commit straight to `main` counted as merging that PR, so the first "is it blocked?" test proved nothing. A commit outside any PR was the real test. Lesson: a test of a control must use an input the control should actually reject.

## CI never touches Azure · step 0.4 (dropped)

GitHub Actions holds no Azure identity at all. A compromised workflow, action or dependency then cannot reach Azure, and nothing about the Azure account leaks into Actions logs, which are public on a public repo. The trade-off: drift between Terraform and Azure is only caught when `terraform plan` is run by hand.
