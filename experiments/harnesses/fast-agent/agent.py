"""Generic scenario runner for fast-agent — dispatches by scenario kind.

Exercises the activation primitive of the Skills-over-MCP SEP. For
`kind: pr-review`, the model must walk the three-step pending-review
workflow (Scenario #1). For `kind: plan`, the model must read the
named skill and produce a plan whose prose covers prescribed elements,
without ever calling the forbidden tools (Scenario #2).

SECURITY -- do not point this at untrusted repos / endpoints. PR
diffs and skill content are attacker-controlled on public sources;
hostile content can redirect the agent. Keep target endpoints sandboxed.

Pre-reqs vary by kind:
  pr-review: ANTHROPIC_API_KEY, GITHUB_TOKEN, MCP server on the scenario's
             endpoint without --read-only, and a reviewable PR (scaffold
             with `scaffolding_script` from the YAML).
  plan:      ANTHROPIC_API_KEY, MCP server on the scenario's endpoint.

Usage:
    cd experiments/harnesses/fast-agent
    GITHUB_TOKEN=$(gh auth token) uv run agent.py ../../scenarios/pr-review.yaml
    HF_TOKEN=hf_xxx              uv run agent.py ../../scenarios/hf-jobs-plan.yaml

Windows: prepend `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` so Rich's
block-drawing characters don't crash the cp1252 console.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import (  # noqa: E402
    load_scenario,
    parse_scenario_arg,
    report_and_save,
    setup_run,
)

from fast_agent import FastAgent  # noqa: E402


_REPO_ROOT = Path(__file__).resolve().parents[3]

# Birch-html stdio MCP server path. fastagent.config.yaml's birch_skills
# entry uses `args: ["${BIRCH_MCP_SERVER_DIST}"]`, so the absolute path
# has to be in the env BEFORE fast-agent loads the config (which happens
# at FastAgent() construction below). Exported unconditionally — it
# has no effect on scenarios that don't reference birch_skills.
_BIRCH_DIR = Path(
    os.environ.get("BIRCH_MCP_SERVER_DIR")
    or (_REPO_ROOT / "experiments" / ".workspace" / "birch-html")
).resolve()
os.environ.setdefault(
    "BIRCH_MCP_SERVER_DIST",
    str(_BIRCH_DIR / "mcp-server" / "dist" / "server.js"),
)

# fast-agent resolves `fastagent.config.yaml` at import; the @fast.agent
# decorator needs scenario values at module-import time. So this runs
# at module scope, not under `if __name__ == "__main__"`.
_SCENARIO_PATH = parse_scenario_arg(sys.argv)
SCENARIO = load_scenario(_SCENARIO_PATH)
CTX = setup_run(SCENARIO)

# fast-agent's fastagent.config.yaml expects the bearer token under the
# expected env-var name ("GITHUB_TOKEN" for github_skills, "HF_TOKEN"
# for hf_skills) — `Authorization: "Bearer ${VAR}"`. setup_run resolves
# the token; we only need to make it visible to fast-agent under the
# right name. Stdio servers (no auth) pass token_env_var=None.
if CTX["token_env_var"]:
    os.environ[CTX["token_env_var"]] = CTX["token"]

PROMPT = CTX["prompt"]


def _resolve_model_and_variant(scenario: dict) -> tuple[str | None, str | None]:
    """Pick the model id and variant label from env + scenario YAML.

    `FAST_AGENT_MODEL` is the ad-hoc override and always wins. Otherwise
    `models.fast-agent` is a map keyed by FAST_AGENT_VARIANT (default
    `anthropic`); a legacy scalar entry is treated as the only model.
    """
    override = os.environ.get("FAST_AGENT_MODEL")
    entry = scenario.get("models", {}).get("fast-agent")
    if override:
        return override, os.environ.get("FAST_AGENT_VARIANT")
    if isinstance(entry, dict):
        variant = os.environ.get("FAST_AGENT_VARIANT", "anthropic")
        if variant not in entry:
            available = ", ".join(sorted(entry)) or "(none)"
            sys.exit(
                f"scenario {scenario.get('id', _SCENARIO_PATH)!r} has no "
                f"fast-agent.{variant} entry (available: {available}) — "
                f"add one to the YAML or set FAST_AGENT_MODEL=<id>"
            )
        return entry[variant], variant
    return entry, None


MODEL, VARIANT = _resolve_model_and_variant(SCENARIO)
SERVER_ALIAS = CTX["server_alias"]

fast = FastAgent(f"skills-over-mcp scenario: {SCENARIO['id']}")


@contextmanager
def _run_workspace(scenario: dict):
    """Yield the cwd the agent should run under.

    For artifact-producing scenarios (those declaring `artifact_glob`)
    this is a *persistent* per-run dir under
    `experiments/.workspace/artifacts/<scenario_id>/<UTC-ts>/` — the
    model's file writes survive the run so the user can open them.

    For every other scenario it's a hermetic tempdir that gets wiped
    on exit, matching the existing behavior that keeps the harness
    dirs clean.
    """
    if scenario.get("artifact_glob"):
        ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = (
            _REPO_ROOT
            / "experiments"
            / ".workspace"
            / "artifacts"
            / scenario["id"]
            / ts
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        yield run_dir
    else:
        with tempfile.TemporaryDirectory(
            prefix="skills-e2e-fast-agent-",
            ignore_cleanup_errors=True,
        ) as tmp:
            yield Path(tmp)


def _locate_artifact(run_dir: Path, glob: str) -> Path | None:
    """Return the most-recently-modified file matching `glob` under `run_dir`.

    Single-artifact assumption: file-output scenarios prompt for one
    document. If the model wrote multiple (e.g. a stray template),
    pick the newest — that's the one it intended as the final.
    """
    matches = sorted(
        run_dir.glob(glob),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def _run_postprocess(
    cmd_template: list[str],
    artifact: Path,
    cwd: Path,
) -> tuple[str, str]:
    """Run the scenario's postprocess command. Returns (status, detail).

    `status` is one of: 'ok', 'failed', 'crashed'. `detail` is a short
    diagnostic suitable for the banner (exit code or exception type).
    Failures are not fatal — the raw artifact still grades; only the
    rendered output is missing.
    """
    cmd = [arg.format(artifact=str(artifact)) for arg in cmd_template]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except FileNotFoundError as exc:
        return "crashed", f"FileNotFoundError: {exc}"
    except subprocess.TimeoutExpired:
        return "crashed", "timeout after 60s"
    except Exception as exc:  # noqa: BLE001
        return "crashed", f"{type(exc).__name__}: {exc}"

    if proc.returncode == 0:
        return "ok", "exit=0"
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
    snippet = tail[0] if tail else ""
    return "failed", f"exit={proc.returncode}: {snippet}"[:140]


def _extract_tool_calls(agent) -> list[tuple[str, str, dict]]:
    """Walk message_history; return [(bare_name, raw_name, args), ...].

    fast-agent namespaces MCP tools as `<server>__<tool>`. The evaluator
    matches on the bare name; `raw_name` preserves the namespace so the
    server identifier survives in the recorded result.
    """
    runner = agent.runner
    calls: list[tuple[str, str, dict]] = []
    for msg in runner.message_history:
        if not msg.tool_calls:
            continue
        for req in msg.tool_calls.values():
            params = req.params
            raw = getattr(params, "name", None) or ""
            name = raw.split("__", 1)[1] if "__" in raw else raw
            args = dict(getattr(params, "arguments", None) or {})
            calls.append((name, raw, args))
    return calls


@fast.agent(
    name="runner",
    # No custom instruction — fall through to fast-agent's default so
    # the activation test sees only this CLI's native system prompt.
    model=MODEL,
    servers=[SERVER_ALIAS],
)
async def main() -> int:
    print(f"Scenario: {_SCENARIO_PATH}")
    print(f"Kind:    {CTX['kind']}")
    if CTX["kind"] == "pr-review":
        print(f"Target:  {CTX['repo']} PR #{CTX['pr_number']}")
    print(f"Server:  {SERVER_ALIAS}")
    print(f"Model:   {MODEL}")
    if VARIANT:
        print(f"Variant: {VARIANT}")
    print(f"Prompt:  {PROMPT}")
    print()

    response = None
    calls: list[tuple[str, dict]] = []
    error: str | None = None
    elapsed = 0.0
    run_dir: Path | None = None
    # fast-agent runs in-process, so its tools (write_text_file etc.)
    # resolve relative paths to *this* Python process's CWD. For most
    # scenarios this is a hermetic tempdir that gets wiped on exit; for
    # file-output scenarios (`artifact_glob` set) we use a persistent
    # per-run dir under `.workspace/artifacts/` so the model's writes
    # survive. fastagent.config.yaml is resolved at import time, before
    # this chdir, so config lookup is unaffected.
    prev_cwd = os.getcwd()
    with _run_workspace(SCENARIO) as workdir:
        run_dir = workdir
        os.chdir(workdir)
        try:
            async with fast.run() as agent:
                start = time.monotonic()
                try:
                    response = await agent.send(PROMPT)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    print(f"\n[fast-agent raised] {error}", file=sys.stderr)
                elapsed = time.monotonic() - start
                try:
                    calls = _extract_tool_calls(agent)
                except Exception as exc:
                    error = error or f"tool-call extraction failed: {exc}"
        finally:
            os.chdir(prev_cwd)

    final_text = response if isinstance(response, str) else str(response) if response else None

    # Artifact handling for file-output scenarios. Phrase-grep should
    # target the RAW output (model's exact bytes) since postprocess
    # mutates the placeholder away. Order: locate → copy raw aside →
    # run postprocess in place → grade against the raw copy.
    artifact_path: Path | None = None
    raw_artifact_path: Path | None = None
    postprocess_status: str | None = None
    if SCENARIO.get("artifact_glob") and run_dir is not None:
        artifact_path = _locate_artifact(run_dir, SCENARIO["artifact_glob"])
        if artifact_path is not None:
            raw_artifact_path = artifact_path.with_name(
                f"{artifact_path.stem}.raw{artifact_path.suffix}"
            )
            try:
                shutil.copy2(artifact_path, raw_artifact_path)
            except OSError as exc:
                print(f"[raw-copy failed] {exc}", file=sys.stderr)
                raw_artifact_path = None

            postprocess = SCENARIO.get("postprocess") or {}
            cmd_template = postprocess.get("cmd")
            if cmd_template:
                status, detail = _run_postprocess(
                    cmd_template, artifact_path, cwd=_BIRCH_DIR,
                )
                postprocess_status = detail
                print(f"[postprocess] {status}: {detail}", file=sys.stderr)
        else:
            print(
                f"[artifact] no file matched {SCENARIO['artifact_glob']!r} "
                f"under {run_dir}",
                file=sys.stderr,
            )

    report_and_save(
        client="fast-agent", scenario=SCENARIO, ctx=CTX, model=MODEL,
        calls=calls, final_text=final_text,
        elapsed_s=elapsed, error=error,
        artifact_path=str(artifact_path) if artifact_path else None,
        raw_artifact_path=str(raw_artifact_path) if raw_artifact_path else None,
        postprocess_status=postprocess_status,
    )
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
