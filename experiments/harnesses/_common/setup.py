"""Scenario setup + uniform report wrapper for client harnesses.

`setup_run` resolves everything a client harness needs to wire up its
subprocess (token, server config, prompt). `report_and_save` is the
banner + JSON write at the end. Behavior is dispatched structurally:

  - Token type is inferred from `mcp_server.alias` (github_* / hf_*),
    or skipped entirely for `transport: stdio`.
  - PR-style setup (resolve PR number, scaffold the branch, substitute
    {pr_number}/{repo} in the prompt) triggers when the scenario
    declares a `scaffolding_script`; everything else uses the prompt
    template verbatim.

Client harnesses still own the parts that differ per binary:
  - resolving / spawning the binary (codex / goose)
  - injecting MCP server config (CLI flags vs. temp config.yaml — the
    wire format varies)
  - parsing the binary's stream-json events into (calls, final_text)
"""

from __future__ import annotations

import os
import sys
from typing import Any

from _common.pr import find_review_url, resolve_pr_number
from _common.report import render_report, write_result_json
from _common.tokens import resolve_github_token, resolve_hf_token


def _resolve_auth(alias: str) -> tuple[str | None, str | None]:
    """Pick the bearer token + env-var name for an MCP server alias.

    The alias prefix encodes which backend the server talks to:
    `github_*` aliases get a GitHub PAT (e.g. `gh auth token`),
    `hf_*` aliases get `$HF_TOKEN`. Anything else exits with a clear
    error — add a branch here when introducing a new server family.
    """
    prefix = alias.split("_", 1)[0]
    if prefix == "github":
        return resolve_github_token(), "GITHUB_TOKEN"
    if prefix == "hf":
        return resolve_hf_token(), "HF_TOKEN"
    sys.exit(
        f"Cannot resolve auth for alias {alias!r}; expected a prefix of "
        f"'github_' or 'hf_'. Add a branch to _resolve_auth() if you're "
        f"wiring a new server family."
    )


def setup_run(scenario: dict) -> dict[str, Any]:
    """Resolve token, server config, prompt, and (when scaffolding) PR state.

    Returns a dict with:
      - token: resolved bearer token string, or None for stdio transport
        (used directly when the client materializes auth into a config
        file, e.g. goose)
      - token_env_var: "GITHUB_TOKEN" | "HF_TOKEN" — the env-var name
        the client should set in the child process when its config
        takes an env-var *name* rather than a literal token (e.g.
        codex's `bearer_token_env_var`). None for stdio servers
        that don't authenticate.
      - server_alias: name to register the MCP server under
      - server_endpoint: full URL (e.g. http://localhost:8082/mcp), or
        None for stdio servers whose spawn config lives in the client's
        own config file
      - prompt: final prompt text, PR-substituted when scaffolding,
        unchanged otherwise
      - repo, pr_number: set when scaffolding_script ran; None otherwise.
        `pr_number is not None` is the structural flag downstream code
        uses to print the PR target line and fetch a review URL.
    """
    server = scenario.get("mcp_server") or {}
    transport = server.get("transport", "http")
    alias = server.get("alias")
    if not alias:
        sys.exit("Scenario YAML must declare mcp_server.alias")
    if transport not in ("http", "stdio"):
        sys.exit(f"Unknown mcp_server.transport {transport!r}; expected 'http' or 'stdio'")

    needs_scaffolding = bool(scenario.get("scaffolding_script"))

    # Stdio servers have no URL and (currently) no authentication.
    # The client's own config supplies the spawn command/args.
    if transport == "stdio":
        if needs_scaffolding:
            sys.exit(
                "scaffolding_script is incompatible with stdio transport "
                "(scaffolding talks to GitHub over HTTP; stdio servers have "
                "no PR concept)."
            )
        return {
            "token": None, "token_env_var": None,
            "server_alias": alias, "server_endpoint": None,
            "repo": None, "pr_number": None,
            "prompt": scenario["prompt_template"].rstrip(),
        }

    endpoint = server.get("endpoint")
    if not endpoint:
        sys.exit("Scenario YAML must declare mcp_server.endpoint for http transport")

    token, token_env_var = _resolve_auth(alias)

    if needs_scaffolding:
        repo = os.environ.get("REPO", scenario["repo"])
        pr_number = resolve_pr_number(repo, scenario["head_branch"], scenario["scaffolding_script"])
        prompt = scenario["prompt_template"].format(pr_number=pr_number, repo=repo).rstrip()
        return {
            "token": token, "token_env_var": token_env_var,
            "server_alias": alias, "server_endpoint": endpoint,
            "repo": repo, "pr_number": pr_number, "prompt": prompt,
        }

    return {
        "token": token, "token_env_var": token_env_var,
        "server_alias": alias, "server_endpoint": endpoint,
        "repo": None, "pr_number": None,
        "prompt": scenario["prompt_template"].rstrip(),
    }


def report_and_save(
    *,
    client: str,
    scenario: dict,
    ctx: dict,
    model: str | None,
    calls: list[tuple[str, str, dict]],
    final_text: str | None,
    elapsed_s: float,
    timed_out: bool = False,
    error: str | None = None,
    artifact_path: str | None = None,
    raw_artifact_path: str | None = None,
    postprocess_status: str | None = None,
) -> None:
    """Render the banner and write the result JSON.

    Scenarios that scaffolded a PR (ctx['pr_number'] is set) fetch the
    review URL via `gh api` and print it after the banner; everything
    else omits the URL line and the JSON field entirely.

    File-output scenarios additionally pass `artifact_path` (the
    postprocessed file) and `raw_artifact_path` (the preserved
    pre-postprocess copy); both show up in the banner and JSON record.
    """
    common_json = dict(
        client=client, scenario_id=scenario["id"], model=model,
        tool_calls=calls,
        elapsed_ms=int(elapsed_s * 1000),
        error=error, final_text=final_text,
        artifact_path=artifact_path,
        raw_artifact_path=raw_artifact_path,
        postprocess_status=postprocess_status,
    )
    if ctx.get("pr_number") is not None:
        review_url = find_review_url(ctx["repo"], ctx["pr_number"])
        render_report(
            calls=calls, review_url=review_url,
            elapsed_s=elapsed_s, timed_out=timed_out, final_text=final_text,
            artifact_path=artifact_path, raw_artifact_path=raw_artifact_path,
            postprocess_status=postprocess_status,
        )
        write_result_json(**common_json, review_url=review_url)
    else:
        render_report(
            calls=calls,
            elapsed_s=elapsed_s, timed_out=timed_out, final_text=final_text,
            artifact_path=artifact_path, raw_artifact_path=raw_artifact_path,
            postprocess_status=postprocess_status,
        )
        write_result_json(**common_json)
