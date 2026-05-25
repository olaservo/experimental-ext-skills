# Scenario: birch-html-implementation-plan

**Kind:** `plan` · **Server:** birch-html-mcp (stdio) · **YAML:** [`experiments/scenarios/birch-html-implementation-plan.yaml`](../../../../experiments/scenarios/birch-html-implementation-plan.yaml)

File-output skill probe over stdio. The agent reads the `birch-html`
skill and writes a self-contained HTML implementation-plan artifact to
disk; the harness then runs the skill's `finish_birch_html.py`
postprocess so the file renders directly in a browser. Unlike #2–#4
the grade target is the saved file's content, not the assistant's text
reply. Probes two firsts in the matrix:

- **Stdio transport.** The wrapper from `olaservo/birch-html@add-mcp-server-wrapper`
  serves the skill as `skill://` resources but binds to stdio rather
  than HTTP. fast-agent's `birch_skills` config entry spawns
  `node ${BIRCH_MCP_SERVER_DIST}` on connect — there's no port and
  no bearer token.
- **Persisted file artifact.** The harness uses a per-run dir under
  `experiments/.workspace/artifacts/birch-html-implementation-plan/<UTC-ts>/`
  instead of a tempdir, so the file survives the run. The postprocess
  mutates the file in place to substitute `__BIRCH_SYSTEM_CSS__` with
  the canonical Birch CSS; a `.raw.html` copy is preserved alongside
  for forensics.

Three signature markers from the skill's output contract to look for
in the **raw** file (before postprocess substitutes the placeholder
away):

- `__BIRCH_SYSTEM_CSS__` — canonical placeholder the skill demands be
  preserved until postprocessing. Models working without the skill
  emit inline CSS or external `<link>` and miss this entirely.
- `data-birch-system` — attribute on the placeholder's `<style>` tag.
- `class="page stack"` — required shell signature. Models default to
  `<body>` or a custom container without the skill.

## Reporting

```bash
grep -B 1 -A 40 "Ordered tool calls:" /tmp/verify-run.log
```

Report verbatim:

- The ordered tool-call list — note whether `read_skill` targets the
  `birch-html` skill and which `references/` / `recipes/` files were
  read.
- `Artifact: /abs/path/to/<slug>.html` — the postprocessed, openable file
- `Raw: /abs/path/to/<slug>.raw.html` — preserved pre-postprocess copy
- `Postprocess: exit=0` — `ok` means the rendered file is browser-ready;
  any other value means the raw is still readable but won't render
- `Wall-clock: ...`

Eyeball the raw file (or `grep` for the three signature markers above)
to confirm the skill's output contract was followed.

## Inspecting the artifact

Each run writes under `experiments/.workspace/artifacts/birch-html-implementation-plan/<UTC-ts>/`.
After a green run there will be two files:

```
<slug>.html         # postprocessed; open in a browser to see the rendered plan
<slug>.raw.html     # exact bytes the model wrote (placeholder intact)
```

Open the rendered file:

```bash
# Windows
start "" "experiments/.workspace/artifacts/birch-html-implementation-plan/<ts>/<slug>.html"
# macOS
open "experiments/.workspace/artifacts/birch-html-implementation-plan/<ts>/<slug>.html"
```

If the page renders without any Birch styling, the postprocess didn't
run or its output was discarded. Re-check the `Postprocess:` line in
the banner — most common failure is missing `uv` on PATH or
`BIRCH_MCP_SERVER_DIR` not pointing at the cloned skill.

## Client coverage

fast-agent only. The codex and goose harnesses currently hard-code
`mcp_servers.<alias>.url=` flags and don't support stdio transport.
Adding them is a separate piece of work — needs a config-flag swap to
`command`/`args` (codex) and the equivalent in the temp config.yaml
(goose).
