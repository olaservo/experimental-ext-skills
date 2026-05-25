# Scenario: hf-jobs-plan

**Kind:** `plan` · **Server:** hf-mcp-server :8083 (with `HF_JOBS_DRY_RUN=true`) · **YAML:** [`experiments/scenarios/hf-jobs-plan.yaml`](../../../../experiments/scenarios/hf-jobs-plan.yaml)

A real HF Jobs training prompt — *"Fine-tune
`meta-llama/Llama-3.2-1B-Instruct` on `databricks/databricks-dolly-15k`
using Hugging Face Jobs"* — gated by the dry-run intercept. The agent's
submitted script (the `script` arg of the `hf_jobs` call) is graded
for prescriptions from the `huggingface-llm-trainer` skill: PEP 723
metadata, `HF_TOKEN` secret forwarding, Trackio instrumentation.

## Reporting

```bash
grep -B 1 -A 40 "Ordered tool calls:" /tmp/verify-run.log
```

Report verbatim:

- The ordered tool-call list — note whether `read_skill` /
  `read_mcp_resource` / `load_skill` targets the
  `huggingface-llm-trainer` skill before any `hf_jobs` call.
- Any `hf_jobs` calls and what's in their `script` arg (PEP 723
  `# /// script` block, `$HF_TOKEN` / `secrets:` forwarding, Trackio
  references).
- `Wall-clock: ...`

## Goose-specific behavior

Goose's agentic planning interleaves `todo__todo_write` calls with
skill activation — expect to see those in the call list. They aren't
graded; just note them in the report alongside the real activation
signal.
