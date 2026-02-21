# Related Work

## Open SEPs and Proposals

| Proposal | Venue | Description |
| :--- | :--- | :--- |
| [SEP-2076](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2076) | MCP Spec | Agent Skills as a first-class MCP primitive |
| [skills.json format proposal](https://github.com/modelcontextprotocol/registry/discussions/895) | MCP Registry | Skills metadata in registry schema |

## Implementations

Original implementations from external repositories (example implementations in this repo will be added to `examples` folder):

| Implementation | Author | URL | Notes |
| :--- | :--- | :--- | :--- |
| skilljack-mcp | Ola Hungerford | [github.com/olaservo/skilljack-mcp](https://github.com/olaservo/skilljack-mcp) | Skills as MCP tools, resources, prompts with dynamic updates |
| mcpGraph skill | Bob Dickinson | [github.com/TeamSparkAI/mcpGraph](https://github.com/TeamSparkAI/mcpGraph) | Complex skill example for graph orchestration |
| skills-over-mcp | Keith Groves | [github.com/keithagroves/skills-over-mcp](https://github.com/keithagroves/skills-over-mcp) | Example using skills as MCP resources with current MCP primitives |
| chrome-devtools-mcp | Anthropic | [github.com/anthropics/anthropic-quickstarts/…/chrome-devtools-mcp](https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp-servers/chrome-devtools-mcp) | Real-world example: `skills/` folder requires separate install path |
| NimbleBrain skills repo | NimbleBrain | [github.com/NimbleBrainInc/skills](https://github.com/NimbleBrainInc/skills) | Monorepo with `.skill` artifact format |
| NimbleBrain registry | NimbleBrain | [registry.nimbletools.ai](https://registry.nimbletools.ai/) | Registry with skill metadata support |
| FastMCP 3.0 Skills | FastMCP | [gofastmcp.com/servers/providers/skills](https://gofastmcp.com/servers/providers/skills) | Native skills provider ([#2694](https://github.com/jlowin/fastmcp/issues/2694)) |
| PydanticAI Skills | PydanticAI | [pydantic/pydantic-ai#3780](https://github.com/pydantic/pydantic-ai/pull/3780) | Agent skills with tools-based approach |
| mcp-cli | philschmid | [github.com/philschmid/mcp-cli](https://github.com/philschmid/mcp-cli) | Wraps MCP servers as CLI for progressive disclosure |
| mcp-execution | bug-ops | [github.com/bug-ops/mcp-execution](https://github.com/bug-ops/mcp-execution) | Compiles MCP servers into skill packages |
| Astronomer agents | Kaxil Naik | [github.com/astronomer/agents](https://github.com/astronomer/agents) | Skills distribution via MCP for Apache Airflow |
| my-cool-proxy | karashiiro | [github.com/karashiiro/my-cool-proxy](https://github.com/karashiiro/my-cool-proxy) | MCP gateway server with skills as resources via Lua scripts |
| code-execution-with-mcp | Ola Hungerford | [github.com/olaservo/code-execution-with-mcp](https://github.com/olaservo/code-execution-with-mcp) | Code execution vs direct MCP tool calls demo |
| lootbox | jx-codes | [github.com/jx-codes/lootbox](https://github.com/jx-codes/lootbox) | Code mode with auto-discovery and type generation (successor to codemode-mcp) |
| mcp-server-code-execution-mode | elusznik | [github.com/elusznik/mcp-server-code-execution-mode](https://github.com/elusznik/mcp-server-code-execution-mode) | Python code execution in rootless containers with MCP proxying |

## External Resources

- **Agent Skills Standard:** [agentskills.io](https://agentskills.io/)
- **Anthropic's guidance on progressive disclosure:** [Equipping agents for the real world with agent skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- **"MCP and Skills: Why Not Both?"** (Kurtis Van Gent): [kvg.dev/posts/20260125-skills-and-mcp/](https://kvg.dev/posts/20260125-skills-and-mcp/) — Frames MCP (connectivity) and Skills (context saturation) as complementary; discusses hybrid approaches
- **Conceptual spec visualization** (Keith Groves): [enact-465fb1fc.mintlify.app/specification/draft/server/skills](https://enact-465fb1fc.mintlify.app/specification/draft/server/skills) — "What if" exploration
- **Apache Airflow AIP-91** (MCP integration): [cwiki.apache.org/…/AIP-91+-+MCP](https://cwiki.apache.org/confluence/display/AIRFLOW/AIP-91+-+MCP)
- **Cloudflare "Code Mode: the better way to use MCP":** [blog.cloudflare.com/code-mode/](https://blog.cloudflare.com/code-mode/) — Introduces the "code mode" pattern: converting MCP tools into TypeScript APIs and executing agent-generated code in sandboxed V8 isolates
- **Anthropic "Code execution with MCP: Building more efficient agents":** [anthropic.com/engineering/code-execution-with-mcp](https://www.anthropic.com/engineering/code-execution-with-mcp) — Filesystem-based tool discovery with progressive disclosure; reports 98.7% token reduction
- **Goose Code Mode MCP:** [block.github.io/goose/blog/2025/12/15/code-mode-mcp/](https://block.github.io/goose/blog/2025/12/15/code-mode-mcp/) — Open-source code mode implementation using embedded Rust-based JS engine
- **CodeAct: Executable Code Actions Elicit Better LLM Agents** (Wang et al., ICML 2024): [arXiv 2402.01030](https://arxiv.org/abs/2402.01030) — Foundational academic validation of code-as-action paradigm; up to 20% higher success rate vs JSON tool-calling across 17 LLMs
- **Voyager: An Open-Ended Embodied Agent with Large Language Models** (Wang et al., NeurIPS 2023): [arXiv 2305.16291](https://arxiv.org/abs/2305.16291) — Pioneered persistent skill library of executable code
- **Video background:** [youtube.com/watch?v=CEvIs9y1uog](https://www.youtube.com/watch?v=CEvIs9y1uog)
