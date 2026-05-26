"""Scenario YAML loader.

Scenarios declare a base set of fields (id, prompt_template, mcp_server);
scenarios that mutate state additionally declare `scaffolding_script`,
which triggers PR-style setup (repo + head_branch + prompt substitution)
in `setup.py`. We don't have a `kind` discriminator — the presence of
`scaffolding_script` is the only structural signal that flips behavior.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_BASE_REQUIRED = ("id", "prompt_template")


def load_scenario(path: Path) -> dict:
    """Load and validate a scenario YAML. Exits on missing file or fields."""
    if not path.exists():
        sys.exit(f"Scenario YAML not found at {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        sys.exit(f"Scenario YAML at {path} did not parse to a mapping")

    missing = [f for f in _BASE_REQUIRED if not data.get(f)]
    if missing:
        sys.exit(f"Scenario YAML at {path} is missing required fields: {', '.join(missing)}")

    if data.get("scaffolding_script"):
        scaffold_missing = [f for f in ("repo", "head_branch") if not data.get(f)]
        if scaffold_missing:
            sys.exit(
                f"Scenario YAML at {path} declares scaffolding_script but is "
                f"missing: {', '.join(scaffold_missing)}"
            )
    return data


def parse_scenario_arg(argv: list[str]) -> Path:
    """Parse the required positional scenario-YAML path, ignoring flags."""
    args = [a for a in argv[1:] if not a.startswith("-")]
    if len(args) != 1:
        sys.exit(
            "Usage: agent.py <scenario-yaml-path>\n"
            "The scenario YAML path is a required positional argument."
        )
    return Path(args[0]).resolve()
