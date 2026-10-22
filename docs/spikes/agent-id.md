# Spike: Entra Agent ID feasibility (step 0.5)

**Question:** can this project's tenant use Microsoft Entra Agent ID (blueprints and agent identities) for its agents, or does it fall back to managed identities and app registrations?

**Date:** 2026-10-22 · **Timebox:** 2–3 hours · **Tenant:** personal tenant on **Microsoft Entra ID Free**, pay-as-you-go subscription, no Agent 365 or Microsoft 365 licences. The person running the spike is Global Administrator.

**Context:** Agent ID became generally available in 2026 ([what's new](https://learn.microsoft.com/en-us/entra/agent-id/whats-new-agent-id)). Conditional Access and ID Protection for agents need Agent 365 or E7 licences and are out of scope. Public sources did not agree on whether the core objects need a licence, so this spike tested it.

IDs below are shortened; none of them is a secret, but they are not needed to follow the result.

## Steps and results

### 1. Agent ID area in the Entra admin center

**Entra ID > Agents** is present with three tabs: *Agent blueprints*, *Agent identities*, *Sign-in logs*. No licence or preview banner.

### 2. Create a blueprint and an agent identity (admin center wizards)

- **Agents > Agent blueprints > New agent blueprint**: `spike-agent-blueprint`, with the admin as owner and sponsor. Worked.
- **Different from the docs:** the wizard also created a linked agent identity automatically. The [docs](https://learn.microsoft.com/en-us/entra/agent-id/create-delete-agent-identities) describe creating the identity as a separate step.
- A client secret with the shortest expiry was added on the blueprint in the admin center.

### 3. Token as the agent identity

Script: [`get-agent-token.ps1`](get-agent-token.ps1), run by the human in their own terminal; it reads the secret without echoing it and prints only decoded claims. Both steps of the [autonomous agent flow](https://learn.microsoft.com/en-us/entra/agent-id/autonomous-agent-authentication-authorization-flow) succeeded on the first try.

**T1, the blueprint acting for one agent identity** (`client_credentials` with `fmi_path`, scope `api://AzureADTokenExchange/.default`):

| Claim | Value | Meaning |
|---|---|---|
| `azp` | `756c…` | The blueprint (who asked) |
| `sub` | `…/6d1e…` | Ends with the agent identity's ID: the token is for that one agent |
| `aud` | `fb60…` | Entra's token-exchange service; T1 cannot call any API |
| `idtyp` | `app` | No user involved |

**T2, the agent identity for Microsoft Graph** (`client_credentials` with T1 as `client_assertion`):

| Claim | Value | Meaning |
|---|---|---|
| `appid` = `oid` = `sub` | `6d1e…` | The agent identity is the caller; its app ID and object ID are the same (a service principal with no app registration behind it) |
| `xms_par_app_azp` | `756c…` | The parent blueprint, carried in the token |
| `aud` | `https://graph.microsoft.com` | Only Graph accepts it |
| `idtyp` | `app` | Autonomous: no user |
| `roles` | *(absent)* | No permissions granted: the token is valid but authorises nothing |
| `app_displayname` | `spike-agent-blueprint` | Shows the blueprint's name, not the agent's |
| lifetime | 3,900 s | About 65 minutes |

### 4. Clean-up

- Deleting the blueprint in the admin center warned that child agent identities would be deleted too. The identity was still listed right afterwards (the cascade runs later, see [agent identity deletion](https://learn.microsoft.com/en-us/entra/agent-id/howto-delete-agent-identity)), so it was deleted by hand.
- All deletions are soft deletions, kept 30 days. The admin center has no recycle bin for agent objects; restore and permanent delete are Graph or PowerShell only.
- The soft-deleted blueprint application does not appear under **App registrations > Deleted applications** either. It was found and permanently deleted through Graph with the Azure CLI, run by the human:
  - `az rest --method get --url "https://graph.microsoft.com/v1.0/directory/deletedItems/microsoft.graph.application?$select=id,appId,displayName,deletedDateTime"` listed it.
  - `az rest --method delete --url "https://graph.microsoft.com/v1.0/directory/deletedItems/<id>"` succeeded. The Azure CLI's own app was allowed to do this.
- The client secret, which lived on that application, is gone with it (it also had a one-day expiry).
- The blueprint principal cannot be permanently deleted (blocked by design); it and the agent identity, which hold no credential and no permissions, are left to expire after 30 days.

## Finding

**Available.** On Microsoft Entra ID Free, with no extra licence, this tenant can create agent identity blueprints and agent identities, and an agent identity can get its own access token through the documented two-step flow.

Limits found:

- Conditional Access and ID Protection for agents need Agent 365 or E7 licences (not tested, out of scope). The gateway's own policies stand in for them, and the README maps them to the enterprise features.
- The docs lag the product: the admin center created the identity with the blueprint and could delete agent objects, which the docs say it cannot. Some Graph calls for agent identities are still on `beta`.
- There is no admin-center view of deleted agent objects; finding and purging them takes Graph.

Recommended path (provisional until step 3.1):

- One blueprint for the project; one agent identity per agent (SRE agent, access agent). Each agent then appears as itself in tokens and logs, and the blueprint is visible in its tokens (`xms_par_app_azp`), which the gateway can check.
- In Azure, the blueprint's credential is a managed identity used as a federated credential, so no secret exists. Local development needs a separate answer (step 3.1).
- Permissions start at none; grant each agent only what its tools need.
- Fallback if Agent ID breaks or blocks a later step: a managed identity or app registration per agent.

Still to check later: the access agent's on-behalf-of flow with an agent identity (step 4.2); neither agent appears to need an agent's user account, which exists for resources that require a user, such as a mailbox.
