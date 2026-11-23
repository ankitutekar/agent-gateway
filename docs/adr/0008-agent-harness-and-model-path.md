# 8. Agent harness and model path

- **Status:** Accepted; smoke-test results added 2026-11-21 (see [Results](#results-of-the-live-smoke-test-2026-11-21))
- **Date:** 2026-11-19

## Context

Step 1.3 builds the tool-use loop (the "harness") that both agents will use. It needs a way to call models. The choice decides which API format every model call uses, and those requests are what the gateway will inspect and forward from step 1.5.

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
| API format | OpenRouter **Chat Completions**, behind a `ModelClient` interface in the harness. (Both of OpenRouter's formats are JSON; they differ in field names and in how a conversation is laid out. Called "wire format" until 2026-11-23, D32.) |
| Fallback | If Claude features break through Chat Completions (history check, strict tool arguments, pinning), add a second backend for OpenRouter's Anthropic-compatible Messages endpoint and route Claude through it. Agent code does not change. *Built and tested in step 1.3; not in use (see Results).* |
| Model | Claude Sonnet 5.5 to start, with `effort` set explicitly. |
| Pinning | Every request sends `provider: {only: [...], allow_fallbacks: false, require_parameters: true}` and never a fallback model list. The harness checks the returned `model` and `provider` and fails if they differ. |
| Data, default route | Pinned to Anthropic; `data_collection: deny`; OpenRouter prompt logging off; OpenRouter zero data retention (ZDR) not enforced. Anthropic's standard retention is an accepted risk (fixtures are synthetic). |
| Alternative route | ZDR on, pinned to Amazon Bedrock. Tested in the 1.3 smoke test so switching later is a known quantity. |

Rules the harness follows on any route:

- **History is append-only.** Reasoning details are replayed exactly as received. The gateway (1.5) forwards the agent's bytes unchanged and runs its checks on a parsed copy.
- **Every finish reason is handled.** A refusal arrives as HTTP 200, so the body is read, not just the status. A length stop with no visible answer is an error.
- **Tool arguments are validated in code**, whatever the provider promises about strict schemas: unknown fields are rejected and types are not coerced ("5" is not accepted as 5). The final answer is validated just as strictly; the harness refuses an answer model that allows extra fields (D32, from the sre-agent#3 review).
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
- **Pydantic AI and similar libraries.** Pydantic AI is a framework that owns the loop; thinner libraries hide the requests we want to govern.
- **Anthropic's OpenAI-compatible endpoint.** Ignores strict tool schemas, returns no reasoning and has no prompt caching.
- **Foundry-hosted models.** Out of scope for now.

## Results of the live smoke test (2026-11-21)

`sre-agent/scripts/smoke_openrouter.py`, run six times by the maintainer (about $0.40 in total). The last run covered four routes: Anthropic and Bedrock-with-ZDR, each over Chat Completions and over the Messages endpoint. The recordings are in `sre-agent/tests/recordings/openrouter/` and are replayed offline in CI.

| Check | Result |
|---|---|
| Two-tool toy task | Completes on all four routes |
| Pinning | Every reply came from the pinned model and provider (`Anthropic`, `Amazon Bedrock`). When an account setting removed the only allowed provider, the request failed with a 404 naming the reason: nothing was rerouted |
| Strict tool arguments | Always valid |
| Usage | Cost and cache-token counts in every response |
| Thinking | Sonnet 5.5 thinks adaptively and did **not** think on the toy task at medium or high effort. At effort `max`, on a task that needs planning, it thought on both API formats, and the thinking came back signed even when cut off by `max_tokens` |
| Cross-provider replay | Thinking from Anthropic's endpoint sent to Bedrock: a clear 400 ("encrypted reasoning … can only be processed by the provider that created it") |
| Edited history | The unedited history (control) was accepted, and **so was a copy with the readable thinking summary edited**, on both API formats |

What changed as a result:

- **The Messages-endpoint backend was built** (slice E, `OpenRouterMessagesClient`), when no reasoning came back through Chat Completions. Later runs showed the reason was the model choosing not to think, not a translation problem, so the fallback condition was not actually met. **R1 stays on Chat Completions** (decision D30, 2026-11-21). The Messages backend stays, tested, as a ready fallback. The backends live in `sre_agent.models`, outside the harness, which knows them only through the `ModelClient` protocol (D32). Each reply records its API format, and a backend refuses history from the other one.
- **Readable reasoning is not integrity-protected through this path.** With `display: "summarized"`, the readable text is a summary and the real reasoning travels encrypted in the signature. Either the summary is not checked, or the history check is not enforced for requests made through OpenRouter's account; the data cannot tell which (a signature-tamper test is deferred to a later phase). So the gateway enforces append-only history itself: it records assistant turns as received and checks them on replay (step 1.5). Audit records come from provider responses, not from replayed history. Tracked as a risk in the plan, and in threat model v2 (5.6).
- **Console settings are part of the trust boundary.** Two OpenRouter account settings overrode the code. An account-level "ZDR endpoints only" switch removed Anthropic's endpoint, and a stored bring-your-own Anthropic key (expired) was used instead of OpenRouter's own access. Both were removed. Error bodies also echoed the account's user id, so recordings strip it before they are saved.
- The harness asks for thinking explicitly (`reasoning.enabled: true` on Chat Completions; `thinking: {type: "adaptive", display: "summarized"}` on Messages), and the Messages backend reads Anthropic's own `thinking_tokens` count.

## Revisit if

- The smoke test shows Claude's history check or strict tool arguments failing through Chat Completions (switch Claude to the Messages-endpoint backend, which is built and tested).
- The edited-history replay test (`test_control_and_edited_history_replay`) starts failing after a re-recording: the provider began checking edited reasoning, and the consequence above changes.
- Real data, or a policy that rules out a third-party processor, enters the project.
- A demo needs streamed output, or long responses hit timeouts.
- OpenRouter's terms or data handling change (it agreed to be acquired by Stripe in August 2026).
