output "resource_group_name" {
  value = azurerm_resource_group.bootstrap.name
}

output "state_storage_account_name" {
  value = azurerm_storage_account.state.name
}

output "state_container_name" {
  value = azurerm_storage_container.tfstate.name
}

output "key_vault_id" {
  value = azurerm_key_vault.main.id
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "cost_action_group_id" {
  description = "Reused by the automatic cost stop (step 3.7)."
  value       = azurerm_monitor_action_group.cost.id
}
