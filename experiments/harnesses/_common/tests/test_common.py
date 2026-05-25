"""Regression tests for the shared harness plumbing.

After dropping per-kind grading, the harness's only evaluation step is
recording the MCP tool calls. The interesting surface to cover is:

  - token parsing (skill_name_from_arg, matches_expected_skill_uri) —
    still used by tooling that wants to compare URIs even though the
    runtime no longer asserts on them
  - scenario YAML loading + kind-aware validation
  - setup_run (token resolution, server config, prompt substitution)
  - render_report + write_result_json shape (the call log is the result)

Run from harnesses/:
    uv run --with pyyaml --with pytest python -m pytest _common/tests/
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest
import yaml

_HARNESSES_DIR = Path(__file__).resolve().parents[2]
if str(_HARNESSES_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESSES_DIR))

from _common import (  # noqa: E402
    evaluate, load_scenario, render_report, write_result_json,
)
from _common.setup import setup_run  # noqa: E402
from _common.tokens import (  # noqa: E402
    matches_expected_skill_uri,
    skill_name_from_arg,
)


SKILL_URI = "skill://pull-requests/SKILL.md"
HF_SKILL_URI = "skill://huggingface-llm-trainer/SKILL.md"


# Tool-call shape is (name, raw_name, args) — see _common/report.py.
def _t(name: str, args: dict, raw_name: str | None = None) -> tuple[str, str, dict]:
    return (name, raw_name if raw_name is not None else name, args)


# ---------------------------------------------------------------------- skill_name_from_arg

@pytest.mark.parametrize(
    "val,expected",
    [
        # legacy un-namespaced URIs (still in use on hf-mcp-server)
        ("skill://pull-requests/SKILL.md", "pull-requests"),
        ("skill://huggingface-llm-trainer/SKILL.md", "huggingface-llm-trainer"),
        ("skill://huggingface-llm-trainer/references/training_methods.md",
         "huggingface-llm-trainer"),
        # namespaced URIs (github-mcp-server advertises `skill://github/<name>/...`)
        ("skill://github/pull-requests/SKILL.md", "pull-requests"),
        ("skill://github/create-pr/SKILL.md", "create-pr"),
        ("skill://github/pull-requests/references/X.md", "pull-requests"),
        ("skill://github/foo/scripts/sub/file.py", "foo"),
        # non-URI forms (goose's load_skill name argument)
        ("pull-requests", "pull-requests"),
        ("pull-requests/scripts/train.py", "pull-requests"),
        ("github_skills__pull-requests", "pull-requests"),
    ],
)
def test_skill_name_from_arg(val: str, expected: str):
    assert skill_name_from_arg(val) == expected


@pytest.mark.parametrize(
    "target,expected_uri,ok",
    [
        # URI-form target: byte-for-byte equality required.
        ("skill://github/pull-requests/SKILL.md",
         "skill://github/pull-requests/SKILL.md", True),
        # Namespace divergence MUST fail under URI-strict matching even
        # though both sides parse to the same skill name.
        ("skill://github/pull-requests/SKILL.md",
         "skill://pull-requests/SKILL.md", False),
        ("skill://pull-requests/SKILL.md",
         "skill://github/pull-requests/SKILL.md", False),
        # Bare-name target: falls back to parsed-name comparison.
        ("pull-requests", "skill://github/pull-requests/SKILL.md", True),
        ("pull-requests", "skill://pull-requests/SKILL.md", True),
        # goose's <server>__<name> disambiguation form.
        ("github_skills__pull-requests",
         "skill://github/pull-requests/SKILL.md", True),
        # Wrong skill name in bare-name form.
        ("other-skill", "skill://github/pull-requests/SKILL.md", False),
    ],
)
def test_matches_expected_skill_uri(target: str, expected_uri: str, ok: bool):
    assert matches_expected_skill_uri(target, expected_uri) is ok


# ---------------------------------------------------------------------- evaluate

def test_evaluate_returns_tool_calls_unchanged():
    calls = [
        _t("read_mcp_resource", {"uri": SKILL_URI}),
        _t("hf_jobs", {"operation": "uv", "args": {"script": "..."}}),
    ]
    result = evaluate(calls)
    assert result == {"tool_calls": calls}


def test_evaluate_accepts_empty_calls():
    assert evaluate([]) == {"tool_calls": []}


# ---------------------------------------------------------------------- scenario

def _write_yaml(path: Path, **fields) -> None:
    path.write_text(yaml.safe_dump(fields, sort_keys=False), encoding="utf-8")


def test_load_scenario_pr_review_happy_path(tmp_path: Path):
    path = tmp_path / "s.yaml"
    _write_yaml(
        path,
        id="test", kind="pr-review", repo="a/b", head_branch="main", scaffolding_script="s.sh",
        prompt_template="PR #{pr_number} on {repo}",
    )
    s = load_scenario(path)
    assert s["id"] == "test"
    assert s["kind"] == "pr-review"
    assert s["prompt_template"].format(pr_number=7, repo="a/b") == "PR #7 on a/b"


def test_load_scenario_plan_does_not_require_pr_fields(tmp_path: Path):
    path = tmp_path / "s.yaml"
    _write_yaml(
        path,
        id="plan-test", kind="plan",
        prompt_template="just a plan",
    )
    s = load_scenario(path)
    assert s["kind"] == "plan"


def test_load_scenario_missing_kind_exits(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    _write_yaml(path, id="x", repo="a/b", head_branch="main", scaffolding_script="s.sh",
                prompt_template="...")
    with pytest.raises(SystemExit) as ei:
        load_scenario(path)
    assert "kind" in str(ei.value)


def test_load_scenario_unknown_kind_exits(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    _write_yaml(path, id="x", kind="bogus", prompt_template="...")
    with pytest.raises(SystemExit) as ei:
        load_scenario(path)
    assert "unknown kind" in str(ei.value)


def test_load_scenario_pr_missing_repo_exits(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    _write_yaml(path, id="x", kind="pr-review", prompt_template="...")
    with pytest.raises(SystemExit) as ei:
        load_scenario(path)
    assert "missing fields" in str(ei.value)


# ---------------------------------------------------------------------- report

def test_write_result_json_pr_shape(tmp_path: Path):
    calls = [
        _t("read_mcp_resource", {"uri": SKILL_URI}),
        _t("pull_request_review_write", {"method": "create", "pullNumber": 7}),
        _t("add_comment_to_pending_review",
           {"line": 10, "body": "secret_body_should_be_preserved_in_json"}),
        _t("pull_request_review_write", {"method": "submit_pending", "event": "APPROVE"}),
    ]
    path = write_result_json(
        client="codex", scenario_id="pr-review", model="gpt-5.1-codex",
        tool_calls=calls,
        review_url="https://example.com/r/1", elapsed_ms=12345,
        results_dir=tmp_path,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["client"] == "codex"
    assert payload["scenario_id"] == "pr-review"
    # No criteria / overall keys post-simplification.
    assert "criteria" not in payload
    assert "overall" not in payload
    # Filename convention: <ISO-UTC>-<scenario>-<client>-<model>.json
    assert path.name.endswith("-pr-review-codex-gpt-5.1-codex.json")
    # Body preserved in JSON (only stripped from stdout preview).
    assert payload["tool_calls"][2]["args"]["body"].startswith("secret_body")
    assert payload["review_url"] == "https://example.com/r/1"


def test_write_result_json_plan_shape(tmp_path: Path):
    calls = [_t("read_mcp_resource", {"uri": HF_SKILL_URI})]
    path = write_result_json(
        client="codex", scenario_id="hf-jobs-plan", model="gpt-5.1-codex",
        tool_calls=calls, elapsed_ms=4200,
        final_text="Job submitted!",
        results_dir=tmp_path,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "criteria" not in payload
    assert "overall" not in payload
    assert payload["final_text"] == "Job submitted!"
    # No review_url for plan scenarios.
    assert "review_url" not in payload


def test_write_result_json_crash_path_records_error(tmp_path: Path):
    path = write_result_json(
        client="goose", scenario_id="pr-review", model="claude-haiku-4-5-20251001",
        tool_calls=[], review_url=None, elapsed_ms=50,
        error="connection refused", results_dir=tmp_path,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["tool_calls"] == []
    assert payload["error"] == "connection refused"


def test_render_report_emits_pr_banner_with_review_url():
    calls = [
        _t("read_mcp_resource", {"uri": SKILL_URI}),
        _t("pull_request_review_write", {"method": "create", "pullNumber": 7}),
        _t("add_comment_to_pending_review",
           {"line": 10, "body": "secret_body_should_not_appear_in_stdout"}),
        _t("pull_request_review_write", {"method": "submit_pending", "event": "COMMENT"}),
    ]
    buf = io.StringIO()
    render_report(calls=calls, review_url="https://example.com/r/1", elapsed_s=1.5, out=buf)
    text = buf.getvalue()
    assert "Ordered tool calls:" in text
    assert "Review URL: https://example.com/r/1" in text
    assert "Wall-clock:" in text
    # `body` arg is stripped from stdout preview (privacy / log size).
    assert "secret_body" not in text
    # No criteria block anymore.
    assert "PASS" not in text
    assert "FAIL" not in text


def test_render_report_plan_omits_review_url():
    calls = [_t("read_mcp_resource", {"uri": HF_SKILL_URI})]
    buf = io.StringIO()
    render_report(calls=calls, elapsed_s=2.0, out=buf)
    text = buf.getvalue()
    assert "Ordered tool calls:" in text
    assert "Wall-clock:" in text
    # Plan scenarios omit the Review URL line entirely.
    assert "Review URL:" not in text


def test_render_report_empty_calls():
    buf = io.StringIO()
    render_report(calls=[], elapsed_s=0.1, out=buf)
    text = buf.getvalue()
    assert "Ordered tool calls:" in text
    assert "(none)" in text


def test_setup_run_plan_resolves_token_and_skips_pr_state(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_test")
    scenario = {
        "id": "hf-jobs-plan", "kind": "plan",
        "prompt_template": "do a plan",
        "mcp_server": {"endpoint": "http://localhost:8083/mcp", "alias": "hf_skills"},
    }
    ctx = setup_run(scenario)
    assert ctx["kind"] == "plan"
    assert ctx["token"] == "hf_test"
    assert ctx["token_env_var"] == "HF_TOKEN"
    assert ctx["server_alias"] == "hf_skills"
    assert ctx["server_endpoint"] == "http://localhost:8083/mcp"
    assert ctx["repo"] is None
    assert ctx["pr_number"] is None
    # Plan prompts have no {pr_number}/{repo} substitution.
    assert ctx["prompt"] == "do a plan"


def test_setup_run_pr_review_uses_github_token_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "gh_test")
    monkeypatch.setenv("PR_NUMBER", "42")  # bypass `gh pr list`
    scenario = {
        "id": "pr-review", "kind": "pr-review",
        "prompt_template": "review #{pr_number} on {repo}",
        "mcp_server": {"endpoint": "http://localhost:8082/mcp", "alias": "github_skills"},
        "repo": "owner/sandbox", "head_branch": "f", "scaffolding_script": "ignored.sh",
    }
    ctx = setup_run(scenario)
    assert ctx["kind"] == "pr-review"
    assert ctx["token"] == "gh_test"
    assert ctx["token_env_var"] == "GITHUB_TOKEN"
    assert ctx["repo"] == "owner/sandbox"
    assert ctx["pr_number"] == 42
    assert ctx["prompt"] == "review #42 on owner/sandbox"


def test_setup_run_missing_alias_exits():
    scenario = {
        "id": "x", "kind": "plan",
        "prompt_template": "...",
        "mcp_server": {"endpoint": "http://localhost:8083/mcp"},  # no alias
    }
    with pytest.raises(SystemExit) as ei:
        setup_run(scenario)
    assert "alias" in str(ei.value)
