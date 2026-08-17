# Scenario: transformers-js-demo

> **Sampling caveats.** The cross-client section is single-trial
> (2026-04-23). The cross-model section below aggregates 3 trials per
> (fast-agent, model), run 2026-05-27 against the same hf-mcp-server.
> Treat individual outcomes as samples, not stable behavior.

**MCP server:** [`olaservo/hf-mcp-server@skills-over-mcp-experiment`](https://github.com/olaservo/hf-mcp-server/tree/skills-over-mcp-experiment) · **Scenario YAML:** [`experiments/scenarios/transformers-js-demo.yaml`](../../../experiments/scenarios/transformers-js-demo.yaml) · **Skill:** [`transformers-js`](https://github.com/huggingface/skills/tree/main/skills/transformers-js)

## What this probes

Code-output skill loading. The agent reads `transformers-js` (a
JavaScript-output skill bundling 7 reference files) and writes a
self-contained browser HTML demo. **No tool execution** — the artifact
is the agent's response itself. This swaps the loading mechanism's
target from a tool-call-shape skill (the previous three) to a
prose-output skill, and probes whether prominent in-body prescriptions
translate into the agent's output.

The three graded phrases come from the skill body specifically:

- `@huggingface/transformers` — the v4 package name. Untrained agents
  reach for the older `@xenova/transformers`.
- `pipeline()` — the API the skill leads with.
- `dispose()` — memory-management rule the skill flags with a ⚠️
  warning + capital MUST + bold formatting.

## Why this server

Authoritative knowledge for a JS library belongs near the registry of
that library's models — exercises the skills-as-resources idea where
the server attaches reference materials and the skill body points at
them. The 7 reference files (including official examples) are the
load-bearing part of this scenario, so the test is whether the host
follows the skill's pointers into those references when generating code.

## Findings

| Client + model | Activated? | Package | API | `dispose()` |
| :--- | :--- | :--- | :--- | :--- |
| fast-agent (claude-haiku-4-5) | yes | `@huggingface/transformers` | `pipeline()` | **missed** (39s wall) |
| codex (gpt-5.1-codex-mini) | yes | `@huggingface/transformers` | `pipeline()` | covered (30s wall) — **PASS overall** |
| goose (claude-sonnet-4-6) | yes | `@huggingface/transformers` | `pipeline()` | **missed** (~60s wall) |

All three clients activate the skill and pick up the prescribed
package + API; the divergence is on the `dispose()` memory-management
rule. **Prescription skimming** — in-body emphasis on a specific rule
(bold + ⚠️ + capital MUST) isn't sufficient to guarantee adherence
even when the skill is read. Only codex covered it; claude variants
(in fast-agent and goose) both skimmed past it.

## Cross-model findings (fast-agent, 8 models × 3 reps)

> Run 2026-05-27. fast-agent client only. Each cell is 3 trials
> against the same `hf-mcp-server@skills-over-mcp-experiment`.

| Model | Activated | `@huggingface/transformers` | `pipeline()` | `dispose()` | Median wall-clock |
| :--- | :---: | :---: | :---: | :---: | ---: |
| Claude Haiku 4.5 | 3/3 | 3/3 | 3/3 | **1/3** | 25s |
| Gemini 3.5 Flash | 0/2 † | n/a | n/a | n/a | 270s ‡ |
| GPT-5.5 (patched) | 3/3 | 3/3 | 3/3 | **3/3** | 17s |
| DeepSeek v4 Pro | 3/3 | 3/3 | 3/3 | 1/3 | 105s |
| Kimi K2.6 | 3/3 | 3/3 | 3/3 | 1/3 | 52s |
| MiniMax M2.7 | 3/3 | 3/3 | 3/3 | 1/3 | 42s |
| Qwen 3.7 Max | 3/3 | 3/3 | 3/3 | **0/3** | 34s |
| GLM 4.6 | **1/3** | 1/3 | 3/3 | 0/3 | 112s |

† Gemini's two reps both looped read_skill ↔ write_text_file
until the harness turn cap fired; the harness recorded `read_skill`
but the workflow never emitted final assistant text. Rep 3 was
skipped after the failure pattern was confirmed reproducible.

‡ Gemini median is wall-clock to cap, not time-to-complete.

### Skill-activation reliability is model-specific

The single most striking finding here is **GLM 4.6's 1/3
activation rate**: reps 1 and 2 wrote `sentiment-analysis.html`
*without ever calling `read_skill`*, drawing the API surface from
the model's training data instead of the in-context skill. The
generated files referenced `@xenova/transformers` (the v3-era
package name) rather than the `@huggingface/transformers` v4
package the skill teaches. Rep 3 *did* read the skill and produced
the correct v4 API.

Compare to Gemini, whose failure mode is different: it
**does** read the skill but then can't complete the workflow
because of a fast-agent provider-side bug ([details](../../experimental-findings.md#fast-agent-fork-provider-bugs-discovered-during-cross-model-runs)).
The signal there is wrapper, not model — GLM's signal is model.

For the model fleet that *does* activate reliably (Haiku, gpt-5.5,
DeepSeek, Kimi, MiniMax, Qwen), the divergence collapses to the
single bold-warning prescription:

### `dispose()` adherence is the canary

The skill body uses **bold + ⚠️ + capital MUST** for the `dispose()`
memory-management rule. Across the 18 reps where activation
succeeded:

| Model | `dispose()` hit rate |
| :--- | ---: |
| GPT-5.5 (patched) | **3/3** ⭐ |
| Haiku 4.5 | 1/3 |
| DeepSeek v4 Pro | 1/3 |
| Kimi K2.6 | 1/3 |
| MiniMax M2.7 | 1/3 |
| Qwen 3.7 Max | 0/3 |
| GLM 4.6 (when activated) | 0/3 |

Even with the bold + ⚠️ + capital MUST formatting, only GPT-5.5
consistently translates the rule into output. The middle band
(Haiku/DeepSeek/Kimi/MiniMax) hits it ~33%. Qwen and GLM never
do. This generalizes the earlier N=1 finding ("Haiku missed,
codex got it, goose missed") into a model-level adherence
spectrum — and reframes the open question.

## Open question

The dispose-rule miss is interesting on its own — *what makes a
SKILL.md prescription stick?* SKILL.md uses bold + ⚠️ + capital MUST
and still gets skimmed by 6 of 8 models we tested at sub-50% rate.
GPT-5.5 is the outlier. Lower-priority follow-up: probe whether
reorganizing the rule (top of file, code-block-first, code-comment
inside the canonical example, etc.) changes adherence rates for
the middle-band models.

## Related

- Each agentic client's planning step (`todo__todo_write` for goose,
  `list_mcp_resources` for codex) fires before skill activation —
  the harness's plan evaluator needed a small "neutral tools" set so
  the `skill-read-before-plan` fallback gate doesn't fire on these.
  The set is empirical (one entry per observed client), not a
  normative claim.
- Reproduce locally: [`run-scenario` skill — transformers-js-demo sub-page](../../../.claude/skills/run-scenario/scenarios/transformers-js-demo.md)
