"""Generic scenario runner for goose.

Drives `goose run --output-format stream-json` and parses its JSONL
StreamEvent stream. Server endpoint, alias, and the auth token come
from the scenario YAML via `setup_run`.

SECURITY -- do not point at untrusted repos / endpoints (see
fast-agent/agent.py).

Pre-reqs:
- `goose` from the fork branch: `cargo install --git
  https://github.com/olaservo/goose.git --branch mcp-skills-sep
  --no-default-features --features rustls-tls --locked goose-cli`.
  Or set GOOSE_BIN=/abs/path/goose[.exe].
- Provider API key for the chosen variant (ANTHROPIC_API_KEY,
  OPENAI_API_KEY, GEMINI_API_KEY, or OPENROUTER_API_KEY). Source
  `$AGENT_SKILLS_ENV_FILE` once per shell.
- Token for the scenario's server: GITHUB_TOKEN for github_* aliases,
  HF_TOKEN for hf_* aliases.
- The MCP server the scenario points at, running on its declared port.

Model selection: scenario YAML's `models.goose` is a dict keyed by
variant (`anthropic` | `openai` | `google` | `openrouter`); pick one
via GOOSE_VARIANT (default `anthropic`). GOOSE_MODEL is the ad-hoc
override that wins over both -- pair with GOOSE_PROVIDER when the
model belongs to a non-default provider.

Usage:
    cd experiments/harnesses/goose
    set -a && . "$AGENT_SKILLS_ENV_FILE" && set +a
    # Default Anthropic variant:
    GITHUB_TOKEN=$(gh auth token) \\
        uv run agent.py ../../scenarios/pr-review.yaml
    # Google variant:
    GITHUB_TOKEN=$(gh auth token) GOOSE_VARIANT=google \\
        uv run agent.py ../../scenarios/pr-review.yaml
    # Ad-hoc model override:
    GITHUB_TOKEN=$(gh auth token) GOOSE_PROVIDER=openai GOOSE_MODEL=gpt-5-mini \\
        uv run agent.py ../../scenarios/pr-review.yaml
"""

# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0", "psutil>=5.9"]
# ///

from __future__ import annotations

import json
import os
import shutil
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


# 600s accommodates sonnet working through 6+ inline PR comments; at
# 240s it often gets killed mid-commenting on dense reviews. Override
# per run with GOOSE_TIMEOUT_S=<seconds>.
_DEFAULT_TIMEOUT_S = 600
_DEFAULT_PROVIDER = "anthropic"

# Variant name -> goose `--provider` value. Mirrors fast-agent's variant
# names so the cross-client matrix uses the same vocabulary; goose's
# provider IDs happen to coincide with the variant labels we use today.
_VARIANT_TO_PROVIDER = {
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google",
    "openrouter": "openrouter",
}


def _resolve_model_provider_variant(
    scenario: dict,
) -> tuple[str | None, str, str | None]:
    """Pick model, provider, and variant label from env + scenario YAML.

    GOOSE_MODEL (or legacy GOOSE_E2E_MODEL) is the ad-hoc override and
    always wins; pair with GOOSE_PROVIDER for non-default providers.
    Otherwise `models.goose` is a dict keyed by GOOSE_VARIANT (default
    `anthropic`); the provider is derived from the variant via
    `_VARIANT_TO_PROVIDER` unless GOOSE_PROVIDER overrides. A legacy
    scalar entry (single model id) is treated as the only model.
    """
    override = os.environ.get("GOOSE_MODEL") or os.environ.get("GOOSE_E2E_MODEL")
    entry = scenario.get("models", {}).get("goose")
    if override:
        provider = os.environ.get("GOOSE_PROVIDER") or _DEFAULT_PROVIDER
        return override, provider, os.environ.get("GOOSE_VARIANT")
    if isinstance(entry, dict):
        variant = os.environ.get("GOOSE_VARIANT", "anthropic")
        if variant not in entry:
            available = ", ".join(sorted(entry)) or "(none)"
            sys.exit(
                f"scenario {scenario.get('id', '?')!r} has no goose.{variant} "
                f"entry (available: {available}) -- add one to the YAML or "
                f"set GOOSE_MODEL=<id>"
            )
        provider = (
            os.environ.get("GOOSE_PROVIDER")
            or _VARIANT_TO_PROVIDER.get(variant, _DEFAULT_PROVIDER)
        )
        return entry[variant], provider, variant
    provider = os.environ.get("GOOSE_PROVIDER") or _DEFAULT_PROVIDER
    return entry, provider, None


def _resolve_goose_command() -> list[str]:
    explicit = os.environ.get("GOOSE_BIN")
    if explicit:
        path = Path(explicit)
        if not path.exists():
            sys.exit(f"GOOSE_BIN points at a path that does not exist: {path}")
        resolved = str(path)
    else:
        resolved = shutil.which("goose")
        if resolved is None:
            sys.exit(
                "`goose` not found on PATH and GOOSE_BIN not set. See the "
                "module docstring for the fork install command."
            )
    if os.name == "nt" and resolved.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", resolved]
    return [resolved]


def _write_goose_config(
    goose_path_root: Path, *, alias: str, endpoint: str, token: str,
) -> None:
    """Write a config.yaml with the MCP extension pre-registered.

    `--with-streamable-http-extension` doesn't accept headers, so the
    Bearer auth has to go in a config file. GOOSE_PATH_ROOT redirects
    goose's config dirs to a hermetic temp.
    """
    config_dir = goose_path_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "extensions": {
            alias: {
                "type": "streamable_http",
                "name": alias,
                "description": f"MCP server registered for skills-over-mcp scenario ({alias})",
                "uri": endpoint,
                "headers": {"Authorization": f"Bearer {token}"},
                "timeout": 60,
                "enabled": True,
            },
        },
    }
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
    )


def _extract_tool_calls(events: list[dict], *, alias: str) -> tuple[list[tuple[str, str, dict]], str | None]:
    """Walk goose's JSONL stream.

    Schema: {"type":"message","message":{"role":"assistant","content":[
        {"type":"text","text":"..."},
        {"type":"toolRequest","toolCall":{"status":"success",
            "value":{"name":"X","arguments":{...}}}},
    ]}}

    Goose prefixes MCP tools with `<server>__`; strip so the evaluator
    matches bare names. Built-ins (read_mcp_resource, load_skill) have
    no prefix. `raw_name` preserves the unstripped form so the server
    identifier survives in the recorded result.
    """
    calls: list[tuple[str, str, dict]] = []
    final_text: str | None = None
    prefix = f"{alias}__"
    for event in events:
        if event.get("type") != "message":
            continue
        msg = event.get("message") or {}
        role = msg.get("role")
        for item in (msg.get("content") or []):
            it_type = item.get("type")
            if it_type == "toolRequest":
                tc = item.get("toolCall") or {}
                if tc.get("status") != "success":
                    continue
                value = tc.get("value") or {}
                raw_name = value.get("name") or ""
                name = raw_name.removeprefix(prefix)
                args = value.get("arguments") or {}
                if not isinstance(args, dict):
                    args = {}
                calls.append((name, raw_name, args))
            elif it_type == "text" and role == "assistant":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    final_text = text
    return calls, final_text


def _run_goose(cmd: list[str], env: dict[str, str], timeout_s: float, cwd: str | None = None):
    """Stream JSONL from goose stdout, echoing to stderr. Returns
    (events, exit_code, timed_out).
    """
    events: list[dict] = []
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
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                print(f"[non-JSON goose stdout] {line}", file=sys.stderr)
                continue
            events.append(event)
            etype = event.get("type", "?")
            if etype == "message":
                msg = event.get("message") or {}
                for item in (msg.get("content") or []):
                    it_type = item.get("type")
                    if it_type == "toolRequest":
                        tc = item.get("toolCall") or {}
                        value = tc.get("value") or {}
                        print(f"  >> {value.get('name')}  status={tc.get('status')}", file=sys.stderr)
                    elif it_type == "text" and msg.get("role") == "assistant":
                        preview = (item.get("text") or "")[:120]
                        if preview.strip():
                            print(f"  >> agent: {preview}...", file=sys.stderr)
            elif etype == "error":
                print(f"  !! error: {event.get('error')}", file=sys.stderr)
    finally:
        timer.cancel()
        proc.wait()
    stderr_tail = (proc.stderr.read() if proc.stderr else "") or ""
    if stderr_tail.strip():
        print("--- goose stderr ---", file=sys.stderr)
        print(stderr_tail, file=sys.stderr)
    if timed_out["fired"]:
        print(f"\n!! TIMED OUT after {timeout_s:.0f}s", file=sys.stderr)
    return events, proc.returncode, timed_out["fired"]


def main() -> int:
    goose_prefix = _resolve_goose_command()
    scenario_path = parse_scenario_arg(sys.argv)
    scenario = load_scenario(scenario_path)
    ctx = setup_run(scenario)

    model, provider, variant = _resolve_model_provider_variant(scenario)
    if not model:
        sys.exit(
            "No goose model. Scenario YAML should carry `models.goose` as a "
            "dict keyed by variant (anthropic|openai|google|openrouter), or "
            "as a single id. Override with GOOSE_MODEL=<id>."
        )
    prompt = ctx["prompt"]
    alias = ctx["server_alias"]

    print(f"Scenario: {scenario_path}")
    if ctx["pr_number"] is not None:
        print(f"Target:  {ctx['repo']} PR #{ctx['pr_number']}")
    variant_suffix = f" (variant={variant})" if variant else ""
    print(f"Provider/Model:  {provider} / {model}{variant_suffix}")
    print(f"Server:  {alias} -> {ctx['server_endpoint']}")
    print(f"Prompt:  {prompt}")
    print()

    timeout_s = float(os.environ.get("GOOSE_TIMEOUT_S") or _DEFAULT_TIMEOUT_S)
    error: str | None = None
    events: list[dict] = []
    rc = -1
    timed_out = False
    elapsed = 0.0

    with tempfile.TemporaryDirectory(prefix="skills-e2e-goose-", ignore_cleanup_errors=True) as tmp:
        goose_path_root = Path(tmp)
        _write_goose_config(
            goose_path_root, alias=alias, endpoint=ctx["server_endpoint"], token=ctx["token"],
        )
        env = {
            **os.environ,
            ctx["token_env_var"]: ctx["token"],
            "GOOSE_PATH_ROOT": str(goose_path_root),
            "GOOSE_DISABLE_KEYRING": "1",
        }
        # Goose's google provider reads GOOGLE_API_KEY; the shared
        # $AGENT_SKILLS_ENV_FILE only declares GEMINI_API_KEY (the name
        # fast-agent's google provider expects). Bridge so a single .env
        # works across both clients.
        if "GOOGLE_API_KEY" not in env and env.get("GEMINI_API_KEY"):
            env["GOOGLE_API_KEY"] = env["GEMINI_API_KEY"]
        cmd = [
            *goose_prefix, "run",
            "--text", prompt,
            "--output-format", "stream-json",
            "--no-session",
            "--provider", provider,
            "--model", model,
            "-q",
        ]
        start = time.monotonic()
        try:
            # Hermetic CWD: any `write` / shell-curl-output lands in
            # goose_path_root (already used for goose's config dir) and
            # is discarded when the harness exits.
            events, rc, timed_out = _run_goose(cmd, env, timeout_s, cwd=str(goose_path_root))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"\n[goose subprocess failed] {error}", file=sys.stderr)
        elapsed = time.monotonic() - start

    if timed_out:
        error = error or f"timeout after {timeout_s:.0f}s"
    elif rc != 0 and not error:
        print(f"\n[goose run exited non-zero: {rc}]", file=sys.stderr)
        error = f"goose exit code {rc}"

    calls, final_text = _extract_tool_calls(events, alias=alias)
    report_and_save(
        client="goose", scenario=scenario, ctx=ctx, model=model,
        calls=calls, final_text=final_text,
        elapsed_s=elapsed, timed_out=timed_out, error=error,
    )
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
