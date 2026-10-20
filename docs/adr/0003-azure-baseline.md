# 3. Azure baseline: IaC, region, billing and Key Vault

- **Status:** Accepted
- **Date:** 2026-10-20

## Infrastructure as code (D5)

- **Decision:** Terraform (azurerm provider), in separate roots: `bootstrap` (persistent), later `identity` and `app` (ephemeral).
- **Alternatives:** Bicep or azd, which are Azure-native and track new Azure features faster.
- **Why:** familiarity, and skills that carry across clouds. Where Terraform cannot reach (for example some Entra Agent ID objects), an idempotent script is used and documented.

## Region (D6)

- **Decision:** East US 2 for everything.
- **Why:** it supports every Azure service the project plans to use, including the preview ones. India regions do not: Content Safety Task Adherence is not offered in any India region. East US 2 also has the API Management AI Gateway tier preview, which East US does not.

| Service | East US 2 | India regions |
|---|---|---|
| Content Safety Prompt Shields | Yes | South India only |
| Content Safety Task Adherence | Yes | No |
| Container Apps dynamic sessions | Yes | Yes |
| APIM AI Gateway tier (preview) | Yes | No |

- **Cost:** about 200–250 ms latency from India, which is irrelevant for this workload.

## Billing

- **Decision:** the existing pay-as-you-go subscription. No free credit or credit-based subscription is available.
- **Consequence:** pay-as-you-go has no spending limit, and budgets only notify. Protection is layered:
  1. A monthly budget of ₹1,000 with alerts at 20%, 50% and 100% of actual spend and 100% of forecast (this root).
  2. An automatic stop that deletes the ephemeral `app` resource group when spending crosses a threshold (planned with the `app` root).
  3. Teardown by default, scale-to-zero and free tiers wherever possible.
- Model tokens are billed by the model provider, outside Azure, and are capped there by prepaid credits.

## Key Vault authorization

- **Decision:** Azure RBAC, not access policies.
- **Why:** one permission model across all resources, permissions scoped down to a single secret, and role assignments managed in Terraform like everything else.
- **Consequence:** the creator gets no access by default; the operator is granted Key Vault Secrets Officer explicitly.

## CI never touches Azure

- **Decision:** GitHub Actions has no Azure access at all: no identity, no federated credential, no `plan` or `apply`. Every Terraform command against Azure runs on the maintainer's machine, by the maintainer. CI runs only offline checks (lint, types, tests, `terraform fmt` and `validate`, secret scan).
- **Alternatives:** OIDC-federated CI identity running `plan` on PRs, with or without `apply`.
- **Why:**
  - Smallest attack surface: a compromised workflow, action or dependency cannot reach Azure, because CI holds nothing that can.
  - Actions logs on a public repository are public; a `plan` there would publish resource IDs, the subscription ID and other details.
  - Changes to Azure stay deliberate and human-run, which suits a learning project.
- **Consequences:**
  - "No long-lived secrets" holds trivially for CI.
  - Drift between code and Azure is only caught when the maintainer runs `plan`.
  - Anything planned as a scheduled CI job against Azure (teardown) must run inside Azure instead, alongside the automatic cost stop.
- **Revisit if:** another person needs to deploy, or deployments become frequent enough that manual runs are error-prone.

## Other baseline choices

- Terraform state storage uses Entra authentication only (shared keys disabled), with blob versioning and 30-day soft delete.
- Key Vault has purge protection on, and this root never purges on destroy.
- Personal values (subscription ID, alert email) live in git-ignored `terraform.tfvars` and `backend.hcl`.

## Revisit if

Spending patterns make ₹1,000 too tight or too loose, or a needed service turns out to be unavailable in East US 2.
