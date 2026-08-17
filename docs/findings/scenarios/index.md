# Cross-Client Scenarios

These scenarios run the same prompt across three MCP-aware clients
(fast-agent, codex, goose) pointed at a server that exposes
skills via `extensions["io.modelcontextprotocol/skills"]` +
`skill://` resource URIs. Each scenario is a small **probe** of one
specific aspect of skills-over-MCP — not a benchmark of model quality.
The point is to see whether the loading mechanism behaves consistently
across hosts, and where host implementations diverge.

If you're new here, **start with [pr-review](pr-review.md)** — it's the
most-replicated scenario and demonstrates the canonical setup.
[transformers-js-demo](transformers-js-demo.md) and
[repo-skills-discovery](repo-skills-discovery.md) probe complementary
loading aspects (code-output skill, per-repo template).
[birch-html-implementation-plan](birch-html-implementation-plan.md)
covers the stdio transport + persisted-artifact case.

| Scenario | What it probes | MCP server | Maturity |
| :--- | :--- | :--- | :--- |
| [pr-review](pr-review.md) | Skill-access primitives — how the three host wrappers (`read_skill`, `read_mcp_resource`, `load_skill`) surface a skill read at the tool-call boundary, and whether wrappers that hide the read break server-side observability | github-mcp-server (tool-rich, widely-deployed proxy for real PR-review work) | Stable — N=5 per client; 8-model N=3 fast-agent matrix |
| [repo-skills-discovery](repo-skills-discovery.md) | Per-repo resource template `skill://{owner}/{repo}/{skill_name}/{+file_path}` and `list_repo_skills` tool — the server-side demo of [SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640) and [github-mcp-server#2428](https://github.com/github/github-mcp-server/pull/2428) | github-mcp-server (`--toolsets=all` exposes the new primitives) | 8-model N=3 fast-agent matrix |
| [transformers-js-demo](transformers-js-demo.md) | Code-output skill — whether a skill bundling 7 reference files reliably steers code generation onto the right API (`@huggingface/transformers`, `pipeline()`, `dispose()`) when untrained agents tend to hallucinate older APIs | hf-mcp-server (authoritative knowledge near the model registry — exercises the skills-as-resources idea) | 8-model N=3 fast-agent matrix |
| [birch-html-implementation-plan](birch-html-implementation-plan.md) | Stdio transport + persisted file artifact — whether the activation primitive works without HTTP framing, and whether models conform to a structured output contract (placeholder + class signatures) | birch-html-mcp (stdio Node wrapper around the birch-html skill) | Partial fast-agent matrix; only Haiku and gpt-5.5 have N=3 |

## How to read these pages

Each scenario page has the same structure:

1. **What this probes** — the specific aspect of skills-over-MCP being tested
2. **Why this server** — what made this MCP server the right substrate
3. **Setup** — pointer to the scenario YAML and any server-side flags
4. **Findings** — what happened, per client
5. **Open questions** — what's worth probing next

For the runnable harness and full results JSON, see
[`experiments/`](../../../experiments/). To reproduce a scenario
locally, the [`run-scenario`](../../../.claude/skills/run-scenario/SKILL.md)
skill walks through preflight → run → report.

## Future probes

- **File-based skills as a baseline** — comparing the same scenarios
  against agents loading skills from a local directory (no MCP) would
  let us isolate what the MCP loading path adds vs. what's just
  "having the skill in context." Tracked separately.
