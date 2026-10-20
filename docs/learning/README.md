# Learning notes

Learning is one of this project's main goals. Notes are organised by **concept**, not by step, so each file grows as later steps revisit the topic. Each entry notes the step where it first came up.

| Topic | What's in it |
|---|---|
| [Repository practices](repository-practices.md) | ADRs, one repo vs many, public-repo hygiene, licences |
| [Python tooling](python-tooling.md) | uv and lockfiles, ruff, type checking, local checks |
| [CI and supply chain](ci-and-supply-chain.md) | Secret scanning layers, pinning actions, workflow permissions, rulesets, why CI never touches Azure |
| [Terraform](terraform.md) | State, the bootstrap chicken-and-egg, secrets in state, lock files |
| [Azure identity and access](azure-identity-and-access.md) | Object IDs, RBAC, shared keys, MFA |
| [Azure cost and resources](azure-cost-and-resources.md) | Pay-as-you-go and budgets, alert testing, regions, soft delete |

[Reflections](reflections.md) holds the per-step learning-log prompts and my own answers.

Add a new topic file when a concept doesn't fit an existing one; prefer extending a file over creating a near-duplicate.
