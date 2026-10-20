# Azure identity and access

## Object IDs · step 0.3

Every identity in Entra ID (user, app, managed identity) has a fixed object ID per tenant. Role assignments point at object IDs, not emails, because emails can change. A personal Microsoft account gets its own user object, with its own ID, in each tenant it belongs to. Terraform reads the signed-in user's ID (`azurerm_client_config.object_id`) and grants that identity access.

## RBAC vs access policies (Key Vault) · step 0.3

RBAC uses the same role model as the rest of Azure and can be scoped down to a single secret. Surprise: in RBAC mode even the vault's creator gets no access until a role (here Key Vault Secrets Officer) is explicitly assigned.

## Shared keys disabled · step 0.3

A storage account normally has two master keys that open everything. With them disabled, access needs an Entra identity plus an RBAC data role (Storage Blob Data Contributor), so there is no single key to leak. Role assignments can take a few minutes to take effect.

## MFA for management access · step 0.3

Azure requires multi-factor authentication for Resource Manager (the API behind `az` and Terraform). A plain `az login` found no subscriptions; `az login --tenant <id>` prompted for MFA and worked.
