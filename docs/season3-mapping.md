# Advent of Agents Season 3: lesson mapping

This project reimplements the themes of [Advent of Agents, Season 3](https://adventofagents.com/2026/10/) (October 2026) on Azure. The lessons build on Google Cloud; this file maps each one to its Azure counterpart and to the project step that covers it. Summaries are in my own words; follow the links for the lessons themselves.

Checked through Day 20 on 2026-10-21. Updated as lessons are published.

**Status:** Planned (a step covers it) · Candidate (decided when that step is reached) · Pattern only (no build, the idea is reused) · Done · Skipped.

| Day | Lesson | Question it answers | Google approach | Azure / project approach | Step | Status |
|---|---|---|---|---|---|---|
| [1](https://adventofagents.com/2026/10/01) | Agent development lifecycle | What phases does an agent go through, from idea to optimisation? | Five phases, Scope to Optimize | A short scope document per agent | 1.1 | Planned |
| [2](https://adventofagents.com/2026/10/02) | Threat modeling with SAIF | What can go wrong: injection, rogue tool calls, data disclosure? | Secure AI Framework (SAIF) | `THREAT_MODEL.md` linking each threat to a control and a test | 1.1, 5.6 | Planned |
| [3](https://adventofagents.com/2026/10/03) | Secure multi-agent architecture | How does a prototype become a hardened production system? | Gemini Enterprise, Agent Gateway | A gateway in front of every tool and model call | 1.5, 3.x | Planned |
| [4](https://adventofagents.com/2026/10/04) | Governance maturity model | How mature is our agent governance, layer by layer? | 15-item self-assessment across five layers | Scored at the end; baseline skipped (no agents yet, every item would be 0) | 7.7 | Baseline skipped |
| [5](https://adventofagents.com/2026/10/05) | One identity per agent | How does each agent prove who it is? | SPIFFE identity per agent | Entra Agent ID or a managed identity per agent | 0.5, 3.1, 3.2 | Planned |
| [6](https://adventofagents.com/2026/10/06) | Acting on behalf of the user | How does an agent act with only the signed-in user's rights? | Token delegation | Entra on-behalf-of (OBO) flow for the access agent | 4.2 | Planned |
| [7](https://adventofagents.com/2026/10/07) | Offline delegation | How does an agent act for a user who is not signed in, without broad rights? | Scoped offline refresh tokens | Entra refresh tokens with narrow scopes | 4.2 | Candidate |
| [8](https://adventofagents.com/2026/10/08) | Policies against dangerous tools | How do we stop an agent calling destructive tools? | IAM policies and tool deny rules in Agent Gateway | Per-agent tool allowlists in the gateway; custom RBAC role | 3.3, 6.2 | Planned |
| [9](https://adventofagents.com/2026/10/09) | Principal access boundaries | How do we cap what an agent can reach, even if a broad role allows more? | Principal Access Boundaries | Tight RBAC scope; deny assignments or Azure Policy | 6.2 | Candidate |
| [10](https://adventofagents.com/2026/10/10) | Prompt screening at the gateway | How do we catch injection hidden in content the agent reads? | Model Armor | Prompt Shields on tool outputs, plus gateway checks | 5.1 | Planned |
| [11](https://adventofagents.com/2026/10/11) | Redacting PII from prompts | How do we keep personal data out of the model's context and logs? | Sensitive Data Protection | Azure AI Language PII detection or Microsoft Presidio | 5.4 | Candidate |
| [12](https://adventofagents.com/2026/10/12) | Semantic policy in plain English | Is this tool call within what the agent should be doing? | Natural-language policies checked on every call | Content Safety Task Adherence compared with our own judge | 5.2 | Planned |
| [13](https://adventofagents.com/2026/10/13) | Code execution sandbox | How do we run code an LLM wrote without risk? | Isolated sandbox with state across turns | Container Apps dynamic sessions, egress off | 6.7 | Planned (stretch) |
| [14](https://adventofagents.com/2026/10/14) | Scanning skills before use | How do we stop poisoned tools or skills reaching agents? | CI scan before publishing to Agent Registry | Tool-description pinning; a CI scan as a candidate | 3.3, 5.5 | Planned + candidate |
| [15](https://adventofagents.com/2026/10/15) | Memory isolation | How do we stop memory leaking across users and teams? | Memory Bank scopes, IAM Conditions | Per-agent, per-user session partitioning | 3.3 | Planned (light) |
| [16](https://adventofagents.com/2026/10/16) | Agent payments | How do we make sure money moves only for what the user approved? | AP2 mandates for the exact cart | No payments here; approvals bound to the exact action reuse the idea | 4.4, 5.3 | Pattern only |
| [17](https://adventofagents.com/2026/10/17) | Infrastructure as code | How do we deploy agent infrastructure repeatably? | Terraform with Cloud Build deploys | Terraform roots run from a workstation; CI never touches Azure ([ADR 0003](adr/0003-azure-baseline.md)) | 0.3, 7.5 | Bootstrap done |
| [18](https://adventofagents.com/2026/10/18) | Agent registry | Where is the single list of agents and their tools? | Agent Registry | `agents.yaml` registry deployed with the gateway | 1.4, 3.3 | Planned |
| [19](https://adventofagents.com/2026/10/19) | Dynamic MCP governance | How do we avoid hardcoded tool endpoints and scattered credentials? | Runtime MCP discovery, central auth bindings | The gateway's MCP proxy routes tools and holds their credentials | 1.5, 3.6 | Planned |
| [20](https://adventofagents.com/2026/10/20) | Two gateways | How do we contain runaway loops and control egress? | Agent Gateway with Apigee | Token budgets, iteration ceilings (candidate), egress allowlist; APIM as a write-up | 5.4, 6.3, 7.5 | Planned + candidate |
