terraform {
  required_version = ">= 1.16.0, < 2.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.10.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.9.1"
    }
  }

  # State lives in the storage account this root creates. On the very first
  # run, comment this block out, apply with local state, then restore it and
  # run `terraform init -migrate-state`. See README.md.
  backend "azurerm" {
    use_azuread_auth = true
    # resource_group_name, storage_account_name, container_name and key come
    # from backend.hcl (git-ignored), passed with -backend-config=backend.hcl.
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id

  # The state account has shared keys disabled, so data-plane calls
  # (creating the container) must use Entra ID.
  storage_use_azuread = true

  features {
    key_vault {
      # This root is persistent. Never purge on destroy: a purged vault and
      # its secrets cannot be recovered.
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}
