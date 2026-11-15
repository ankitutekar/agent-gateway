# Access-request agent: scope

Version 1 · step 1.1 · 2026-11-15. Moves to the `access-agent` repo when it is created (Phase 4).

This is the agent's first governance document: what it is for, what it may and may not do, and how we judge it. The gateway's registry (1.4, 3.3) and the threat model ([`THREAT_MODEL.md`](../../THREAT_MODEL.md)) are checked against it.

## Goal

Handle group access requests for a signed-in employee. Given a request in plain language, work out what the user is entitled to and either:

- grant access that is auto-approvable,
- create a request for an approver when approval is needed, or
- refuse, saying so plainly, when the user isn't entitled to it.

It always acts **with the user's own rights** (the on-behalf-of flow, step 4.2), never with broader rights of its own.

## Users

- **Employee:** signs in and asks for access. May be honest, mistaken or malicious.
- **Manager (approver):** approves or denies requests for groups they own, directly through the gateway (4.4), not through the agent.

## Owner

The maintainer is the agent's **sponsor**: the named human accountable for it (ADR 0005).

## Tools (leaning; final list in step 4.3)

| Tool | Kind | Notes |
|---|---|---|
| `get_my_entitlements` | Read | The signed-in user's own entitlements only |
| `list_requestable_groups` | Read | Only groups this user may request; denials don't reveal others (T27) |
| `check_request_status` | Read | The user's own requests only |
| `create_access_request` | **Create** | For the signed-in user; rate-limited (T05, T13) |
| `grant_membership` | **Privileged** | Blocked without a matching, unexpired approval; requestable groups only (T04, T07–T11) |

## Data it touches

The signed-in user's entitlements and requests; names and descriptions of requestable groups (descriptions are untrusted input, T02). Test users and groups in a personal tenant (4.1); no real people's data.

## Rights

Its own agent identity, plus the signed-in user's delegated token. Which identity actually performs an approved grant is decided in 4.2; whichever it is can only touch requestable groups.

## Success criteria

- Legitimate requests succeed: auto-approvable ones are granted, the rest reach the right approver.
- Every request the user isn't entitled to is refused, and every confused-deputy attack fails **at the gateway**, even when the model is coaxed into trying (4.5).
- Each run ends with a decision record: what was asked, what was decided, why.

## Non-goals: it must never

- Grant anything the requesting user isn't entitled to, however persuasive the request.
- Grant privileged groups, or any group that isn't requestable.
- Approve requests. Only people approve, and never their own.
- Act for anyone other than the signed-in user.
- Reveal other users' memberships, or groups the user can't request.
- Remove members, create or change groups, or touch anything outside group membership.
