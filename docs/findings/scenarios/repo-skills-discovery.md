# Scenario: repo-skills-discovery

> **N=3 caveat.** Results below aggregate 3 trials per
> (fast-agent, model), run 2026-05-27. Cross-client coverage (codex,
> goose) is open — this page only covers the fast-agent matrix.

**MCP server:** [`olaservo/github-mcp-server@add-agent-skills`](https://github.com/olaservo/github-mcp-server/tree/add-agent-skills) with `--toolsets=all` · **Scenario YAML:** [`experiments/scenarios/repo-skills-discovery.yaml`](../../../experiments/scenarios/repo-skills-discovery.yaml) · **Probes:** the two new surfaces added by [github/github-mcp-server#2428](https://github.com/github/github-mcp-server/pull/2428)

## What this probes

The server-side demo of [SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640).
Two new primitives are exposed:

- **Per-repo resource template** — `skill://{owner}/{repo}/{skill_name}/{+file_path}`
  reads any file inside any skill in any GitHub repo, not just the
  ~28 bundled SKILL.md files the server ships.
- **`list_repo_skills` tool** — enumerates skills in a given repo.
  The SEP's designed discovery path is `completion/complete` on the
  URI template, but that's a UI-only method; autonomous agents need
  a tool primitive to walk the tree.

The prompt names the target repo (`anthropics/skills`) but not the
skill. The agent has to either call
`list_repo_skills(owner="anthropics", repo="skills")` and pick from
the returned list, or guess a URI shape and `resources/read` it
directly. Both paths exercise the per-repo template; we record
which one each agent chooses.

We target `pptx` rather than `pdf` because `pdf/SKILL.md` references
its companion files in uppercase (`FORMS.md`, `REFERENCE.md`) while
the actual files are lowercase — agents that follow the SKILL.md
text faithfully get 404s and the per-repo template appears broken
when it isn't. `pptx/SKILL.md` has consistent lowercase references.

## Why this server

`github-mcp-server` is the natural home for a per-repo skill
discovery primitive — the server already brokers PR/file/branch
access for repos the user has permission for. Adding skills as a
new dimension on top of an existing tool-rich, widely-deployed
server validates the "skills colocate with the system that owns
their domain" pattern.

## Setup

- Server runs with `DISABLE_INSTRUCTIONS=true` and `--toolsets=all`.
  The `--toolsets=all` flag is what exposes the new `list_repo_skills`
  tool + per-repo resource template; default toolsets omit them.
- No PR scaffolding — `anthropics/skills` is consumed as a stable
  external corpus.
- Verify exposure before running:
  ```bash
  curl -sX POST "$MCP_SERVER_URL" -H "Authorization: Bearer $(gh auth token)" \
       -H "Accept: application/json, text/event-stream" \
       -H "Content-Type: application/json" \
       -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
    | grep -o '"list_repo_skills"' || echo "MISSING — relaunch with --toolsets=all"
  ```

## Cross-model findings (fast-agent, 8 models × 3 reps)

| Model | Picked | Tools/rep | Meta-skill read first? | Alternate peek | Median wall-clock |
| :--- | :--- | ---: | :---: | :--- | ---: |
| Claude Haiku 4.5 | `pptx` 3/3 | 4–5 | yes (3/3) | — | 38s |
| Gemini 3.5 Flash | n/a † | 21 (cap) | yes (3/3) | tree+file_contents fallback | 71s ‡ |
| GPT-5.5 (patched) | `pptx` 3/3 | 5 | yes (3/3) | `editing.md` (3/3) | 67s |
| DeepSeek v4 Pro | `pptx` 3/3 | 4–5 | **no (0/3)** | `xlsx`, `theme-factory` | 56s |
| Kimi K2.6 | `pptx` 3/3 | 3–4 | **no (0/3)** | — | 58s |
| MiniMax M2.7 | `pptx` 3/3 | 3–4 | yes (3/3) | — | 63s |
| Qwen 3.7 Max | `pptx` 3/3 | 3 | **no (0/3)** | — | 41s |
| GLM 4.6 | `pptx` 3/3 | 4–5 | **no (0/3)** | `xlsx` (1/3) | 91s |

† Gemini activated the skill, found `pptx`, even called the
per-repo `read_skill` on `pptxgenjs.md` correctly — but never
emitted final text. Same call-binding bug as pr-review.
See [fast-agent fork bugs](../../experimental-findings.md#fast-agent-fork-provider-bugs-discovered-during-cross-model-runs).

‡ Gemini's median is wall-clock to cap, not time-to-complete.

### Two discovery patterns coexist in the matrix

**Pattern A: meta-skill-first (read the protocol, then walk).**
Used by Haiku, gpt-5.5, MiniMax, and Gemini (the broken-output
one). The agent reads `skill://github/discover-mcp-skills/SKILL.md`
to learn the per-repo discovery convention, *then* calls
`list_repo_skills` against the named repo. Total: 5 tools when
the chosen skill has one referenced file (e.g. `pptxgenjs.md`),
6 when it picks two (e.g. + `editing.md`).

**Pattern B: skip-the-meta-skill, call the tool directly.**
Used by DeepSeek, Kimi, Qwen, and GLM. The agent calls
`list_repo_skills(owner="anthropics", repo="skills")` as its very
first tool call, no meta-skill read. Saves one tool call (3–4
total). Both patterns produce correct outputs — there's no
detectable quality difference, just style.

**Why does the split exist?** The OpenRouter-routed models (all
four pattern-B agents) appear to be biased toward calling a named
tool when the prompt names a repo. The meta-skill-readers
(Anthropic, OpenAI, Google) seem to default to "read the docs
first." This is a tentative observation across 8 models — N=3
isn't enough to claim it's a provider-routing pattern vs a
training-data pattern.

### Alternate-candidate peeking is a DeepSeek/GLM quirk

DeepSeek explicitly read `xlsx/SKILL.md` (rep 1) and
`theme-factory/SKILL.md` (rep 2) before committing to `pptx`.
GLM did the same with `xlsx` on rep 1. The other models picked
`pptx` from the `list_repo_skills` returned list and committed
without alternate reads. Worth a note for anyone interpreting
tool counts — these "extra" reads aren't waste, they're
exploratory and the model resolved them correctly.

### Gemini activated but couldn't produce output

This is worth distinguishing from "Gemini failed activation."
The Gemini reps *did* find `pptx`, *did* read its referenced
`pptxgenjs.md` via the per-repo template (and `editing.md` on
rep 2). The activation primitive worked. What didn't work was
emitting a final assistant response — the agent kept making
duplicate `list_repo_skills` calls until the harness cap fired.
Reps 1 + 3 also tried fallback `get_repository_tree` /
`get_file_contents` / `search_repositories` calls (the model
hunting for confirmation that the tool result it already had
was correct), which is consistent with the call-binding loss
described in the fast-agent bugs doc.

For Gemini specifically: **the SEP-2640 primitives work; the
fast-agent google-native provider doesn't surface their results
in a way Gemini can recognize as "this is the answer to the
call I just made."**

## Open questions

- The pattern-A vs pattern-B split (meta-skill-first vs
  direct-tool) — is this stable across runs with the same
  models? Worth re-running with N=5 to see whether the
  one-call-shorter discovery pattern is a property of those
  specific models or noise.
- The `discover-mcp-skills` meta-skill is currently optional —
  if the SEP wants the meta-skill read to be normative
  (so server-side observability sees a consistent first
  contact), it has to be either named in the prompt or
  surfaced more prominently in the `<available_skills>`
  catalog so pattern-B models don't skip it.

## Related

- Per-repo template specification: [SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640)
- Server implementation: [github/github-mcp-server#2428](https://github.com/github/github-mcp-server/pull/2428)
- Reproduce locally: [`run-scenario` skill — repo-skills-discovery sub-page](../../../.claude/skills/run-scenario/scenarios/repo-skills-discovery.md)
- Per-run JSON: `experiments/results/*-repo-skills-discovery-fast-agent-*.json`
