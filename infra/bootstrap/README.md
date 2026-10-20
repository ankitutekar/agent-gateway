# Bootstrap root

The persistent Azure baseline. Normal teardown (`make down`) never touches it.

| Resource | Why it must survive teardowns |
|---|---|
| Resource group `rg-agentgw-bootstrap` | Holds everything below |
| Storage account + `tfstate` container | Terraform state for every root, including this one |
| Key Vault | Long-lived secrets (the model API key); purge protection means a deleted vault is recoverable for 90 days |
| Action group + monthly budget | Cost alerts must keep working while everything else comes and goes |

Region: East US 2 (see [ADR 0003](../../docs/adr/0003-azure-baseline.md)).

## Prerequisites

- Terraform 1.16+, Azure CLI, logged in with `az login` to the **personal** tenant
- Permission to create role assignments on the subscription (Owner)

## First run: bootstrapping state

The state storage account is created by this root, so the first apply cannot store its state there yet.

```sh
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars   # fill in; git-ignored

# 1. Use local state for the first apply, via a git-ignored override file
printf 'terraform {\n  backend "local" {}\n}\n' > backend_override.tf
terraform init
terraform apply                                  # state is local for now

# 2. Remove the override, then point the backend at the new account
rm backend_override.tf
cp backend.hcl.example backend.hcl               # fill in from the outputs; git-ignored
terraform init -backend-config=backend.hcl -migrate-state
rm terraform.tfstate terraform.tfstate.backup   # local copies hold the same data
terraform plan                                   # must show no changes
```

## Later runs

```sh
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

## What is in the state, and who can read it

State holds resource IDs, names and your alert email, but **no secret values**: the Key Vault is created empty, and secrets are set outside Terraform (below). Reading state requires an Entra identity with a data role on the storage account (shared keys are disabled). Versioning and 30-day soft delete allow recovering an earlier state file.

If state is lost entirely, the resources still exist: recreate `backend.hcl`, then `terraform import` each resource.

## Setting the model API key

Never in code, `.tfvars`, shell history or Terraform state. From PowerShell:

```powershell
$key = Read-Host -AsSecureString "Anthropic API key"
az keyvault secret set --vault-name <key_vault_name> --name anthropic-api-key `
  --value ([System.Net.NetworkCredential]::new('', $key).Password) --output none
```

Only the gateway's managed identity gets read access to this secret (step 3.6).

## Testing the cost alert

Budgets cannot be fired on demand, but the action group they notify can:

```sh
az monitor action-group test-notifications create \
  --action-group-name ag-agentgw-cost --resource-group rg-agentgw-bootstrap \
  --alert-type budget --add-action email owner <alert_email>
```

The portal works too: Monitor → Alerts → Action groups → `ag-agentgw-cost` → **Test action group**.

If the test fails with *"There are no valid receivers in the request"*, the email address has not been verified yet: Azure does not deliver to an address until its verification is complete. Check the inbox (and spam) for the verification email.

Budgets only notify; they do not stop spending. Cost data lags usage by several hours.
