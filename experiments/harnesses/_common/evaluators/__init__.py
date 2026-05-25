"""Tool-call logger for scenario runs.

The harness used to grade each run against per-kind criteria (skill-read
ordering, phrase-grep over the agent's output, workflow assertions). We
dropped grading in favor of plain observation: record the MCP tool calls
the client made and let the human read them.

`evaluate` exists to keep the `evaluate(...) -> result` shape that
`render_report`/`write_result_json` consume.
"""

from __future__ import annotations

from typing import Any


def evaluate(calls: list[tuple[str, str, dict]]) -> dict[str, Any]:
    return {"tool_calls": calls}
