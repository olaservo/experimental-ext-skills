# skills-e2e-hermes

Harness for `olaservo/hermes-agent @ feature/add-skill-over-mcp-support`.
Python subprocess driving `hermes chat -q "<prompt>"`; tool calls are
recovered from hermes's SQLite session store (`$HERMES_HOME/state.db`,
table `messages`) since hermes has no JSON stream output. The `hermes`
binary comes from the fork branch (install per the hermes-agent repo;
`uv pip install -e ".[all]"` from a clone, or `./setup-hermes.sh`).

The harness runs hermes with a hermetic `HERMES_HOME` tempdir, so its
written `config.yaml` (model + MCP server + `mcp.skills_extension:
experimental`), materialized MCP skills, and session DB never touch the
user's real `~/.hermes/`.

- **Runbook + env-var reference** (`HERMES_VARIANT`, `HERMES_MODEL`,
  `HERMES_TIMEOUT_S`, `HERMES_BIN`) and the install/PATH-shadowing
  caution: the docstring at the top of `agent.py`.
- **Cross-client orientation** (MCP server launch, scaffolding, the
  other harnesses): the `run-scenario` skill and the per-scenario
  sub-pages under `.claude/skills/run-scenario/`.

Only HTTP MCP servers are supported today (pr-review,
repo-skills-discovery, transformers-js-demo); the stdio `birch` scenario
is not wired here yet — same as goose.
