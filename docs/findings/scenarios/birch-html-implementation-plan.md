# Scenario: birch-html-implementation-plan

> **N=2–3 caveat.** Most models in this matrix have 3 reps; Kimi
> K2.6 and DeepSeek v4 Pro have 2 and 1 respectively (DeepSeek's
> rep 1 took 53 minutes and reps 2–3 were skipped to bound cost;
> Kimi rep 3 was skipped after the failure pattern was clear).
> MiniMax/Qwen/GLM/Gemini were not measured. Treat single-trial
> outcomes as samples, not stable behavior.

**MCP server:** [`olaservo/birch-html@add-mcp-server-wrapper`](https://github.com/olaservo/birch-html/tree/add-mcp-server-wrapper) (stdio) · **Scenario YAML:** [`experiments/scenarios/birch-html-implementation-plan.yaml`](../../../experiments/scenarios/birch-html-implementation-plan.yaml) · **Skill:** [`birch-html`](https://github.com/olaservo/birch-html/tree/add-mcp-server-wrapper/skill)

## What this probes

Two firsts in the cross-scenario matrix:

- **Stdio transport.** Unlike pr-review/repo-skills-discovery/transformers-js-demo
  (all HTTP), the birch-html-mcp wrapper is a stdio Node binary
  that fast-agent spawns on connect. There's no port, no bearer
  token, and the connection lifecycle is bound to the agent
  process.
- **Persisted file artifact.** The harness uses a per-run dir
  under `experiments/.workspace/artifacts/birch-html-implementation-plan/<UTC-ts>/`
  instead of a tempdir. After the agent writes the HTML, the
  harness runs the skill's `finish_birch_html.py` postprocess
  to substitute `__BIRCH_SYSTEM_CSS__` with the canonical Birch
  CSS. A `.raw.html` copy is preserved alongside for forensics.

The grade target is the saved file's content, not the assistant's
text reply. Three signature markers come from the skill's output
contract:

- `__BIRCH_SYSTEM_CSS__` — canonical placeholder the skill demands
  be preserved until postprocessing. Models working without the
  skill emit inline CSS or external `<link>` and miss this entirely.
- `data-birch-system` — attribute on the placeholder's `<style>` tag.
- `class="page stack"` — required shell signature. Models default
  to `<body>` or a custom container without the skill.

## Why this server

Validates that the activation primitive works over stdio, not
just HTTP. A stdio server can't be probed externally (no port to
curl); the only verification path is "did the harness's agent
read the skill and produce conforming output." This is a tight
loop where any wrapper-level issue (auth, transport, MCP framing)
shows up immediately.

## Setup

- No external server health check. The harness verifies
  `mcp-server/dist/server.js` exists; if it doesn't, run
  `bootstrap.sh` or `npm install && npm run build` in
  `experiments/.workspace/birch-html/mcp-server`.
- fast-agent's `birch_skills` config entry spawns
  `node ${BIRCH_MCP_SERVER_DIST}` on connect.
- `include_instructions: false` — the `<available_skills>`
  catalog remains the only activation signal, same contamination
  control as the HTTP scenarios.

## Cross-model findings (fast-agent, 4 models measured)

| Model | Reps run | All 3 signature markers | Postprocess | Median wall-clock | Tools/rep | Notes |
| :--- | ---: | :---: | :---: | ---: | ---: | :--- |
| Claude Haiku 4.5 | 3 | 3/3 | exit=0 (3/3) | 37s | 2 | Clean: `read_skill` + `write_text_file`, done |
| GPT-5.5 (patched) | 3 | 3/3 | exit=0 (3/3) | 90s | 4–6 | Reads extra ref files, writes via PowerShell `execute` (heredoc) instead of `write_text_file`; rep 2 adds verification |
| DeepSeek v4 Pro | 1 † | 3/3 | exit=0 (1/1) | **3225s ⚠️** | 35 | 23 of 35 tool calls returned `Error: 'content' argument is required and must be a string` before the model recovered; eventually produced correct output |
| Kimi K2.6 | 2 ‡ | 1/2 ⚠ | exit=0 (2/2) | 526s | 4–12 | Rep 1: **missed `__BIRCH_SYSTEM_CSS__`** — inlined the actual CSS (42KB file vs others' ~10KB) instead of leaving the placeholder. Also tried to run the postprocess itself via PowerShell + `uv`. Rep 2: all 3 markers present. |

† DeepSeek reps 2–3 skipped to bound the 53-min-per-rep cost.
The pattern is reproducible but the failure mode is "recover
slowly," not "never recover."

‡ Kimi rep 3 was skipped after the placeholder-miss/postprocess-attempt
pattern was clear from rep 1.

Gemini 3.5 Flash, MiniMax M2.7, Qwen 3.7 Max, and GLM 4.6 were
not measured on this scenario. Gemini would almost certainly
loop ([fast-agent fork bugs](../../experimental-findings.md#fast-agent-fork-provider-bugs-discovered-during-cross-model-runs)).
The other three are reasonable next probes.

### The DeepSeek 53-minute argument-loss loop

The single most expensive run in the whole matrix. DeepSeek's
final tool-call list looked like this (compressed):

```
[0] read_skill skill://birch-html/SKILL.md
[1] read_skill skill://birch-html/resources/template.html
[2] read_skill skill://birch-html/references/implementation-plan.md
[3] read_skill skill://birch-html/recipes/implementation-plan.md
[4] write_text_file path="...dark-mode-implementation-plan.html"   ← missing content
[5..27] write_text_file (alternating errors and retries)            ← 23 of these
[28..34] write_text_file (eventually with content) + execute (postprocess attempts)
```

Each `write_text_file` call attempted with no `content` field
returned `Error: 'content' argument is required and must be a
string`. The model's recovery strategy was to retry the call,
sometimes also losing the `path` arg. After 23 retries it
eventually emitted a complete call and the artifact landed.

This looks like a tool-call payload-size issue on the OpenRouter
→ DeepSeek route — the birch artifact is ~16KB of HTML and the
model's JSON-mode tool-call generation appears to drop required
string arguments under load. Worth re-testing with `parallel_tool_calls=false`
or via a different provider (e.g. DeepSeek direct API) to confirm.

### The Kimi placeholder-skip failure (rep 1 only)

Kimi rep 1 wrote a 42KB raw file with the actual Birch CSS
inlined directly, skipping the `__BIRCH_SYSTEM_CSS__` placeholder
the skill's output contract requires. The agent then *tried to
run the postprocess script itself* via PowerShell + `uv run`,
searching the filesystem with `Get-ChildItem -Recurse -Filter
"finish_birch_html.py"` — which suggests it read the skill body's
"the harness will run the postprocess" instruction but didn't
register that the harness, not the agent, owns that step.

Kimi rep 2 followed the placeholder convention correctly. So
this is variance, not a stable failure — but a single rep
missing the placeholder is enough to break server-side
postprocess assumptions in production usage. Worth flagging
for Kimi-routed deployments.

### Behavioral observations across the matrix

- **gpt-5.5's PowerShell-execute pattern**: `[2] execute  {"command": "@'<heredoc>... 'dark-mode-implementation-plan.html'..."}`
  is genuinely a heredoc (PowerShell `@'...'@`) that writes the
  HTML via PowerShell's redirection instead of calling
  `write_text_file`. fast-agent ships a built-in `execute`
  tool (the `powershell` channel), and gpt-5.5 picks it over
  the MCP-provided write tool. Doesn't affect grading — the
  postprocess works on whatever file lands at the expected
  path — but it's a meaningful host vs MCP tool-selection
  signal.
- **Haiku is the fastest activator** by a wide margin (37s
  median vs 90s for gpt-5.5, 526s for Kimi). 2 tool calls,
  zero exploration of references/recipes.

## Open questions

- Does the DeepSeek argument-loss pattern reproduce on
  smaller artifacts (e.g. <5KB)? Or is the failure size-bound?
- Does any model that's *not* an Anthropic native call (the
  OpenRouter pool especially) succeed cleanly on first attempt?
  Kimi 1/2 and DeepSeek "yes-but-painfully" both come from
  OpenRouter; gpt-5.5 worked but takes 3× as long as Haiku.
  Either the activation+output-contract loop is genuinely
  harder for non-Anthropic models, or the OpenRouter routing
  is amplifying provider-side issues.
- The Kimi rep-1 placeholder skip — would a SKILL.md edit
  putting the placeholder mention at the top (rather than in
  the output contract section) raise the hit rate? Similar
  shape to the `dispose()` adherence question in
  [transformers-js-demo](transformers-js-demo.md).

## Related

- Reproduce locally: [`run-scenario` skill — birch-html-implementation-plan sub-page](../../../.claude/skills/run-scenario/scenarios/birch-html-implementation-plan.md)
- Per-run JSON: `experiments/results/*-birch-html-implementation-plan-fast-agent-*.json`
- Persisted artifacts: `experiments/.workspace/artifacts/birch-html-implementation-plan/<UTC-ts>/`
