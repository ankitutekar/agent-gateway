# 6. Threat-modeling method and repository layout

- **Status:** Accepted
- **Date:** 2026-11-15

## Context

Step 1.1 writes the project's first threat model ([`THREAT_MODEL.md`](../../THREAT_MODEL.md)), which later steps implement row by row. It needs a method that finds both ordinary software threats and agent-specific ones, ratings simple enough to apply consistently, and IDs that link each threat to its tests.

Separately, ADR 0001 started with one repository. While planning step 1.1, the agents' code was given repositories of their own, so each can grow independently and stand as a portfolio piece.

## Decision

**Method:** a mix of three lenses.

- Draw a **data-flow diagram** with trust boundaries, then apply **STRIDE** at each boundary to catch the classic threats (spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege).
- Tag every threat with its **OWASP** IDs (Top 10 for LLM Applications 2025, Top 10 for Agentic Applications 2026) and its **Google SAIF** risk or control area, to catch the agent-specific ones and make rows recognisable to reviewers.
- Rate **likelihood and impact** Low / Medium / High, before controls. Measurements from the baseline run (2.4) and the red-team suite (5.5) replace the guesses.
- Number threats `T01`, `T02`… and name tests after them (`T01-injection-in-log-line`), so a failing test points to its threat. Accepted risks are `R01`…
- Every threat names a planned control, a test and the plan step that builds it. Version 2 (step 5.6) updates the model with what the attacks showed.

**Scope docs:** one per agent, in `docs/agents/`, moving to each agent's repository when it is created.

**Repositories:** three.

- `agent-gateway`: the gateway, contracts, infrastructure, end-to-end red-team suite and the threat model.
- `sre-agent`: created at step 1.2.
- `access-agent`: created in Phase 4.

Each agent repository copies the gateway repository's CI, `make check`, ruleset and coding-agent guard hook. They share only the versioned contracts in `agent-gateway/contracts/`; the agent harness is copied, not shared.

## Alternatives considered

- **STRIDE only:** well known, but made for ordinary software; it has no words for goal hijack or tool poisoning.
- **SAIF or OWASP only:** agent-aware, but easy to miss classic gaps such as an unauthenticated approval endpoint or audit tampering.
- **Numeric risk scores (for example DREAD or CVSS):** more precision than the guesses can support at this stage.
- **One repository with agent directories:** less setup, but the agents could not grow or be shown on their own, and the boundary between platform and agent teams would be blurred.

## Consequences

- `THREAT_MODEL.md` lives at the root of `agent-gateway` and is the reference for later steps; the README will link threats to passing tests (7.5).
- Changes to the threat model come with the step that changes the design, and are noted in its change log.
- Three repositories mean three sets of CI and settings to keep in step; duplication is accepted, as it is for the copied harness.
- Cross-repository changes to contracts need a version bump in the contract and a follow-up in each agent repository.

## Revisit if

The model becomes too large to keep in one file, or the agent repositories turn out to need shared code beyond the contracts.
