# SRE agent: scope

Version 1 · step 1.1 · 2026-11-15. Moves to the `sre-agent` repo when it is created (step 1.2).

This is the agent's first governance document: what it is for, what it may and may not do, and how we judge it. The gateway's registry (1.4, 3.3) and the threat model ([`THREAT_MODEL.md`](../../THREAT_MODEL.md)) are checked against it.

## Goal

When an alert fires on the target app, investigate and return a **triage**: the likely cause, the evidence behind it, a proposed action, a confidence score, and whether a human needs to look. It may carry out a restart or a scale change, but only through the gateway and only when the gateway's rules allow it (approval required, step 5.3).

## Users

- **Engineer on call:** starts a triage, reads the report, decides what to do with it.
- **Alert system:** may start a triage automatically, with the alert as input.

## Owner

The maintainer is the agent's **sponsor**: the named human accountable for it (ADR 0005).

## Tools (leaning; final list in step 2.1)

| Tool | Kind | Notes |
|---|---|---|
| `query_logs` | Read | Time range and app from fixed lists; output capped |
| `get_metrics` | Read | Named metrics only |
| `list_recent_deploys` | Read | |
| `search_runbooks` | Read | Runbook text is untrusted input (T01) |
| `restart_app` | **Change** | Target app only; approval required; rate-limited (T22, T23) |
| `scale_app` (possibly) | **Change** | Target app only; replica cap; approval required (T22, T24) |

## Data it touches

Logs and metrics of the target app (which can contain secrets or personal data from requests), deploy history, runbooks. Fixtures in Phases 1–5; the live test app from Phase 6. No real customer data.

## Rights

Its own agent identity, with no Azure rights of its own. The SRE tool server acts on Azure with a custom role limited to the target app (6.2).

## Success criteria

- Schema-valid triage for every clean fixture (2.2).
- The right cause category on most clean fixtures; the threshold is set in 2.3.
- No forbidden action on any fixture, clean or poisoned: no change action without approval, none on anything but the target app.
- Says "needs a human" when the evidence is weak, rather than guessing.

## Non-goals: it must never

- Act on any resource other than the target app.
- Delete, redeploy, roll back or change configuration. Its only change actions are restart and scale.
- Send data anywhere except its report: no email, chat, web requests or links.
- Hold credentials or read secrets.
- Fix code or open pull requests.
- Be a capable, best-in-class SRE. It needs to be realistic and attackable; effort goes into governing it.
