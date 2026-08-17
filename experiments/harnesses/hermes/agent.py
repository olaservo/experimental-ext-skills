"""Generic scenario runner for hermes (NousResearch/hermes-agent).

Drives `hermes chat -q "<prompt>"` non-interactively and recovers the
tool-call sequence from hermes's SQLite session store. Server endpoint,
alias, and the auth token come from the scenario YAML via `setup_run`.

Why a session-DB read instead of stdout parsing: hermes has no
`--output-format json` stream. In quiet mode (`-Q`) stdout is just the
final assistant response; the full message history (including
OpenAI-format `tool_calls`) is persisted to `$HERMES_HOME/state.db`
(table `messages`, `tool_calls` column = JSON string). We run with a
hermetic `HERMES_HOME` tempdir, so that DB holds exactly this run's one
session and we read it back after the process exits.

SECURITY -- do not point at untrusted repos / endpoints (see
fast-agent/agent.py).

Pre-reqs:
- `hermes` from the fork branch on PATH (or set HERMES_BIN=/abs/path):
  install per the hermes-agent repo (`./setup-hermes.sh`, or
  `uv pip install -e ".[all]"` from a clone of
  `olaservo/hermes-agent @ feature/add-skill-over-mcp-support`).
  An upstream hermes WITHOUT the skills-over-mcp branch will run but
  never materialize MCP skills (no `read_skill` in the call list) --
  same failure signature as the codex PATH-shadowing trap.
- Provider API key for the chosen variant (ANTHROPIC_API_KEY for the
  default). Source `$AGENT_SKILLS_ENV_FILE` once per shell.
- Token for the scenario's server: GITHUB_TOKEN for github_* aliases,
  HF_TOKEN for hf_* aliases.
- The MCP server the scenario points at, running on its declared port.

Model selection: scenario YAML's `models.hermes` is a dict keyed by
variant (`anthropic` for now); pick one via HERMES_VARIANT (default
`anthropic`). HERMES_MODEL is the ad-hoc override that wins over both.
Hermes takes a combined `provider/model` slug on `-m`
(e.g. `anthropic/claude-sonnet-4-6`), so the YAML value IS the full slug
and the provider auto-resolves from credentials -- no separate provider
flag.

Usage:
    cd experiments/harnesses/hermes
    set -a && . "$AGENT_SKILLS_ENV_FILE" && set +a
    # Default Anthropic variant:
    GITHUB_TOKEN=$(gh auth token) \\
        uv run agent.py ../../scenarios/pr-review.yaml
    # Ad-hoc model override:
    GITHUB_TOKEN=$(gh auth token) HERMES_MODEL=openrouter/deepseek/deepseek-v4-pro \\
        uv run agent.py ../../scenarios/pr-review.yaml
    # HF scenario (HF_TOKEN comes from $AGENT_SKILLS_ENV_FILE):
    uv run agent.py ../../scenarios/transformers-js-demo.yaml
"""

# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0", "psutil>=5.9"]
# ///

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import psutil
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _common import (  # noqa: E402
    load_scenario,
    parse_scenario_arg,
    report_and_save,
    setup_run,
)


# 600s matches goose -- accommodates a model working through 6+ inline PR
# comments; shorter timeouts get killed mid-commenting. Override per run
# with HERMES_TIMEOUT_S=<seconds>.
_DEFAULT_TIMEOUT_S = 600

# Session source tag: keeps this run's session out of the user's normal
# session lists. Moot under a hermetic HERMES_HOME (the DB is fresh
# anyway), but harmless and self-documenting.
_SESSION_SOURCE = "skills-e2e"

# hermes is itself a Python app launched via its own venv's `hermes.exe`
# (the interpreter path is baked into the console script). When THIS
# harness runs under `uv run agent.py`, uv injects its managed Python via
# these vars; inheriting them makes hermes.exe load its venv's editable
# `.pth` under the wrong interpreter and crash in site.py before main().
# Strip them so hermes resolves its own interpreter cleanly.
_INTERPRETER_ENV_VARS = (
    "VIRTUAL_ENV",
    "PYTHONHOME",
    "PYTHONPATH",
    "PYTHONEXECUTABLE",
    "PYTHONSTARTUP",
    "PYTHONSAFEPATH",
    "__PYVENV_LAUNCHER__",
)


def _child_env(hermes_home: Path) -> dict[str, str]:
    """os.environ minus interpreter/venv/uv vars, plus a hermetic HERMES_HOME."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in _INTERPRETER_ENV_VARS and not k.startswith("UV_")
    }
    env["HERMES_HOME"] = str(hermes_home)
    return env


def _resolve_model_variant(scenario: dict) -> tuple[str | None, str | None]:
    """Pick the `provider/model` slug + variant label from env + YAML.

    HERMES_MODEL (or legacy HERMES_E2E_MODEL) is the ad-hoc override and
    always wins. Otherwise `models.hermes` is a dict keyed by
    HERMES_VARIANT (default `anthropic`); a legacy scalar entry (single
    slug) is treated as the only model. Unlike goose, hermes encodes the
    provider in the slug, so there's no separate provider to resolve.
    """
    override = os.environ.get("HERMES_MODEL") or os.environ.get("HERMES_E2E_MODEL")
    entry = scenario.get("models", {}).get("hermes")
    if override:
        return override, os.environ.get("HERMES_VARIANT")
    if isinstance(entry, dict):
        variant = os.environ.get("HERMES_VARIANT", "anthropic")
        if variant not in entry:
            available = ", ".join(sorted(entry)) or "(none)"
            sys.exit(
                f"scenario {scenario.get('id', '?')!r} has no hermes.{variant} "
                f"entry (available: {available}) -- add one to the YAML or "
                f"set HERMES_MODEL=<provider/model>"
            )
        return entry[variant], variant
    return entry, None


def _resolve_hermes_command() -> list[str]:
    explicit = os.environ.get("HERMES_BIN")
    if explicit:
        path = Path(explicit)
        if not path.exists():
            sys.exit(f"HERMES_BIN points at a path that does not exist: {path}")
        resolved = str(path)
    else:
        resolved = shutil.which("hermes")
        if resolved is None:
            sys.exit(
                "`hermes` not found on PATH and HERMES_BIN not set. Install the "
                "fork branch (see the module docstring) or set HERMES_BIN."
            )
    if os.name == "nt" and resolved.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", resolved]
    return [resolved]


def _write_hermes_config(
    hermes_home: Path, *, model: str, alias: str, endpoint: str, token: str | None,
) -> None:
    """Write a config.yaml that pins the model, registers the MCP server
    with bearer auth, and turns the skills-over-MCP extension on.

    The config lives under a hermetic HERMES_HOME tempdir so it never
    touches the user's real ~/.hermes/. Auth goes inline as a literal
    Bearer header (hermes also supports `${ENV}` interpolation in headers,
    but a literal token is self-contained -- same approach goose takes).
    `mcp.skills_extension: experimental` is the feature gate
    (`tools/mcp_skills.py::skills_extension_enabled`); default is off.
    """
    server: dict = {"url": endpoint, "enabled": True}
    if token:
        server["headers"] = {"Authorization": f"Bearer {token}"}
    config = {
        "model": {"default": model, "provider": "auto"},
        "mcp": {"skills_extension": "experimental"},
        "mcp_servers": {alias: server},
    }
    (hermes_home / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )


def _extract_tool_calls(
    state_db: Path, *, alias: str,
) -> tuple[list[tuple[str, str, dict]], str | None]:
    """Read tool calls + final text from hermes's SQLite session store.

    Schema (website/docs/developer-guide/session-storage.md):
        messages(id, session_id, role, content, tool_call_id,
                 tool_calls TEXT, tool_name, timestamp REAL, ...)
    `tool_calls` is a JSON string -- a list of OpenAI tool-call objects
    `{"function": {"name": ..., "arguments": "<json string>"}}`.

    Hermes namespaces MCP tools as `mcp_<server>_<tool>` (single
    underscores, observed against github_skills); we strip the prefix
    into `name` so it matches the bare names goose/codex/fast-agent
    record, and keep the unstripped form in `raw_name` so the server
    identifier survives. Double-underscore variants are handled too in
    case the convention shifts.
    """
    calls: list[tuple[str, str, dict]] = []
    final_text: str | None = None
    if not state_db.exists():
        print(f"!! no session DB at {state_db} -- did the run persist?", file=sys.stderr)
        return calls, final_text

    con = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT role, content, tool_calls FROM messages ORDER BY id"
        ).fetchall()
    finally:
        con.close()

    # Longest match first so the bare tool name lands in `name`.
    prefixes = (f"mcp__{alias}__", f"mcp_{alias}_", f"{alias}__", f"{alias}_")
    for role, content, tc_json in rows:
        if role != "assistant":
            continue
        if isinstance(content, str) and content.strip():
            final_text = content
        if not tc_json:
            continue
        try:
            tool_calls = json.loads(tc_json)
        except (json.JSONDecodeError, TypeError):
            continue
        for tc in tool_calls or []:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function") or {}
            raw_name = fn.get("name") or tc.get("name") or ""
            name = raw_name
            for p in prefixes:
                if name.startswith(p):
                    name = name[len(p):]
                    break
            raw_args = fn.get("arguments", tc.get("arguments"))
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args)
                except (json.JSONDecodeError, ValueError):
                    args = {"_raw": raw_args}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}
            if not isinstance(args, dict):
                args = {"_value": args}
            calls.append((name, raw_name, args))
    return calls, final_text


def _run_hermes(cmd: list[str], env: dict[str, str], timeout_s: float, cwd: str):
    """Run hermes, echoing stdout to stderr. Returns (rc, timed_out).

    Tool calls are NOT parsed from stdout (we read them from state.db
    afterward); we just stream output so the log shows progress and the
    final response.
    """
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    assert proc.stdout is not None
    timed_out = {"fired": False}

    def _kill_on_timeout() -> None:
        # Process-tree kill: Windows TerminateProcess leaves children
        # holding the stdout pipe open, so the reader never sees EOF.
        timed_out["fired"] = True
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
        except psutil.NoSuchProcess:
            pass
        except Exception as exc:
            print(f"!! kill_on_timeout failed: {exc}", file=sys.stderr)

    timer = threading.Timer(timeout_s, _kill_on_timeout)
    timer.start()
    try:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if line.strip():
                print(f"  >> {line}", file=sys.stderr)
    finally:
        timer.cancel()
        proc.wait()
    stderr_tail = (proc.stderr.read() if proc.stderr else "") or ""
    if stderr_tail.strip():
        print("--- hermes stderr ---", file=sys.stderr)
        print(stderr_tail, file=sys.stderr)
    if timed_out["fired"]:
        print(f"\n!! TIMED OUT after {timeout_s:.0f}s", file=sys.stderr)
    return proc.returncode, timed_out["fired"]


def main() -> int:
    hermes_prefix = _resolve_hermes_command()
    scenario_path = parse_scenario_arg(sys.argv)
    scenario = load_scenario(scenario_path)
    ctx = setup_run(scenario)

    model, variant = _resolve_model_variant(scenario)
    if not model:
        sys.exit(
            "No hermes model. Scenario YAML should carry `models.hermes` as a "
            "dict keyed by variant (anthropic), or as a single provider/model "
            "slug. Override with HERMES_MODEL=<provider/model>."
        )
    prompt = ctx["prompt"]
    alias = ctx["server_alias"]

    if ctx["server_endpoint"] is None:
        sys.exit(
            "hermes harness currently supports HTTP MCP servers only; this "
            "scenario uses stdio transport (no endpoint). Skipping."
        )

    print(f"Scenario: {scenario_path}")
    if ctx["pr_number"] is not None:
        print(f"Target:  {ctx['repo']} PR #{ctx['pr_number']}")
    variant_suffix = f" (variant={variant})" if variant else ""
    print(f"Model:   {model}{variant_suffix}")
    print(f"Server:  {alias} -> {ctx['server_endpoint']}")
    print(f"Prompt:  {prompt}")
    print()

    timeout_s = float(os.environ.get("HERMES_TIMEOUT_S") or _DEFAULT_TIMEOUT_S)
    error: str | None = None
    rc = -1
    timed_out = False
    elapsed = 0.0
    calls: list[tuple[str, str, dict]] = []
    final_text: str | None = None

    with tempfile.TemporaryDirectory(prefix="skills-e2e-hermes-", ignore_cleanup_errors=True) as tmp:
        hermes_home = Path(tmp)
        _write_hermes_config(
            hermes_home, model=model, alias=alias,
            endpoint=ctx["server_endpoint"], token=ctx["token"],
        )
        env = _child_env(hermes_home)
        if ctx["token_env_var"] and ctx["token"]:
            env[ctx["token_env_var"]] = ctx["token"]
        cmd = [
            *hermes_prefix, "chat",
            "-q", prompt,
            "-m", model,
            "-Q",                 # quiet: programmatic output only
            "--yolo",             # bypass dangerous-command approval prompts
            "--accept-hooks",     # auto-approve config hooks (no TTY)
            "--ignore-rules",     # skip AGENTS.md/SOUL.md/memory injection
            "--source", _SESSION_SOURCE,
        ]
        start = time.monotonic()
        try:
            # Hermetic CWD: any file the agent writes lands in the
            # throwaway HERMES_HOME and is discarded on exit.
            rc, timed_out = _run_hermes(cmd, env, timeout_s, cwd=str(hermes_home))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"\n[hermes subprocess failed] {error}", file=sys.stderr)
        elapsed = time.monotonic() - start

        # Read the session record while HERMES_HOME still exists.
        calls, final_text = _extract_tool_calls(hermes_home / "state.db", alias=alias)

    if timed_out:
        error = error or f"timeout after {timeout_s:.0f}s"
    elif rc != 0 and not error:
        print(f"\n[hermes run exited non-zero: {rc}]", file=sys.stderr)
        error = f"hermes exit code {rc}"

    report_and_save(
        client="hermes", scenario=scenario, ctx=ctx, model=model,
        calls=calls, final_text=final_text,
        elapsed_s=elapsed, timed_out=timed_out, error=error,
    )
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
