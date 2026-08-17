# Scenario: pr-review

> **Sampling caveats.** The cross-client section below aggregates 5
> trials per client (all `claude-haiku-4-5`), run 2026-04-27. The
> cross-model section further down aggregates 3 trials per
> (fast-agent, model), run 2026-05-27 against the same scaffolded PR
> series on `olaservo/code-review-subject`. Treat individual outcomes
> as samples, not fixed behavior. Wrapper-level outcomes (which
> dispatch primitive each fork emits) are stable across trials;
> criterion-level outcomes are not.

**MCP server:** [`olaservo/github-mcp-server@add-agent-skills`](https://github.com/olaservo/github-mcp-server/tree/add-agent-skills) · **Scenario YAML:** [`experiments/scenarios/pr-review.yaml`](../../../experiments/scenarios/pr-review.yaml) · **Skill:** `pull-requests` (served as `skill://pull-requests/SKILL.md`)

## What this probes

Skill-access primitives at the tool-call boundary. The same PR-review
prompt runs across fast-agent, codex, and goose — each fork wraps the
underlying `resources/read` differently. The
`skill-read-before-write` criterion checks whether a resource read is
visible at the tool-call layer *before* any mutating PR tool. What
each fork actually emits matters:

- **fast-agent** → `read_skill(path=...)` — host-side wrapper that invokes `get_resource` underneath
- **codex** → `read_mcp_resource(uri=...)` — the MCP primitive directly
- **goose** → `load_skill(name=...)` — name-based helper; no `read_mcp_resource` visible at the tool boundary

One of the three (`load_skill`) hides the underlying resource read
from the tool-call boundary — whether it internally invokes
`read_mcp_resource` is unobservable from the agent or server side.
Wrappers that hide the read break server-side features keyed on
resource access: subscription-based updates (`resources/updated`),
access-based caching, telemetry.

## Why this server

`github-mcp-server` is tool-rich, widely deployed, and PR review is a
well-understood workflow with clear ground truth — that combination
makes adherence measurable. The skill teaches a multi-step orchestration
(`create_pending_review` → `add_comment_to_pending_review` (Nx) →
`submit_pending_review`); the host either follows that shape or it
doesn't, and the failure modes are easy to read.

## Setup

- Server runs with `DISABLE_INSTRUCTIONS=true` — required contamination
  control. The server's `instructions` field would otherwise leak skill
  activation hints; the only signal the model should get is the
  `<available_skills>` catalog.
- Each trial scaffolds a fresh PR via
  [`create-pr-input-validation.sh`](https://github.com/olaservo/code-review-subject)
  on `feature/input-validation-enhancement` so the subject under review
  is identical across trials and runs are independent.
- Trials are run sequentially (never two clients concurrent against
  the same server) because `_find_review_url` collides on the last
  review for the PR otherwise.

## Findings

Per-criterion pass rate (n/5 per client). Models per
[scenarios YAML](../../../experiments/scenarios/pr-review.yaml).

| Client | Wrapper observed | skill-read-before-write | create-pending-review | add-comment(s) | submit-pending-with-verdict | no-single-shot-bypass | **overall** |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| fast-agent | `read_skill(path=...)` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5/5** |
| goose | `load_skill(name=...)` | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | **5/5** |
| codex | `read_mcp_resource(uri=...)` | 2/5 | 4/5 | 2/5 | 0/5 | 1/5 | **0/5** |

Sample wall-clocks (median per client): fast-agent ~48s, codex ~165s,
goose ~206s. Codex and goose run substantially longer because their
default tool-output verbosity drives more tokens through the model.

### Two distinct outcome patterns, not a continuum

**fast-agent and goose: clean PASS.** Both hit all five criteria on
every trial. Wrapper choice (`read_skill` vs `load_skill`) doesn't
predict reliability — what matters is that the wrapper is *plumbed
through to the model* such that activation is the model's natural
first move. Both helpers shipped with this property in their
respective forks.

**codex: workflow shape broken.** A different failure mode entirely.
0/5 trials submitted properly (`submit-pending-with-verdict` 0/5,
verdict always `None`); 4/5 triggered single-shot bypass — the SEP
anti-pattern of `pull_request_review_write(method=create, event=...)`
in one call. When create-pending succeeds (4/5) the agent attaches at
most one comment (count=1 in 2/5 trials, count=0 in 3/5) before
attempting a malformed submit-shape. The skill is read in 2/5 trials,
but reading the skill doesn't fix the submission shape — codex's
`gpt-5.1-codex` consistently produces a different mental model of
"submit a review" that bypasses the staged-review workflow even when
the skill body says otherwise.

### Behavioral observations from N=5

- **fast-agent self-corrects mid-flow:** trial 1 emitted two
  `submit_pending` calls (verdicts `REQUEST_CHANGES` then `COMMENT`);
  the second is a no-op against an already-submitted review. The
  banner reports the first, which is the one that actually landed on
  the PR. Doesn't affect overall PASS but worth knowing — the agent
  sometimes attempts a verdict revision after the workflow has closed.
- **goose's planning interleaves with skill activation:** every trial
  emits at least one `todo__todo_write` before `load_skill`. Without
  `gate_tools: [pull_request_review_write, add_comment_to_pending_review]`
  in the scenario YAML's evaluator config (or the equivalent for
  pr-review's `MUTATING_TOOLS` list), the implicit fallback gate would
  treat the todo as the gate and fail goose for "skill-read after first
  call." `MUTATING_TOOLS` in the pr-review evaluator already does this;
  no scenario change needed.
- **codex's bypass pattern is consistent across trials:** the
  `bypass_indices` are clustered (e.g. `[6, 7, 8, 9]` in trial 4,
  `[7, 8, 9, 10]` in trial 5) — the agent fires a sequence of
  malformed `pull_request_review_write` calls in rapid succession,
  not a single mistaken call. This points at the model emitting a
  workflow shape it learned elsewhere and the wrapper not coercing
  it back into the staged-review path.

## Cross-model findings (fast-agent, 8 models × 3 reps)

> Run 2026-05-27. fast-agent client only. Each cell is 3 trials
> against scaffolded PRs #132–156 on `olaservo/code-review-subject`.
> The four cross-model probes are: does the model read the skill
> before mutating? does it follow the three-step pending-review
> workflow? does it handle the author-own-PR `REQUEST_CHANGES` fallback?
> does it produce a final assistant response?

| Model | Variant id | Activated | Workflow | Final text | Median wall-clock | Tools/rep |
| :--- | :--- | :---: | :---: | :---: | ---: | ---: |
| Claude Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001` | 3/3 | 3/3 | 3/3 | 53s | 11 |
| Gemini 3.5 Flash | `google.gemini-3.5-flash` | 3/3 † | 0/3 | 0/3 | 55s ‡ | 21 (cap) |
| GPT-5.5 | `responses.gpt-5.5` (patched) | 3/3 | 3/3 | 3/3 | 144s | 25 |
| DeepSeek v4 Pro | `openrouter.deepseek/deepseek-v4-pro` | 3/3 | 3/3 | 3/3 | 194s | 14 |
| Kimi K2.6 | `openrouter.moonshotai/kimi-k2.6` | 3/3 | 3/3 | 3/3 | 130s | 13 |
| MiniMax M2.7 | `openrouter.minimax/minimax-m2.7` | 3/3 | 3/3 | 3/3 | 268s | 11 |
| Qwen 3.7 Max | `openrouter.qwen/qwen3.7-max` | 3/3 | 3/3 | 3/3 | 152s | 18 |
| GLM 4.6 | `openrouter.z-ai/glm-4.6` | 3/3 | 3/3 | 3/3 | 85s | 11 |

† Gemini reads the skill but loops between `read_skill` and
`pull_request_read.get` indefinitely, hitting the harness's
turn cap without ever creating a pending review or emitting final
text. **Skill read happens, but the workflow doesn't execute** — see
the [fast-agent fork bugs](../../experimental-findings.md#fast-agent-fork-provider-bugs-discovered-during-cross-model-runs)
for the call-binding root cause.

‡ Gemini's median is per-rep wall-clock to cap, not time-to-complete.

### Cross-model wrapper observations

- **Author-own-PR `REQUEST_CHANGES` fallback**: GitHub rejects
  `REQUEST_CHANGES` from the PR author with `422`; agents must
  resubmit as `COMMENT`. Haiku, gpt-5.5, DeepSeek, Qwen, MiniMax,
  GLM all triggered the double-submit. **Kimi K2.6 is the
  exception** — it submitted as `COMMENT` on the first try in 2/3
  reps, recognizing the constraint proactively. Worth a follow-up
  read of its system-prompt awareness for GitHub PR conventions.
- **`read_skill` ordering** is not stable. Haiku reps 1+3 put
  `read_skill` at index [0], rep 2 read PR data first and the
  skill at [2]. gpt-5.5 reads the skill first then fetches 6–8
  source files via `get_file_contents` before commenting. DeepSeek
  puts `read_skill` at [0] every rep. The order varies but the
  *presence* of `read_skill` before any mutating call is stable
  across all non-Gemini models.
- **Qwen's argument-loss retry pattern**: Qwen reps 1+3 hit
  `Error: Could not resolve to a Repository with the name '/'` /
  `'/code-review-subject'` (empty owner string in `get_latest_review`
  args). The model recovered via `delete_pending` + retry but
  burned 2–6 extra tool calls per rep. Same root cause shape as
  DeepSeek's birch-html argument-loss loop, but Qwen recovers
  faster.
- **gpt-5.5 over-fetches context**: 24–26 tool calls vs Haiku's
  11–12. Most of the gap is `get_file_contents` reads of source
  files (validation.ts, todoStore.ts, package.json, etc.) before
  composing comments. Doesn't fail, just spends more time being
  thorough.
- **DeepSeek birch outlier (cross-scenario, not pr-review):**
  53 min single rep with 23 argument-loss errors on
  `write_text_file`. See [birch-html-implementation-plan](birch-html-implementation-plan.md).

### Comparison to prior single-trial findings

The 2026-04-23 single-trial findings reported goose FAIL on
`skill-read-before-write`. With N=5 on 2026-04-27, goose flipped to
consistent PASS (5/5) — the fork's `load_skill` wrapper now reliably
surfaces a name-matching dispatch ahead of mutating calls. Either the
fork tightened up between dates or the earlier observation was a
single-trial flake.

This is the kind of shift that vindicates moving from N=1 to repeated
sampling: a single trial would have led to "goose can't dispatch
skill-reads," which is no longer accurate.

## Open question

Should SEP require that skill access surface `read_mcp_resource` at
the tool-call layer? If yes, ergonomic name-based wrappers
(`load_skill`) still need to emit observable primitive calls. If no,
forks are free to hide the primitive but portability suffers for
server-side features that depend on observing resource reads.

## Related

- Per-client criterion code: [`experiments/harnesses/_common/evaluators/pr_review.py`](../../../experiments/harnesses/_common/evaluators/pr_review.py) — `SKILL_READ_ALIASES` encodes the harness author's editorial judgment about which dispatches satisfy the SEP per fork
- Reproduce locally: [`run-scenario` skill — pr-review sub-page](../../../.claude/skills/run-scenario/scenarios/pr-review.md)
- Per-trial logs (transient, this run): `/tmp/runs/pr-review/{client}-{N}.log`
