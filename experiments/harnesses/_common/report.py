"""Banner printing + results-JSON writing.

The harness no longer grades runs against per-kind criteria — it just
records the MCP tool calls the client made. The banner is the ordered
call list plus a run footer (artifact/review URL/wall-clock); the JSON
record persists the same tool calls for later inspection.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

_BANNER_WIDTH = 72

# Sentinel: distinguishes "scenario has no notion of a review URL"
# (omit the line entirely) from "scenario expected one but lookup
# returned None" (still print, with a hint). pr-review scenarios pass
# review_url= explicitly even when the lookup fails; plan scenarios
# don't pass it at all.
_UNSET = object()


def render_report(
    *,
    calls: list[tuple[str, str, dict]],
    review_url=_UNSET,
    elapsed_s: float,
    timed_out: bool = False,
    final_text: str | None = None,
    artifact_path: str | None = None,
    raw_artifact_path: str | None = None,
    postprocess_status: str | None = None,
    out=sys.stdout,
) -> None:
    print(file=out)
    print("=" * _BANNER_WIDTH, file=out)
    print("Ordered tool calls:", file=out)
    if not calls:
        print("  (none)", file=out)
    for i, (name, raw_name, args) in enumerate(calls):
        compact = {k: v for k, v in (args or {}).items() if k != "body"}
        # Surface the namespaced raw name when it differs from the bare
        # name — that's where 3 of 4 clients carry the server identifier.
        prefix = f"{name} (raw={raw_name})" if raw_name and raw_name != name else name
        print(f"  [{i}] {prefix}  {json.dumps(compact, default=str)[:180]}", file=out)
    print(file=out)

    if review_url is not _UNSET:
        # Only PR-review scenarios produce a review URL. Suppressed for
        # plan-only scenarios where there's no server-side artifact.
        print(f"Review URL: {review_url or '(not found via gh api)'}", file=out)
    if artifact_path:
        # File-output plan scenarios. `artifact_path` is the
        # postprocessed (browser-openable) file; `raw_artifact_path` is
        # the preserved pre-postprocess copy.
        print(f"Artifact:   {artifact_path}", file=out)
        if raw_artifact_path:
            print(f"Raw:        {raw_artifact_path}", file=out)
        if postprocess_status:
            print(f"Postprocess: {postprocess_status}", file=out)
    print(f"Wall-clock: {elapsed_s:.1f}s{'  (TIMED OUT)' if timed_out else ''}", file=out)
    print("=" * _BANNER_WIDTH, file=out)
    print(file=out)
    if final_text is not None:
        print("Final assistant response:", file=out)
        print(final_text or "(no assistant text captured)", file=out)


def write_result_json(
    *,
    client: str,
    scenario_id: str,
    model: str | None,
    tool_calls: list[tuple[str, str, dict]],
    review_url=_UNSET,
    elapsed_ms: int,
    error: str | None = None,
    final_text: str | None = None,
    artifact_path: str | None = None,
    raw_artifact_path: str | None = None,
    postprocess_status: str | None = None,
    results_dir: Path | None = None,
) -> Path:
    """Write `results/<ISO-UTC>-<scenario>-<client>-<model>.json`.

    Written on every run, including crash paths — the file is the
    record that the run happened.
    """
    target_dir = results_dir or (Path(__file__).resolve().parents[2] / "results")
    target_dir.mkdir(parents=True, exist_ok=True)

    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_slug = (model or "unspecified").replace("/", "_").replace(":", "_")
    path = target_dir / f"{ts}-{scenario_id}-{client}-{model_slug}.json"

    payload = {
        "client": client,
        "elapsed_ms": elapsed_ms,
        "model": model,
        "scenario_id": scenario_id,
        "tool_calls": [
            {"args": dict(args or {}), "name": name, "raw_name": raw_name}
            for name, raw_name, args in tool_calls
        ],
    }
    if review_url is not _UNSET:
        payload["review_url"] = review_url
    if final_text is not None:
        payload["final_text"] = final_text
    if artifact_path is not None:
        payload["artifact_path"] = artifact_path
    if raw_artifact_path is not None:
        payload["raw_artifact_path"] = raw_artifact_path
    if postprocess_status is not None:
        payload["postprocess_status"] = postprocess_status
    if error is not None:
        payload["error"] = error

    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return path
