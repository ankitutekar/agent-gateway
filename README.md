# agent-gateway

> **Status: work in progress.** Nothing here is usable yet.

A framework-agnostic governance gateway for AI agents on Azure. Agents hold no credentials and reach their tools (over MCP) and models only through the gateway, which authenticates each agent, enforces per-agent allowlists, screens tool output for prompt injection, checks intent, requires bound human approvals for risky actions, applies budgets and a kill switch, and audits every decision. A red-team suite running in CI shows which layer stopped each attack.

## Documentation

- [Architecture decision records](docs/adr/)
- [Learning log](docs/learning-log.md)

## Licence

[MIT](LICENSE)
