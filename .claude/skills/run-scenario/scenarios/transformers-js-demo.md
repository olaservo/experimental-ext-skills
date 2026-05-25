# Scenario: transformers-js-demo

**Kind:** `plan` · **Server:** hf-mcp-server :8083 (with `HF_JOBS_DRY_RUN=true`) · **YAML:** [`experiments/scenarios/transformers-js-demo.yaml`](../../../../experiments/scenarios/transformers-js-demo.yaml)

Code-output skill probe. The agent reads `transformers-js` (a JS-output
skill bundling 7 reference files) and writes a self-contained browser
HTML demo in its assistant response. There is no execution and no
target tool call — the artifact *is* the response text. Tests the
loading mechanism on a code-output skill rather than a tool-call-shape
skill, and probes whether prominent in-body prescriptions translate
into the agent's output.

Three signature phrases from the skill body to look for in the agent's
final response (printed in full after the banner):

- `@huggingface/transformers` — the v4 package name. Untrained agents
  reach for the older `@xenova/transformers`.
- `pipeline()` — the API the skill leads with.
- `dispose()` — memory-management rule the skill flags with a ⚠️ warning.

## Reporting

```bash
grep -B 1 -A 40 "Ordered tool calls:" /tmp/verify-run.log
```

Report verbatim:

- The ordered tool-call list — note whether `read_skill` /
  `read_mcp_resource` / `load_skill` targets the `transformers-js`
  skill, and how many `references/*.md` reads followed.
- The final assistant response (also in the log) — eyeball the three
  signature phrases above.
- `Wall-clock: ...`
