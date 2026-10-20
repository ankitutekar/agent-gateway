data "azurerm_client_config" "current" {}

data "azurerm_subscription" "current" {}

# Globally unique names (storage accounts, vaults) need a suffix, which also
# avoids clashes with soft-deleted resources from earlier attempts.
resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

locals {
  suffix = random_string.suffix.result
  tags = {
    project = "agent-gateway"
    root    = "bootstrap"
  }
}

resource "azurerm_resource_group" "bootstrap" {
  name     = "rg-${var.prefix}-bootstrap"
  location = var.location
  tags     = local.tags
}

# --- Terraform state -------------------------------------------------------

resource "azurerm_storage_account" "state" {
  name                     = "st${var.prefix}tf${local.suffix}"
  resource_group_name      = azurerm_resource_group.bootstrap.name
  location                 = azurerm_resource_group.bootstrap.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  # Entra ID only: no account keys, no anonymous access, modern TLS.
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true

  # Recover a corrupted or deleted state file.
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 30
    }
    container_delete_retention_policy {
      days = 30
    }
  }

  tags = local.tags
}

resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.state.id
  container_access_type = "private"

  depends_on = [azurerm_role_assignment.state_operator]
}

# --- Key Vault -------------------------------------------------------------

resource "azurerm_key_vault" "main" {
  name                = "kv-${var.prefix}-${local.suffix}"
  resource_group_name = azurerm_resource_group.bootstrap.name
  location            = azurerm_resource_group.bootstrap.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 90

  tags = local.tags
}

# --- Access for the operator (whoever runs this root) ----------------------
# RBAC mode grants nothing by default, not even to the creator.

resource "azurerm_role_assignment" "state_operator" {
  scope                = azurerm_storage_account.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "vault_operator" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# --- Cost alerts -----------------------------------------------------------
# Budgets only notify; they never stop spending. The automatic stop comes
# with the app root.

resource "azurerm_monitor_action_group" "cost" {
  name                = "ag-${var.prefix}-cost"
  resource_group_name = azurerm_resource_group.bootstrap.name
  short_name          = "cost"

  email_receiver {
    name                    = "owner"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }

  tags = local.tags
}

resource "azurerm_consumption_budget_subscription" "monthly" {
  name            = "budget-${var.prefix}-monthly"
  subscription_id = data.azurerm_subscription.current.id
  amount          = var.monthly_budget
  time_grain      = "Monthly"

  time_period {
    start_date = var.budget_start_date
  }

  dynamic "notification" {
    for_each = {
      actual_20    = { threshold = 20, type = "Actual" }
      actual_50    = { threshold = 50, type = "Actual" }
      actual_100   = { threshold = 100, type = "Actual" }
      forecast_100 = { threshold = 100, type = "Forecasted" }
    }
    content {
      enabled        = true
      operator       = "GreaterThanOrEqualTo"
      threshold      = notification.value.threshold
      threshold_type = notification.value.type
      contact_groups = [azurerm_monitor_action_group.cost.id]
    }
  }

  lifecycle {
    # Azure rewrites the start date; don't fight it.
    ignore_changes = [time_period]
  }
}
