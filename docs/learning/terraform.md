# Terraform

## State · step 0.3

Terraform's memory of which real Azure resource belongs to which block of code. Lose it and Terraform can no longer update or delete what it created. It lives in a storage account so it is shared, backed up (versioning, 30-day soft delete) and protected. `.terraform/terraform.tfstate` is *not* state: it only records which backend the folder uses.

## The bootstrap chicken-and-egg · step 0.3

The storage account that holds state is created by the same Terraform that needs it. Solution: first apply with local state (a temporary, git-ignored `backend_override.tf`), then `terraform init -migrate-state` to move it, then confirm with a `plan` showing "No changes", then delete the local copy.

## Secrets and state · step 0.3

State can contain secrets in plain text for some resources. So secrets are kept out of Terraform entirely (the model key is set with `az` directly) and the state account is locked to Entra identities only.

## Variables and personal values · step 0.3

Values like the subscription ID and alert email are declared as variables and supplied from a git-ignored `terraform.tfvars` (or `TF_VAR_name` environment variables, or `-var` flags). The repo holds only `.example` files.

## Plan, then apply the saved plan · step 0.3

`terraform plan -out file` saves exactly what will change; `terraform apply file` does exactly that and nothing else. Review the plan for counts (add / change / destroy) and the security-relevant settings before applying.

## Provider lock file · step 0.3

`.terraform.lock.hcl` pins provider versions and checksums. It was generated for both Windows and Linux so CI verifies the same binaries the laptop uses.
