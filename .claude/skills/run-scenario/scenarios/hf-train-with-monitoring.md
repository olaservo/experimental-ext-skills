# Scenario: hf-train-with-monitoring

**Server:** hf-mcp-server :8083 (with `HF_JOBS_DRY_RUN=true`) · **YAML:** [`experiments/scenarios/hf-train-with-monitoring.yaml`](../../../../experiments/scenarios/hf-train-with-monitoring.yaml)

Cross-skill composition probe. Prompt: *"Fine-tune
`meta-llama/Llama-3.2-1B-Instruct` on `databricks/databricks-dolly-15k`
using Hugging Face Jobs, with Trackio alerts that fire on loss
spikes."* The `huggingface-llm-trainer` skill names "Trackio" by
topic, but the alerts API (`trackio.alert(...)`, webhook setup)
lives in a separate `huggingface-trackio` skill — no `skill://`
cross-references between them. The agent must independently activate
the second skill from `<available_skills>` catalog visibility.

## Reporting

```bash
grep -B 1 -A 40 "Ordered tool calls:" /tmp/verify-run.log
```

Report verbatim:

- The ordered tool-call list — note which `read_skill` / `read_mcp_resource`
  / `load_skill` targets appear (both `huggingface-llm-trainer` *and*
  `huggingface-trackio` are expected for full cross-skill composition).
- Any `hf_jobs` calls and what's in their `script` arg (a `trackio.alert`
  reference, `$HF_TOKEN`/secrets, etc.).
- `Wall-clock: ...`

## Synthesis vs activation

A submitted script can mention `trackio.alert` without the agent
having read `huggingface-trackio` — strong models can synthesize it
from training-data familiarity alone. The call list distinguishes
*catalog activation* (was the second skill actually read?) from
*content* (did the submitted script use the right API?) — both are
independent signals worth flagging separately when you describe the
run.
