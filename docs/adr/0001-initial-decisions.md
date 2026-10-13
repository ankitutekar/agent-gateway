# 1. Initial decisions

- **Status:** Accepted
- **Date:** 2026-10-13

## Recording decisions

Decisions are made late, at the step that needs them, and recorded in `docs/adr/`. Related decisions can share one file; a new file is added when a decision is big enough to stand alone. A changed decision gets a new ADR that supersedes the old one rather than editing it.

## Single repository to start

The original idea was three repositories (the gateway plus one per agent) to show the gateway is framework-agnostic. That costs coordination overhead (versioned contracts, three CI setups) before there is code to justify it.

- **Decision:** one public repository, `agent-gateway`, MIT licence. Contracts live in `contracts/` here.
- **Consequence:** where agent code lives (new repository or a directory here) is decided when agent work starts.
- **Revisit:** at the first step that produces agent-side code (incident fixtures or the agent harness).

## Plan kept outside the repository

The project plan is a personal working document that changes often and is written as instructions, not as system documentation.

- **Decision:** the plan lives outside this repository and is the source of truth; coding agents receive it as context. The repository records outcomes: ADRs, the learning log, code and docs.
- **Consequence:** ADRs must stand on their own without referring to plan text.
- **Revisit:** if losing plan history becomes a problem.
