"""Provider-token resolution + skill-URI canonicalization."""

from __future__ import annotations

import os
import subprocess
import sys


# Known sub-directory names that appear inside a skill bundle. The
# segment immediately preceding one of these in a skill URI is the
# skill name. Servers that namespace skills (e.g. github-mcp-server's
# `skill://github/<skill>/...`) make the first path segment the
# namespace, not the skill — walking back from a known sub-directory
# (or from `SKILL.md`) is what reliably identifies the skill itself.
_SKILL_SUBDIRS = frozenset({"references", "scripts", "assets", "templates"})


def skill_name_from_arg(val: str) -> str:
    """Map a skill URI/name to the canonical skill name.

    Normalizes all the forms clients use to identify a skill:
      - `skill://pull-requests/SKILL.md`            -> `pull-requests`
      - `skill://github/pull-requests/SKILL.md`     -> `pull-requests`
        (servers that namespace skills, e.g. github-mcp-server's
        catalog after the `skill://github/...` switch)
      - `skill://huggingface-llm-trainer/references/training_methods.md`
                                                    -> `huggingface-llm-trainer`
      - `pull-requests`                             -> `pull-requests`
      - `pull-requests/scripts/train.py`            -> `pull-requests`
        (goose's `load_skill {"name": "<skill>/<path>"}` form —
        crates/goose/src/agents/platform_extensions/skills.rs)
      - `github_skills__pull-requests`              -> `pull-requests`
        (goose's `<server>__<name>` disambiguation form when two
        servers expose a same-named skill — same source file L555)
    """
    if val.startswith("skill://"):
        path = val.removeprefix("skill://")
        segments = [s for s in path.split("/") if s]
        if not segments:
            return ""
        # Skill index URIs end with `/SKILL.md`; the skill name is the
        # directory containing it.
        if segments[-1] == "SKILL.md" and len(segments) >= 2:
            return segments[-2]
        # Reference / script / asset URIs: the skill name is the
        # segment immediately preceding the known sub-directory.
        for i in range(len(segments) - 1, 0, -1):
            if segments[i] in _SKILL_SUBDIRS:
                return segments[i - 1]
        # No marker found (rare — bare `skill://name` form). Fall back
        # to the first segment so namespace-less single-segment URIs
        # still resolve.
        return segments[0]
    # Non-URI forms: take first path segment, then strip any
    # `<server>__` disambiguation prefix.
    val = val.split("/", 1)[0]
    return val.rsplit("__", 1)[-1]


def matches_expected_skill_uri(target: str, expected_uri: str) -> bool:
    """Match a skill-read target against an expected `skill://` URI.

    Strong (URI-exact) match: when the target is itself a `skill://`
    URI, require byte-for-byte equality with `expected_uri`. This
    catches namespace/path divergence (e.g. scenario YAML pointing at
    `skill://pull-requests/...` while the server advertises
    `skill://github/pull-requests/...`) that name-based comparison
    would silently absorb.

    Bare-name fallback: clients like goose (`load_skill {"name": ...}`)
    and gemini-cli (`activate_skill {"name": ...}`) activate skills by
    bare name and never produce a URI on the call boundary. For those,
    fall back to comparing the parsed skill name on each side.
    """
    if target.startswith("skill://"):
        return target == expected_uri
    return skill_name_from_arg(target) == skill_name_from_arg(expected_uri)


def resolve_github_token() -> str:
    """Return a GitHub token from env, falling back to `gh auth token`."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        return subprocess.check_output(
            ["gh", "auth", "token"], encoding="utf-8"
        ).strip()
    except Exception as exc:
        sys.exit(
            f"GITHUB_TOKEN not set and `gh auth token` failed: {exc}. "
            f"Export a PAT via GITHUB_TOKEN, or run `gh auth login` first."
        )


def resolve_hf_token() -> str:
    """Return a Hugging Face token from env (HF_TOKEN or DEFAULT_HF_TOKEN)."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("DEFAULT_HF_TOKEN")
    if token:
        return token
    sys.exit(
        "HF_TOKEN not set. Generate one at https://huggingface.co/settings/tokens "
        "and either export HF_TOKEN or source an env-file with `set -a && . FILE && set +a`."
    )
