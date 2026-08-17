# Experimental Findings

> **Contributing findings?** See [#50](https://github.com/modelcontextprotocol/experimental-ext-skills/issues/50) for the contribution template proposal.

This page collects findings from **external implementations** and
cross-cutting community observations. For the WG's own cross-client
scenarios — what each one probes, why a particular MCP server, and
results per host — see **[findings/scenarios/](findings/scenarios/index.md)**.

## McpGraph: Skills in MCP Server Repo

**Repo:** [TeamSparkAI/mcpGraph](https://github.com/TeamSparkAI/mcpGraph)
**Skill:** [mcpgraphtoolkit/SKILL.md](https://github.com/TeamSparkAI/mcpGraph/blob/main/skills/mcpgraphtoolkit/SKILL.md) (875+ lines)

Bob Dickinson built a standalone SKILL.md file that lives in the same repo as the MCP server, but they weren't formally connected. The skill instructs agents on building directed graphs of MCP nodes to orchestrate tool calls.

**Findings:**

- Claude ignored the SKILL.md initially, even when the skill and server had similar descriptions
- Claude would fail at using the server tools a couple times, then read the skill and succeed
- Expected Claude to start with the skill ("I know how to do X") before the server ("I do X"), but it didn't

**Resolution:** Added a server instruction telling the agent to read the SKILL.md before using the tool. That one change caused Claude to reliably read the skill first.

**Remaining concerns:**

- This workaround works for 1:1 skill-to-server case, but doesn't solve discovery — users installing from a registry don't know to also install the skill
- Distinguishes between "skill required to make the server work at all" vs. "skill that orchestrates tools you could use without it" — potentially different solutions needed

## Skilljack MCP

**Repo:** [olaservo/skilljack-mcp](https://github.com/olaservo/skilljack-mcp)

Loads skills into tool descriptions. Uses dynamic tool updates to keep the skills manifest current.

Example eval approach and observations here: https://github.com/olaservo/skilljack-mcp/blob/main/evals/README.md

## FastMCP 3.0 Skills Support

**URL:** [gofastmcp.com/servers/providers/skills](https://gofastmcp.com/servers/providers/skills)

FastMCP added skills support in version 3.0. Worth examining for alignment with other approaches.

**Update model comparison (Feb 26 office hours):**

- FastMCP supports more of a "pull" model for updating resources that have changed
- The skills-as-resources implementation in this repo ([PR #16](https://github.com/modelcontextprotocol/experimental-ext-skills/pull/16)) watches for changes and allows clients to subscribe to resources via `resources/subscribe` and `resources/updated` notifications — more of a "push" model
- Both models are worth evaluating; the right choice is likely use-case specific

**Related:** [jlowin/fastmcp#2694](https://github.com/jlowin/fastmcp/issues/2694)

## PydanticAI Skills Support

**PR:** [pydantic/pydantic-ai#3780](https://github.com/pydantic/pydantic-ai/pull/3780)

Introduces support for agent skills with a tools-based approach.

## NimbleBrain: skill:// Resource Consolidation

[Mat Goldsborough](https://github.com/mgoldsborough) (NimbleBrain) had previously maintained separate components for MCP server code, a skills monorepo, and registry metadata with `server.json`. After community discussion, he consolidated into single atomic repos per server with skills exposed as `skill://` resources directly on the server.

**Findings:**

- Collapsing three separate artifacts into one repo simplified build, versioning, and deployment — skills are colocated with the tools they describe and shipped atomically
- `skill://` resources enable ephemeral/installless availability: skill context is present while the server is installed and disappears when it disconnects, with no git cloning or file system access required on the client side
- Quick tests showed same or better results compared to the previous approach of injecting skills upstream before the LLM call
- Validates the skills-as-resources approach documented in [Approach 3](approaches.md#3-skills-as-tools-andor-resources)

**Reference implementations:** [mcp-ipinfo](https://github.com/NimbleBrainInc/mcp-ipinfo), [mcp-webfetch](https://github.com/NimbleBrainInc/mcp-webfetch), [mcp-pdfco](https://github.com/NimbleBrainInc/mcp-pdfco), [mcp-folk](https://github.com/NimbleBrainInc/mcp-folk), [mcp-brave-search](https://github.com/NimbleBrainInc/mcp-brave-search)

**Community input:**

> "Skills living as skill:// resources on the server itself was the natural endpoint of that consolidation. The skill context is colocated with the tools it describes, versioned together, shipped together." — [Mat Goldsborough](https://github.com/mgoldsborough) (NimbleBrain), via Discord

## Cross-Model Activation Reliability (fast-agent, 8 models × 4 scenarios)

Sampled 2026-05-27. fast-agent client only; 3 trials per
(model, scenario) where measured. Detailed per-scenario tables
in [findings/scenarios/](findings/scenarios/index.md). This
section reports the cross-cutting headline: **which models
reliably activate skills via the MCP loading mechanism, and
which fail in what shape.**

| Model | pr-review | repo-skills | transformers-js | birch-html |
| :--- | :---: | :---: | :---: | :---: |
| Claude Haiku 4.5 | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ |
| Gemini 3.5 Flash | 0/3 (loop) | 0/3 (loop) | 0/2 (loop) | not measured |
| GPT-5.5 (fast-agent patched) | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ |
| DeepSeek v4 Pro | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ | 1/1 ✓ (53 min ⚠️) |
| Kimi K2.6 | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ | 1/2 (1 placeholder skip) |
| MiniMax M2.7 | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ | not measured |
| Qwen 3.7 Max | 3/3 ✓ | 3/3 ✓ | 3/3 ✓ | not measured |
| GLM 4.6 | 3/3 ✓ | 3/3 ✓ | **1/3 ✓** (2/3 skipped `read_skill`) | not measured |

The four meaningful patterns:

1. **Reliable activators.** Haiku, gpt-5.5, DeepSeek, Kimi,
   MiniMax, Qwen activate the skill on every measured rep. The
   downstream-quality divergence (workflow adherence, prescription
   honor rate) lives within "activation worked" — not at the
   loading boundary.

2. **Gemini loops on every scenario.** Skill *is* read (the call
   appears in the tool-call history), but the model fails to
   compose final assistant text within the harness's iteration
   cap. Root cause is in fast-agent's google-native provider,
   not the model — see [fast-agent fork bugs](#fast-agent-fork-provider-bugs-discovered-during-cross-model-runs).
   Resolved on `experimental/skills-over-mcp-v2-base`; needs
   re-running to confirm the in-matrix behavior. Findings here
   are from the original `experimental/skills-over-mcp-v2` run.

3. **GLM 4.6 silent-skip on transformers-js.** Reps 1 and 2
   wrote conforming-looking HTML *without ever calling
   `read_skill`* — used the model's training-data API surface
   (`@xenova/transformers`, the older v3 package) instead of
   the in-context skill's `@huggingface/transformers` v4
   guidance. Rep 3 read the skill and produced correct v4
   output. This is the cleanest "skill present in catalog, not
   triggered by the model" failure in the matrix: not a loop,
   not an error — just a model that decided it already knew the
   answer.

4. **DeepSeek argument-loss recovery loop on birch.** The agent
   read the skill correctly and tried to write the artifact,
   but the tool-call generation dropped the required `content`
   string field on 23 of 35 attempts. The model eventually
   recovered and produced a structurally correct artifact, but
   the rep took 53 minutes. Looks like a tool-call payload-size
   issue at the OpenRouter→DeepSeek route, not a fundamental
   activation problem. Worth re-testing with direct DeepSeek API
   or smaller artifacts.

### Prescription adherence is a separate dimension

Activation success is necessary but not sufficient. The
[transformers-js-demo](findings/scenarios/transformers-js-demo.md)
scenario probes one specific prescription in the skill body —
the `dispose()` memory-management rule, formatted as **bold + ⚠️
+ capital MUST**. Hit rates across the 18 reps where activation
succeeded:

| Model | `dispose()` hits |
| :--- | ---: |
| GPT-5.5 | **3/3** ⭐ |
| Haiku 4.5 | 1/3 |
| DeepSeek v4 Pro | 1/3 |
| Kimi K2.6 | 1/3 |
| MiniMax M2.7 | 1/3 |
| Qwen 3.7 Max | 0/3 |
| GLM 4.6 (when activated) | 0/3 |

Only GPT-5.5 consistently translates the bold/MUST formatting
into output. The middle band hits it about a third of the time.
Qwen and GLM never do. **Even with explicit emphasis, prescription
adherence varies by ~3× across the model fleet.** This generalizes
the earlier N=1 finding ("Haiku missed, codex got it, goose
missed") into a proper model-level adherence spectrum.

### Implication for the SEP

The cross-model data validates the load-via-`resources/read`
mechanism's portability: 6 of 8 models activate skills reliably
when the host wires the catalog through. The two failures are
host-side (Gemini, fixable in fast-agent) and model-side
(GLM 4.6, which sometimes decides it doesn't need to read).

The remaining open question — "does activation translate into
adherence?" — is *not* something the loading mechanism can
solve. Even with the bold/MUST/⚠️ skill formatting, only 1 of
6 reliable-activator models gets the prescription right
consistently. That's a separate research thread (probably
related to model post-training on instruction-following style),
which the SEP doesn't need to solve to be useful.

## Fast-agent Fork Provider Bugs Discovered During Cross-Model Runs

Three bugs in [`olaservo/fast-agent@experimental/skills-over-mcp-v2`](https://github.com/olaservo/fast-agent/tree/experimental/skills-over-mcp-v2)
surfaced while running the cross-model matrix. All three are
upstream/host-side, not model-side.

> **Update:** All three bugs are resolved on
> [`olaservo/fast-agent@experimental/skills-over-mcp-v2-base`](https://github.com/olaservo/fast-agent/tree/experimental/skills-over-mcp-v2-base),
> which the harness now pins by default. The matrix findings
> below are the as-observed record from the original cross-model
> run; the resolution notes per-bug are added inline.

### Bug #1: `max_iterations=20` override on google-native provider

`fast_agent/llm/provider/google/llm_google_native.py:263`
sets `max_iterations=20`, overriding the package-wide default of
99 from `fast_agent/constants.py:49`. The Anthropic and OpenAI
providers don't override (inherit 99). When a scenario takes more
than 20 tool-call/response cycles to complete, the Google native
provider truncates the run silently — `_done = True`, no error,
empty `final_text`.

This isn't itself the loop's root cause (Gemini loops within the
cap), but it bounds Gemini runs at ~21 iterations vs Anthropic's
99, masking the loop's actual length and the model's
self-correction potential.

**Resolution:** Fixed on `experimental/skills-over-mcp-v2-base`.
The google-native provider now uses `DEFAULT_MAX_ITERATIONS`
(99), matching the other providers.

### Bug #2: google-native converter drops the tool-call → tool-result binding

`fast_agent/llm/provider/google/google_converter.py:417-435`
builds the function-response message Gemini sees back from a
tool call:

```python
function_response_payload = {"tool_name": tool_name}
if textual_outputs:
    function_response_payload["text_content"] = "\n".join(textual_outputs)
fn_response_part = types.Part.from_function_response(
    name=tool_name,
    response=function_response_payload,
)
```

Two problems:
- **No `id` parameter** passed to `Part.from_function_response()`.
  `google-genai` ≥1.0 supports `id=` for binding a function response
  to a specific function call. fast-agent threads `tool_use_id`
  through internally but doesn't surface it to Gemini.
- **Custom payload shape.** The wrapper `{"tool_name": ..., "text_content": ...}`
  is non-standard. Gemini wasn't trained to recognize this as
  "the answer to the call I just made."

Compare the Anthropic converter
(`provider/anthropic/multipart_converter_anthropic.py:798-805`),
which builds:

```python
ToolResultBlockParam(
    type="tool_result",
    tool_use_id=sanitized_id,   # ← binds to the specific tool_use call
    content=tool_result_blocks,
)
```

The `tool_use_id` is what tells Claude "this is the answer to
call X, you don't need to call it again." Gemini doesn't get the
equivalent binding — only a bare function name and a non-canonical
payload key. **That's the call-binding bug** that causes Gemini
to re-call the same tool repeatedly.

**Resolution:** Fixed on `experimental/skills-over-mcp-v2-base`.
`convert_function_results_to_google` now takes
`(tool_name, tool_call_id, tool_result)` tuples and constructs
`types.FunctionResponse(..., id=tool_call_id, ...)` explicitly,
threading the call ID through to Gemini.

### Bug #3: openai-responses converter mis-routes TextResourceContents

`fast_agent/llm/provider/openai/responses_content.py:_tool_result_content_to_input_parts`
adds an extra user message containing per-content-block attachments
*on top of* the function_call_output that already carries the
text. For tool results that include `EmbeddedResource` with
`TextResourceContents`, the converter creates `{"type": "input_file",
"file_url": "<resource.uri>"}` — and OpenAI's Responses API treats
`input_file.file_url` as a URL it must fetch. For non-HTTP schemes
(`skill://`, `repo://`), the fetch fails with 400 `invalid_value
'Failed to download file'`, killing the run.

The text content is **already in `function_call_output.output`**
via `_tool_result_content_to_text`. The extra attachment is
either redundant (when the URI is fetchable) or fatal (when it
isn't).

**Resolution:** Fixed upstream via PR #804 (`4bda3af0`,
`fix responses input types for functions`), which is included on
`experimental/skills-over-mcp-v2-base`. The upstream fix refactors
`_convert_tool_results` to eliminate the dual-pathway entirely
(text and attachments now flow through a single `input_*` parts
list inside `function_call_output.output`), which supersedes the
local fork patch at commit `b6605c61` we used during the original
matrix run.

### Why these matter for the SEP

The bugs aren't blocking — three of four scenarios passed
without them on six of eight models, and the patched gpt-5.5
path works. **As of the switch to
`experimental/skills-over-mcp-v2-base`, all three are resolved
upstream and downstream consumers no longer need to patch.**
The historical concern remains relevant: the same bug shapes
could recur in other host implementations, and they're invisible
from outside.

For the SEP discussion specifically, this is a reminder that
**implementation defects in the host wrapper can look identical
to skill-loading failures from the outside**. Gemini "fails
activation" on the surface; the actual failure is a host-side
call-binding bug. A normative test suite for SEP implementations
should distinguish these cases — probably by requiring that the
host emit identifiable tool_call_id ↔ tool_result_id pairing
that the agent can refer back to.

## Skill Reliability and Adherence

Multiple community members have independently reported that models do not reliably load or follow skill instructions, even when skills are preloaded in context. This is a cross-cutting behavioral problem, not specific to any single implementation approach.

**Findings:**

- Models appear to frequently ignore available skills, requiring hooks or repeated prompting to trigger skill loading
- Skill adherence appears to be "time-decaying" similar to other model instructions — models follow instructions initially but lose adherence as the context window grows and compaction occurs
- Behavior is model-specific: weaker models show lower success rates with lazy-loaded skills
- One effective workaround observed by Kryspin: wrapping skills in a subagent whose name or description mentions the skill topic
- Community desire for "skill autoloads" and "dynamic memory autoloads" as design patterns

**Community input:**

> "Even Opus 4.6 needs to be constantly bugged to load skills when they're preloaded in the context already. I actually have a hook that reminds it to load skills and it still just doesn't a lot of the time." — Luca (AWS), via Discord

> "I also have this problem with skills: they're useful… when used. Which isn't nearly often enough." — Jeremiah (FastMCP), via Discord

> "Skills are ephemeral and/or time decaying — it clicks once and then give it some time and they lose the plot." — Kryspin (qcompute), via Discord

> "I've seen lazy load skills with various degrees of success, actually looks like it might be model specific… [best pattern is] putting them in with a subagent that similarly named or mentions the topic in their description." — Kryspin (qcompute), via Discord

**See also:** [#37](https://github.com/modelcontextprotocol/experimental-ext-skills/issues/37) — Compare skill delivery mechanisms: file-based vs MCP-based
