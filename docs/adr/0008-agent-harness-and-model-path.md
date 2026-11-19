# 8. Agent harness and model path

- **Status:** Accepted (smoke-test results to be added when step 1.3 finishes)
- **Date:** 2026-11-19

## Context

Step 1.3 builds the tool-use loop (the "harness") that both agents will use. It needs a way to call models. The choice decides which format every model call uses on the wire, and that format is what the gateway will inspect and forward from step 1.5.

What we want from the model path:

- **No vendor lock-in.** The project relies heavily on Azure, but the model path should not depend on one model vendor. Later (7.1) the same eval suite runs against several vendors' models, so switching models should be configuration, not a rewrite.
- **Wire visibility.** The gateway sits in the middle of these calls. We want to understand exactly what goes over the wire, and where untrusted tool output re-enters the conversation.
- **Strict typing** (pyright strict), offline tests in CI, and one live test run by the maintainer.
- **Claude first.** Claude 5.5 models have rules the loop must follow: reasoning ("thinking") must be sent back unchanged on every turn; edited history is rejected; forced `tool_choice` returns a 400 on Opus 5.5 and Sonnet 5.5.

Identity was not a deciding factor: each agent gets its own Entra identity whatever the model route, and the gateway, not the agent, holds the model key (step 3.6).

We commissioned two outside research reports (Claude on the web and Gemini) comparing the Anthropic SDK direct, OpenRouter through the OpenAI SDK, OpenRouter's own SDK, plain HTTP to OpenRouter, LiteLLM, thin multi-provider libraries, and compatibility endpoints. Both leaned towards Anthropic's own format. We chose otherwise, for the reasons below, with a tested fallback.

## Decision

| Topic | Decision |
|---|---|
| Framework | None. Our own small loop. |
| Route to models | **OpenRouter**, a hosted service that exposes many vendors' models through one API. |
| Client | **Plain HTTP** (`httpx`) with our own small typed models for the fields we use. No vendor SDK. |
| Streaming | Off at first: one complete response per request. |
| Wire format | OpenRouter **Chat Completions**, behind a `ModelClient` interface in the harness. |
| Fallback | If Claude features break through Chat Completions (history check, strict tool arguments, pinning), add a second backend for OpenRouter's Anthropic-compatible Messages endpoint and route Claude through it. Agent code does not change. |
| Model | Claude Sonnet 5.5 to start, with `effort` set explicitly. |
| Pinning | Every request sends `provider: {only: [...], allow_fallbacks: false, require_parameters: true}` and never a fallback model list. The harness checks the returned `model` and `provider` and fails if they differ. |
| Data, default route | Pinned to Anthropic; `data_collection: deny`; OpenRouter prompt logging off; OpenRouter zero data retention (ZDR) not enforced. Anthropic's standard retention is an accepted risk (fixtures are synthetic). |
| Alternative route | ZDR on, pinned to Amazon Bedrock. Tested in the 1.3 smoke test so switching later is a known quantity. |

Rules the harness follows on any route:

- **History is append-only.** Reasoning details are replayed exactly as received. The gateway (1.5) forwards the agent's bytes unchanged and runs its checks on a parsed copy.
- **Every finish reason is handled.** A refusal arrives as HTTP 200, so the body is read, not just the status. A length stop with no visible answer is an error.
- **Tool arguments are validated in code**, whatever the provider promises about strict schemas.
- The API key is read from the environment only and never logged.

## Consequences

- One API key reaches every vendor, and each response reports its own cost. A per-key spending cap gives a second cost stop beside the Azure budget.
- OpenRouter is a third party in the data path and its own outage domain. Pinning with fallbacks off means an outage fails closed. Threat model v2 (5.6) records it as a trust boundary and lists the retention trade-off as an accepted risk.
- OpenRouter charges 5.5% on credit purchases; model prices are not marked up.
- We write timeouts, retries and error types ourselves, and type only the part of the API we use.
- Turning on ZDR for Anthropic models on OpenRouter removes Anthropic's own endpoint. Sonnet 5.5 reasoning can only be replayed to the account group that produced it, so conversations cannot move between Anthropic and Bedrock mid-way.
- Cross-model results (7.1) partly measure OpenRouter's translation layer, so each result records the serving provider.

## Alternatives considered

- **Anthropic SDK, direct to Anthropic.** Full fidelity for Claude features, the shortest data path and a strictly typed SDK. But the agents would speak one vendor's format, and comparing other vendors would need adapters. Both research reports favoured it; we kept its strengths as the fallback route instead (Anthropic's format, via OpenRouter).
- **OpenAI SDK pointed at OpenRouter.** The most common setup. OpenRouter's own fields (reasoning details, provider, cost) become untyped extras under pyright strict, and the SDK follows OpenAI's direction (the Responses API), which is a different lock-in.
- **OpenRouter's official Python SDK.** Typed for OpenRouter's fields, but generated code that changes often, and it binds the code to OpenRouter's types.
- **LiteLLM.** Its PyPI package was compromised twice in 2026, it has documented workarounds that drop Claude reasoning, and as a proxy it duplicates the gateway we are building.
- **Pydantic AI and similar libraries.** Pydantic AI is a framework that owns the loop; thinner libraries hide the wire format we want to govern.
- **Anthropic's OpenAI-compatible endpoint.** Ignores strict tool schemas, returns no reasoning and has no prompt caching.
- **Foundry-hosted models.** Out of scope for now.

## Revisit if

- The smoke test shows Claude's history check or strict tool arguments failing through Chat Completions (switch Claude to the Messages-endpoint backend).
- Real data, or a policy that rules out a third-party processor, enters the project.
- A demo needs streamed output, or long responses hit timeouts.
- OpenRouter's terms or data handling change (it agreed to be acquired by Stripe in August 2026).
