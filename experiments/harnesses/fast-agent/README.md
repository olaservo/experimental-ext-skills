# skills-e2e-fast-agent

Scenario #1 harness for `evalstate/fast-agent @ main` (upstream — carries
the merged SEP-2640 registry/install code that consumes the prod HF
server's digest-gated `skill://*.tar.gz` archives).
Library-embed (Python) — `pyproject.toml` git-deps the branch;
`uv sync` clones it to uv's cache.

- **Runbook + env-var reference + pass-criteria details**: the
  docstring at the top of `agent.py`.
- **Cross-client orientation** (MCP server launch, scaffolding, the
  other three harnesses): the workspace `experiments/CLAUDE.md`.
