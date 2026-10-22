# 5. Agent identity mechanism (provisional)

- **Status:** Accepted, provisional until step 3.1
- **Date:** 2026-10-22

## Context

Each of the project's agents needs its own identity, so the gateway can tell them apart, grant each only what it needs, revoke one without touching the other, and attribute every action. The two candidates were Microsoft Entra Agent ID, which is built for agents but was thought to be gated by Agent 365 licensing, and the general-purpose constructs (managed identities and app registrations). The licensing question could only be settled by trying, so step 0.5 ran a spike: [`docs/spikes/agent-id.md`](../spikes/agent-id.md).

The spike found Agent ID **available** on Microsoft Entra ID Free: a blueprint and an agent identity were created in the admin center, and the agent identity got its own access token through the two-step flow (the blueprint gets an exchange token for one agent, the agent trades it for a resource token). Only Conditional Access and ID Protection for agents need a paid licence.

## Decision

Use **Entra Agent ID**:

- **One blueprint** for the project, holding the only credential.
- **One agent identity per agent** (SRE agent, access agent). Each appears as itself in tokens and sign-in logs, and its token names its parent blueprint (`xms_par_app_azp`), which the gateway can check.
- **No secrets in Azure:** the blueprint's credential is a managed identity used as a federated credential. How agents get tokens in local development is decided in step 3.1.
- **Permissions start at none;** each agent is granted only what its tools need.
- **Sponsors** are the maintainer: a named human accountable for each agent, which Agent ID requires.

## Alternatives considered

- **A managed identity per agent.** No secrets and no new concepts, but a managed identity belongs to an Azure resource, so it does not fit agents that run locally or share a host, and nothing in the token marks it as an agent. Kept as the fallback.
- **An app registration (service principal) per agent.** Works anywhere, but each needs its own credential to manage, and nothing in the token marks it as an agent.
- **One shared identity for all agents.** Simplest, and exactly what this project argues against: the gateway could not tell agents apart, and revoking one would revoke all.

## Consequences

- The gateway authenticates agents by validating Entra tokens: audience, issuer, the agent identity's ID, and the parent blueprint.
- Conditional Access and ID Protection for agents are not available; the gateway's own policies do that job, and the README maps them to the enterprise features.
- Agent ID is new: docs lag the product, some Graph calls for agent identities are still `beta`, and the admin center has no view of deleted agent objects. Provisioning scripts (step 3.1) pin the API versions they use and are tested against the real tenant.
- The access agent's on-behalf-of flow with an agent identity is still untested (step 4.2).

## Revisit if

Step 3.1 or 4.2 hits something Agent ID cannot do on the Free tier, a licence requirement appears for the core objects, or the `beta` APIs change in a way that breaks provisioning.
