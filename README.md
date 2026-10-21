# agent-gateway

> **Status: work in progress.** Nothing here is usable yet.

A framework-agnostic governance gateway for AI agents on Azure. Agents hold no credentials and reach their tools (over MCP) and models only through the gateway, which authenticates each agent, enforces per-agent allowlists, screens tool output for prompt injection, checks intent, requires bound human approvals for risky actions, applies budgets and a kill switch, and audits every decision. A red-team suite running in CI shows which layer stopped each attack.

## Documentation

- [Architecture decision records](docs/adr/)
- [Advent of Agents Season 3 mapping](docs/season3-mapping.md) (each lesson, its Azure counterpart and the step that covers it)

## Development

Requires [uv](https://docs.astral.sh/uv/) and `make`.

```
make install   # install dependencies
make check     # lint, type check and test: what CI runs
```

## Licence

[MIT](LICENSE)
