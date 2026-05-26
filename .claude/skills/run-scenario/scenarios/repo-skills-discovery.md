# Scenario: repo-skills-discovery

**Server:** github-mcp-server :8082 (with `--toolsets=all` or `--toolsets=default,skills`) · **YAML:** [`experiments/scenarios/repo-skills-discovery.yaml`](../../../../experiments/scenarios/repo-skills-discovery.yaml)

The only read-only scenario against `github-mcp-server` — `pr-review` is the
other github-mcp-server scenario but mutates state; everything else runs
against `hf-mcp-server` or stdio `birch-html-mcp`. Probes the two new
surfaces added by [github/github-mcp-server#2428](https://github.com/github/github-mcp-server/pull/2428),
the server-side demo of [SEP-2640](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640):

- **Per-repo resource template** — `skill://{owner}/{repo}/{skill_name}/{+file_path}`
  reads any file inside any skill in any GitHub repo, not just the 28 SKILL.md
  files embedded in the server binary.
- **`list_repo_skills` tool** — enumerates skills in a given repo. The SEP's
  designed discovery path is `completion/complete` on the URI template, but
  that's a UI-only protocol method; autonomous agents need a tool to walk
  the tree, which is what this provides.

The prompt — *"I need to programmatically generate a slide deck presenting
quarterly business metrics... Check the skills available in the
`anthropics/skills` GitHub repository, pick the one that best fits this task,
read its documentation (including any referenced files), and outline an
implementation plan…"* — names the target repo but **not** the skill. The
agent has to either call `list_repo_skills(owner=anthropics, repo=skills)`
and pick from the returned list, or guess a URI shape and `resources/read`
it directly. Both paths exercise the per-repo template; we record which one
each client chooses. We target `pptx` rather than `pdf` because `pdf/SKILL.md`
references its companion files in uppercase (`FORMS.md`, `REFERENCE.md`)
while the actual files are lowercase — agents that follow the SKILL.md text
faithfully get 404s and the per-repo template appears broken when it isn't.
The `pptx` skill has consistent lowercase references.

## Setup

Same launch as `pr-review` — the existing `--toolsets=all` invocation already
exposes the new tools. The new surfaces are gated behind `skills`; if the
server is running on `--toolsets=default` they are absent and this scenario
degenerates into either an empty tool list or a stab at the bundled
`skill://github/...` namespace (which has no PDF skill). Verify exposure
before running:

```bash
curl -sX POST "${MCP_SERVER_URL:-http://localhost:8082/mcp}" \
  -H "Authorization: Bearer $(gh auth token)" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  | grep -o '"list_repo_skills"' || echo "MISSING — relaunch with --toolsets=all"
```

`DISABLE_INSTRUCTIONS=true` is still required (same reason as pr-review:
the legacy `instructions` field would leak activation hints and contaminate
the discovery signal). The `<available_skills>` catalog should be the only
hint the model gets.

No PR scaffolding runs — no `scaffolding_script` is declared, so the
scenario is read-only against the external repo and `anthropics/skills`
is consumed as a stable corpus, not mutated.

## Expected tool-call shapes

The two paths the agent may take, both valid:

- **Enumerate-then-read** (preferred for autonomous discovery):
  - `list_repo_skills(owner="anthropics", repo="skills")` → returns 17+ entries,
    each with a `skill://anthropics/skills/<name>/SKILL.md` URI and a short
    description.
  - `resources/read skill://anthropics/skills/<picked>/SKILL.md`
  - Optionally `resources/read skill://anthropics/skills/<picked>/<file>`
    for referenced files. For the `pptx` skill specifically, the SKILL.md
    points at `editing.md` (template-based path) and `pptxgenjs.md`
    (from-scratch path) — both lowercase, both resolvable via
    `skill://anthropics/skills/pptx/editing.md` and
    `skill://anthropics/skills/pptx/pptxgenjs.md`.

- **Guess-then-read** (older models, or models that skip the tool list):
  - Direct `resources/read skill://anthropics/skills/pptx/SKILL.md` without
    enumerating. Still hits the per-repo template; less robust against
    skill rename / addition.

The expected "right answer" is the `pptx` skill, but the model may
legitimately pick `canvas-design`, `web-artifacts-builder`, or compose
multiple. Record which one and don't grade — the harness no longer
evaluates scenario output (commit `5d54a71`).

## Reporting

```bash
grep -B 1 -A 40 "Ordered tool calls:" /tmp/verify-run.log
```

Report verbatim:

- The ordered tool-call list — separating bundled namespace reads
  (`skill://github/...`, e.g. `discover-mcp-skills`) from per-repo template
  reads (`skill://anthropics/skills/...`). Both can legitimately appear in
  one run.
- Whether `list_repo_skills` was called, and if so with what arguments.
- The chosen skill (which `skill_name` ended up in the read URIs).
- Any reads of relative files inside the skill (the `{+file_path}` part of
  the template firing on something other than `SKILL.md`).
- The final plan output (last assistant message).
- `Wall-clock: ...`

## Known variance

- **Skill choice drift.** Open-ended discovery: `pptx` is the most likely
  pick, but `canvas-design` or `web-artifacts-builder` are reasonable
  alternates; some models read multiple before answering. Record without
  grading.
- **Branch drift.** `pptx/SKILL.md` documents two paths — `editing.md`
  (template-based) and `pptxgenjs.md` (from-scratch JavaScript). The
  prompt says *"programmatically generate"*, which biases toward
  `pptxgenjs.md`, but a model that picks the template path and reads
  `editing.md` is still exercising the per-repo template correctly.
- **Direct-read fallback.** Models that skip `list_repo_skills` and guess
  `skill://anthropics/skills/pptx/SKILL.md` directly are exercising the
  same template — note this as a finding (it's the SEP's *direct read*
  mode rather than the *autonomous discovery* mode), not a failure.
- **Bundled-namespace excursion.** Models occasionally read the
  `discover-mcp-skills` meta-skill (`skill://github/discover-mcp-skills/SKILL.md`)
  first to learn the discovery protocol, then proceed to `list_repo_skills`.
  This is the meta-skill working as designed.
- **`anthropics/skills` corpus is upstream.** Skill count and file layout
  can change without notice. If a run produces fewer than ~15 skills from
  `list_repo_skills`, re-check the repo state before blaming the client.

## Goose-specific behavior

Same as `hf-jobs-plan`: Goose interleaves `todo__todo_write` calls with
skill activation. Note them in the report alongside the real activation
signal; they aren't graded.
