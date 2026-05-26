---
name: run-scenario
description: Run a Skills-over-MCP cross-client scenario end-to-end against the right MCP server, execute the named client's harness, and report the criteria banner. The scenario YAML names the MCP server endpoint; harness behavior follows from structural signals (alias prefix picks the auth token; `scaffolding_script` triggers fresh-PR setup). `pr-review` is the only state-mutating scenario (scaffolds a PR on github-mcp-server); `repo-skills-discovery` is read-only against the same github-mcp-server exercising PR #2428's per-repo resource template; hf-jobs-plan / hf-train-with-monitoring / transformers-js-demo run against hf-mcp-server with `HF_JOBS_DRY_RUN=true`; `birch-html-implementation-plan` runs against the stdio `birch-html-mcp` wrapper and produces a real HTML file. Use when asked to run a scenario, reproduce Scenarios #1–#6, or test a client (fast-agent, codex, goose).
---

# run-scenario

One end-to-end scenario run against one client. Codifies the runbook
(preflight → scaffold → run → report) and the guardrails that aren't
obvious from reading the harness code alone.

## Inputs

- **client** (required): `fast-agent` | `codex` | `goose`.
- **scenario** (optional): scenario id (YAML filename stem). Default: `pr-review`.
- **model** (required — confirm with the user, even when defaulting): which
  model to test. The scenario YAML's `models.<client>` entry is the *default*,
  not a silent choice — different models are the whole point of the
  cross-client matrix, so always surface the option:
  - **fast-agent**: pick a `FAST_AGENT_VARIANT` (`anthropic` | `openai` |
    `google` | `openrouter`), or set `FAST_AGENT_MODEL=<id>` for an ad-hoc
    model (e.g. one of the OpenRouter alternates listed under the fast-agent
    section below). Variants resolve to the scenario YAML's
    `models.fast-agent.<variant>` map.
  - **codex**: scenario default, override with `CODEX_MODEL=<id>` (see
    pr-review sub-page for known-working TPM-tier combos).
  - **goose**: pick a `GOOSE_VARIANT` (`anthropic` | `openai` | `google` |
    `openrouter`), or set `GOOSE_MODEL=<id>` (paired with `GOOSE_PROVIDER`)
    for an ad-hoc model. Variants resolve to the scenario YAML's
    `models.goose.<variant>` map. Goose's openai provider auto-detects
    gpt-5+ models and routes them through `/v1/responses` transparently
    (`should_use_responses_api` in `openai.rs:269`), so `gpt-5.5` works
    via the openai variant without extra config.
- **pr_number** (optional, pr-review only): target a specific open PR
  instead of the auto-detected head of `feature/input-validation-enhancement`.

If invoked without an explicit client / model (e.g. bare `/run-scenario`),
ask the user via `AskUserQuestion` before preflight — one batched question
for client + scenario + model. Show the scenario default as the recommended
option; for fast-agent and goose, list their four variants. Skip the
question only if the user named all three in the same turn.

## Scenarios

The scenario YAML names the MCP server and (when it declares a
`scaffolding_script`) the PR scaffolding step. After preflight, **read
the matching sub-page below** for scenario-specific scaffold/banner/notes
— sub-pages are loaded on demand only.

| Scenario | Server | Sub-page | Probe |
| :--- | :--- | :--- | :--- |
| `pr-review` | github-mcp-server :8082 (scaffolds a PR) | [scenarios/pr-review.md](scenarios/pr-review.md) | Skill-access primitives across host wrappers (bundled `skill://github/...` namespace) |
| `repo-skills-discovery` | github-mcp-server :8082 (`--toolsets=all`) | [scenarios/repo-skills-discovery.md](scenarios/repo-skills-discovery.md) | Per-repo resource template `skill://{owner}/{repo}/{skill_name}/{+file_path}` + `list_repo_skills` tool (PR #2428) |
| `hf-jobs-plan` | hf-mcp-server :8083 | [scenarios/hf-jobs-plan.md](scenarios/hf-jobs-plan.md) | Submission output (PEP 723 + Trackio) under dry-run |
| `hf-train-with-monitoring` | hf-mcp-server :8083 | [scenarios/hf-train-with-monitoring.md](scenarios/hf-train-with-monitoring.md) | Cross-skill composition via catalog visibility |
| `transformers-js-demo` | hf-mcp-server :8083 | [scenarios/transformers-js-demo.md](scenarios/transformers-js-demo.md) | Code-output skill (HTML/JS, no execution) |
| `birch-html-implementation-plan` | birch-html-mcp (stdio) | [scenarios/birch-html-implementation-plan.md](scenarios/birch-html-implementation-plan.md) | Stdio transport + persisted file artifact (fast-agent only) |

For an outside-reader narrative on what each scenario probes and why
that specific MCP server, see [docs/findings/scenarios/index.md](../../../docs/findings/scenarios/index.md).

## Workspace assumptions

The skill resolves cross-repo paths from these env vars. First-time
contributors run `experiments/scripts/bootstrap.sh` to populate
`experiments/.workspace/` (git-ignored) with the canonical clones;
existing users with sibling clones export the env vars to point at
their own checkouts instead.

| Variable | Default | What it points at |
| :--- | :--- | :--- |
| `SUBJECT_REPO_DIR` | `experiments/.workspace/code-review-subject` | Clone of `olaservo/code-review-subject` (pr-review only — has the scaffold script) |
| `MCP_SERVER_DIR` | `experiments/.workspace/github-mcp-server` | Clone of `olaservo/github-mcp-server@add-agent-skills` (built binary lives here) |
| `HF_MCP_SERVER_DIR` | `experiments/.workspace/hf-mcp-server` | Clone of `olaservo/hf-mcp-server@skills-over-mcp-experiment` (`pnpm build` artifacts at `packages/app/dist/`) |
| `BIRCH_MCP_SERVER_DIR` | `experiments/.workspace/birch-html` | Clone of `olaservo/birch-html@add-mcp-server-wrapper` (`mcp-server/dist/server.js` is the stdio entry; `skill/scripts/finish_birch_html.py` is the postprocess) |
| `MCP_SERVER_URL` | `http://localhost:8082/mcp` | Where the github-mcp-server listens (pr-review) |
| `HF_MCP_SERVER_URL` | `http://localhost:8083/mcp` | Where the hf-mcp-server listens (plan scenarios) |
| `AGENT_SKILLS_ENV_FILE` | unset | Absolute path to a `.env` containing `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `HF_TOKEN` |

Defaults are relative to the WG repo root, so they work as-is when
Claude Code's CWD is somewhere inside this repo.

The fast-agent harness additionally needs a `fastagent.secrets.yaml`
next to `agent.py` so the OpenAI / Google / OpenRouter providers pick
up their API keys (Anthropic gets resolved via the SDK's default
env-var fallback, but the OpenAI-compatible providers don't). One-time
setup:
```bash
cp experiments/harnesses/fast-agent/fastagent.secrets.yaml.example \
   experiments/harnesses/fast-agent/fastagent.secrets.yaml
```
The template uses `${VAR}` interpolation against `$AGENT_SKILLS_ENV_FILE`,
so once you've sourced the .env (`set -a && . "$AGENT_SKILLS_ENV_FILE"
&& set +a`) every variant works without further setup. fast-agent's
`google` variant reads `GEMINI_API_KEY`.

## Workflow

### 1. Preflight

Read `experiments/scenarios/<scenario>.yaml` to determine which server
the scenario points at (`mcp_server.endpoint` / `mcp_server.transport`),
and whether it declares a `scaffolding_script` (only `pr-review` does).

**pr-review** — needs `github-mcp-server` on `:8082`:

```bash
curl -s -o /dev/null -w "%{http_code}" "${MCP_SERVER_URL:-http://localhost:8082/mcp}"
```
Expect `200`. If not running, launch from `$MCP_SERVER_DIR`:
```bash
cd "${MCP_SERVER_DIR:-experiments/.workspace/github-mcp-server}"
GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token) \
  DISABLE_INSTRUCTIONS=true \
  ./github-mcp-server.exe http --port 8082 --toolsets=all
```
`DISABLE_INSTRUCTIONS=true` is a required contamination control — the
server's `instructions` field would otherwise leak activation hints;
the only signal the model should get is the `<available_skills>` catalog.

**hf-mcp-server scenarios (hf-jobs-plan, hf-train-with-monitoring, transformers-js-demo)** —
need `hf-mcp-server` on `:8083` with the dry-run intercept:

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"preflight","version":"0"}}}' \
  --max-time 5 "${HF_MCP_SERVER_URL:-http://localhost:8083/mcp}"
```
Bare GET returns 400; the JSON-RPC POST above returns 200 when the
server is healthy. If not running, launch from `$HF_MCP_SERVER_DIR`:
```bash
cd "${HF_MCP_SERVER_DIR:-experiments/.workspace/hf-mcp-server}"
set -a && . "$AGENT_SKILLS_ENV_FILE" && set +a
DEFAULT_HF_TOKEN="$HF_TOKEN" \
  WEB_APP_PORT=8083 \
  HF_JOBS_DRY_RUN=true \
  node packages/app/dist/server/streamableHttp.js
```
`HF_JOBS_DRY_RUN=true` is required — `hf_jobs("uv", ...)` and
`hf_jobs("run", ...)` will otherwise submit real training jobs to the
account behind `HF_TOKEN`. The intercept returns a synthetic "captured
spec" response without contacting the API; the agent's submission
shape (script, secrets, hardware tier) is still graded from the call
args, just not executed.

The hf-mcp-server doesn't currently have a `DISABLE_INSTRUCTIONS` knob —
its `instructions` field has been edited to drop the skills-pointer
sentence (commit `9ed5f31` on `skills-over-mcp-experiment`) so it
shouldn't bias activation, but watch for regressions if the branch
moves.

**birch-html-implementation-plan (stdio transport)** —
the `birch-html-mcp` wrapper is a stdio Node binary, not an HTTP
service. fast-agent spawns it on connect using the `birch_skills`
entry in `fastagent.config.yaml` (`command: node`,
`args: ["${BIRCH_MCP_SERVER_DIST}"]`). There's no port to health-check
and no manual launch — just verify the built entry point exists:

```bash
test -f "${BIRCH_MCP_SERVER_DIR:-experiments/.workspace/birch-html}/mcp-server/dist/server.js" \
  && echo "ok" || echo "missing — run bootstrap.sh"
```

If missing, either re-run `experiments/scripts/bootstrap.sh` or build
manually:
```bash
cd "${BIRCH_MCP_SERVER_DIR:-experiments/.workspace/birch-html}/mcp-server"
npm install && npm run build
```

The wrapper has no authentication (stdio server, no bearer token),
so `setup_run` skips `HF_TOKEN`/`GITHUB_TOKEN` plumbing for this
scenario. `include_instructions: false` is still set in the
fast-agent config — the `<available_skills>` catalog remains the
only activation signal.

**LLM API keys.** If `$AGENT_SKILLS_ENV_FILE` is exported, use it;
otherwise ask the user for the path (do not cache in Claude memory —
it's per-user, not portable across sessions/machines):
```bash
set -a && . "$AGENT_SKILLS_ENV_FILE" && set +a
```
The codex runner instead expects the file via `uv run --env-file
"$AGENT_SKILLS_ENV_FILE"` — its child process needs the env, not the
parent shell. Plan scenarios additionally need `HF_TOKEN` exported so
the harness's `setup_run` can resolve auth for the `hf_skills` server.

### 2. Scaffold (pr-review only)

See [scenarios/pr-review.md](scenarios/pr-review.md). Skip when the
scenario YAML has no `scaffolding_script`.

### 3. Run the client harness

Per-client invocation from `experiments/harnesses/<client>/`. Always
redirect to a log file so the criteria banner survives the Bash-tool
30 000-char output truncation.

Each harness now runs the agent in a hermetic tempdir, so any
`write_file`/`write_text_file`/shell-curl-output goes to `$TEMP/skills-e2e-*`
and is discarded on exit — no more `*.html`, `dolly_*.json`, etc.
accumulating in the harness directories.

The examples below use one scenario YAML per client; substitute
`../../scenarios/<scenario>.yaml` for the scenario you're running.

**fast-agent** — Python library-embed. Windows: prepend
`PYTHONIOENCODING=utf-8 PYTHONUTF8=1` so Rich's block-drawing
characters don't crash the cp1252 console.

Source the .env once per shell so all provider keys are visible:
```bash
set -a && . "$AGENT_SKILLS_ENV_FILE" && set +a
```

The fast-agent harness exposes four named variants per scenario
(`FAST_AGENT_VARIANT=<name>`, default `anthropic`). The model behind
each variant is named in the scenario YAML's `models.fast-agent` map:

| Variant | Model ID | Source |
| :--- | :--- | :--- |
| `anthropic` (default) | `anthropic.claude-haiku-4-5-20251001` | Existing baseline — smallest Anthropic tier that reliably activates the skill. |
| `openai` | `responses.gpt-5.5` | Routes via fast-agent's `responses` provider (OpenAI's `/v1/responses` API) — required for gpt-5.5 with function tools + reasoning_effort; `openai.<model>` (chat completions) returns 400. Exercised in skilljack-evals CI. |
| `google` | `google.gemini-3.5-flash` | Quality winner in the user's fast-agent benchmark. Fall back to `google.gemini-3-flash` if rejected. |
| `openrouter` | `openrouter.deepseek/deepseek-v4-pro` | Primary OR candidate from skilljack-evals CI. First fast-agent run is also a smoke test. |

Ad-hoc-only OpenRouter models (set `FAST_AGENT_MODEL=<id>`, no variant
key needed) — pre-validated by the fast-agent benchmark:

| Model ID | Why it's here |
| :--- | :--- |
| `openrouter.minimax/minimax-m2.7` | Efficiency winner in the benchmark (17.64 score/min, 76.5 quality). Best for fast iteration. |
| `openrouter.moonshotai/kimi-k2.6` | Top OpenRouter quality (77.0); routed via Together. |
| `openrouter.qwen/qwen3.7-max` | Latest Qwen (max tier, not coder-specialized). Not yet in the benchmark. |
| `openrouter.z-ai/glm-4.6` | Zhipu GLM 4.6 — agentic-coding focused open-weights, not yet in the benchmark. |

Invocation:
```bash
cd experiments/harnesses/fast-agent

# Default Anthropic baseline (current behavior):
GITHUB_TOKEN=$(gh auth token) \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# OpenAI variant:
GITHUB_TOKEN=$(gh auth token) FAST_AGENT_VARIANT=openai \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# Google (Gemini) variant:
GITHUB_TOKEN=$(gh auth token) FAST_AGENT_VARIANT=google \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# OpenRouter variant (canonical = deepseek):
GITHUB_TOKEN=$(gh auth token) FAST_AGENT_VARIANT=openrouter \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# Ad-hoc model override (any provider; still works):
GITHUB_TOKEN=$(gh auth token) FAST_AGENT_MODEL=openrouter.minimax/minimax-m2.7 \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# HF scenarios (HF_TOKEN comes from $AGENT_SKILLS_ENV_FILE):
FAST_AGENT_VARIANT=openai \
  uv run agent.py ../../scenarios/hf-jobs-plan.yaml >/tmp/verify-run.log 2>&1
echo "exit=$?"
```

`FAST_AGENT_MODEL` overrides any variant lookup — useful for the
ad-hoc menu above, or for probing a model that isn't named in the
scenario YAML. An unknown variant fails fast with a "no fast-agent.X
entry" message.

**codex** — Python subprocess driving a built Rust binary. Loads env
via `--env-file` so the codex child process gets `OPENAI_API_KEY`
(mirrored to `CODEX_API_KEY` to force API-key auth over any cached
ChatGPT session) along with `HF_TOKEN`/`GITHUB_TOKEN`:
```bash
cd experiments/harnesses/codex
# pr-review:
GITHUB_TOKEN=$(gh auth token) \
  uv run --env-file "$AGENT_SKILLS_ENV_FILE" agent.py \
  ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1
# HF scenarios (HF_TOKEN sourced via --env-file):
uv run --env-file "$AGENT_SKILLS_ENV_FILE" agent.py \
  ../../scenarios/hf-jobs-plan.yaml >/tmp/verify-run.log 2>&1
echo "exit=$?"
```
Codex's TPM-tier sensitivity is scenario-specific — see
[scenarios/pr-review.md](scenarios/pr-review.md) for the
known-working `CODEX_MODEL` combo on the default 200K-TPM tier.

**goose** — Python subprocess driving `goose run --output-format
stream-json`. The harness writes a hermetic `GOOSE_PATH_ROOT` tempdir
with the MCP extension pre-configured; the user's `~/.config/goose/`
is never touched.

Source the .env once per shell so all provider keys are visible:
```bash
set -a && . "$AGENT_SKILLS_ENV_FILE" && set +a
```
The harness mirrors `GEMINI_API_KEY` → `GOOGLE_API_KEY` internally so
the same `.env` works for goose's google provider.

Like fast-agent, goose exposes four named variants per scenario
(`GOOSE_VARIANT=<name>`, default `anthropic`). The model behind each
variant is named in the scenario YAML's `models.goose` map — bare ids,
since goose takes provider + model as separate CLI flags:

| Variant | Model ID | Notes |
| :--- | :--- | :--- |
| `anthropic` (default) | `claude-sonnet-4-6` | Sonnet, not haiku — goose regresses on haiku under the activation primitive. |
| `openai` | `gpt-5.5` | Goose's openai provider auto-detects gpt-5+ models and routes to `/v1/responses` transparently (`should_use_responses_api` in `openai.rs:269`); for earlier models it uses chat-completions. No Responses fallback needed. |
| `google` | `gemini-3.5-flash` | Mirrored from `GEMINI_API_KEY`. Fall back to `gemini-3-flash` if rejected. |
| `openrouter` | `deepseek/deepseek-v4-pro` | Same primary OR candidate as fast-agent. |

Ad-hoc-only OpenRouter models (pair `GOOSE_PROVIDER=openrouter` with
`GOOSE_MODEL=<id>`) — mirrors the fast-agent ad-hoc list:

| Model ID | Why it's here |
| :--- | :--- |
| `minimax/minimax-m2.7` | Efficiency winner in the fast-agent benchmark. |
| `moonshotai/kimi-k2.6` | Top OpenRouter quality in the fast-agent benchmark. |
| `qwen/qwen3.7-max` | Latest Qwen (max tier, not coder-specialized). |
| `z-ai/glm-4.6` | Zhipu GLM 4.6 — agentic-coding focused open-weights. |

`GOOSE_MODEL` overrides any variant lookup — useful for the
chat-completions fallback above, or for probing a model that isn't
named in the scenario YAML. An unknown variant fails fast with a "no
goose.X entry" message.

Invocation:
```bash
cd experiments/harnesses/goose

# Default Anthropic baseline (current behavior):
GITHUB_TOKEN=$(gh auth token) \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# OpenAI variant (may 400 — see notes above):
GITHUB_TOKEN=$(gh auth token) GOOSE_VARIANT=openai \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# Google (Gemini) variant:
GITHUB_TOKEN=$(gh auth token) GOOSE_VARIANT=google \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# OpenRouter variant (canonical = deepseek):
GITHUB_TOKEN=$(gh auth token) GOOSE_VARIANT=openrouter \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# Ad-hoc model override (pair with GOOSE_PROVIDER for non-default provider):
GITHUB_TOKEN=$(gh auth token) GOOSE_PROVIDER=openai GOOSE_MODEL=gpt-5-mini \
  uv run agent.py ../../scenarios/pr-review.yaml >/tmp/verify-run.log 2>&1

# HF scenarios (HF_TOKEN comes from $AGENT_SKILLS_ENV_FILE):
GOOSE_VARIANT=openrouter \
  uv run agent.py ../../scenarios/hf-train-with-monitoring.yaml >/tmp/verify-run.log 2>&1
echo "exit=$?"
```

Note: goose does not run `birch-html-implementation-plan` — that scenario
uses a stdio MCP server and goose's harness only writes
`streamable_http` extension config today.

### 4. Report

Grep the log for the banner:

```bash
grep -B 1 -A 40 "Ordered tool calls:" /tmp/verify-run.log
```

The harness no longer grades runs against acceptance criteria — it just
records what tools the client invoked. Report:

- The ordered tool-call list verbatim (name + args preview).
- For pr-review: the `Review URL:` line.
- For artifact-producing scenarios (birch-html): the `Artifact:` /
  `Raw:` / `Postprocess:` lines.
- The `Wall-clock: ...` line.
- Any self-correction patterns (e.g. `delete_pending` then re-create,
  re-reading the skill mid-task) — behavioral observations worth
  flagging even though they're not pass/fail.

The full call list (including arg bodies stripped from stdout for
brevity) lives in `experiments/results/<ISO-UTC>-...-<client>-<model>.json`
under `tool_calls`.

## Constraints

- **Never run two client harnesses concurrently against the same
  server.** For pr-review they share the subject PR — `_find_review_url`
  grabs the last review on the PR via `gh api`, so another client
  posting during your run leaks into the URL you report. For read-only
  scenarios, concurrent runs may interleave dry-run intercept logs and
  confuse server-side telemetry. Each client's tool-call history is
  process-local and safe; the URL and any shared server state isn't.

- **Codex binary**: install via `cargo install --git
  https://github.com/olaservo/codex.git --branch skills-over-mcp
  --locked codex-cli`. That puts `codex` on PATH at
  `~/.cargo/bin/codex`; the harness's `shutil.which("codex")` picks
  it up. If your cargo prefix is non-default (e.g. `D:` to avoid
  filling `C:`), set `CODEX_BIN=/abs/path/codex.exe` — `which` only
  checks PATH.

  **PATH-shadowing trap.** If an upstream codex (e.g. npm
  `@openai/codex` at `~/AppData/Roaming/npm/codex` on Windows) appears
  on PATH ahead of the cargo build, `shutil.which("codex")` resolves
  to the upstream binary — which doesn't have the skills-over-mcp
  resource-read primitive. The run looks superficially fine (the
  harness exits, the JSON has tool_calls), but the call list never
  contains a `read_mcp_resource` / `read_skill` / `load_skill` and the
  agent typically times out chasing files via the github-mcp instead
  of activating the skill. Always set `CODEX_BIN` explicitly when
  another `codex` might be on PATH; `codex --version` of the fork
  reports `codex-cli 0.0.0`.

- **Goose binary**: install via `cargo install --git
  https://github.com/olaservo/goose.git --branch mcp-skills-sep
  --no-default-features --features rustls-tls --locked goose-cli`.
  Override path with `GOOSE_BIN=/abs/path/goose[.exe]`.

- **Do not modify** `fastagent.config.yaml` or `~/.codex/config.toml`
  to reach the MCP server. All runners inject server config in-memory
  (codex via `-c` flags, goose via temp `config.yaml`); global config
  edits create hidden state that contaminates future runs. fast-agent's
  `fastagent.config.yaml` IS in-tree but pre-declares both
  `github_skills` and `hf_skills` servers — the scenario YAML's
  `mcp_server.alias` selects which one.

- **Single-trial caveat.** Treat individual outcomes as samples,
  not stable behavior. Run a second pass before reporting "the model
  does X" rather than "the model did X this run."

## After the run

- The ordered tool-call list is the record. Compare it against the
  corresponding row of `docs/findings/scenarios/<scenario>.md` for this
  client + scenario + model.
- For anomalies (missing skill read, unexpected tools, premature
  `submit_pending` without comments, etc.), attach the
  `/tmp/verify-run.log` tail to the report — readers can scan the call
  list directly.
