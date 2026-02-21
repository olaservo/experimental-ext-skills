# Code Mode: Skills as a Bridge Between MCP and Local Code Execution

> **Scope note:** Code mode is fundamentally about *execution* — how agents consume tools — rather than *discovery and distribution* of skills, which is this IG's primary charter. This document is included as a reference because code mode intersects with skill design (e.g., when skills encode decision logic about direct calls vs. code execution) and with open IG questions like multi-server composition ([Use Case 3](use-cases.md#3-multi-server-composition)) and the optimal relationship between skills and MCP ([Open Question 13](open-questions.md#13-what-is-the-optimal-relationship-between-skills-and-mcp)). Platform-level concerns like sandbox implementations, wrapper formats, and execution environments are documented here for context but are not proposed as IG deliverables — that work is happening independently in the projects referenced below.

## What Is Code Mode?

"Code mode" is an emerging pattern where agents generate and execute code against typed wrapper files for MCP tools, rather than making direct tool calls. Instead of presenting all connected MCP tools to the model and receiving structured tool-call responses, the agent is given a code execution environment with typed APIs representing those tools. The model writes code — with loops, conditionals, variables, and local data processing — that calls the MCP tools programmatically.

The pattern has deep academic roots (see [CodeAct](#academic-foundations) below) and was applied to MCP independently by [Cloudflare](https://blog.cloudflare.com/code-mode/) (September 2025) and [Anthropic](https://www.anthropic.com/engineering/code-execution-with-mcp) (November 2025), and has since been implemented by [Goose](https://block.github.io/goose/blog/2025/12/15/code-mode-mcp/), [lootbox](https://github.com/jx-codes/lootbox), and others.

**Key mechanisms:**

- **Typed wrapper generation:** MCP tool schemas are converted to TypeScript/JavaScript interfaces that agents can call as functions
- **Filesystem-based progressive discovery:** Rather than loading all tool definitions upfront, agents explore a filesystem structure of wrapper files on demand
- **Sandboxed execution:** Generated code runs in an isolated environment (V8 isolates, embedded JS engines, Docker) with access only to the MCP tool APIs
- **Local data processing:** Intermediate results stay in the execution environment — data transformations happen in code, not through the model's context window

**Core benefits observed across implementations:**

- **Token efficiency:** Reported reductions vary by scenario — from 32% on simple single-event tasks (Cloudflare) to 81% on complex batch operations (Cloudflare), 37% on multi-tool orchestration (Anthropic PTC API), and up to 98.7% on workflows involving large data transfers (Anthropic blog). The highest figures reflect both on-demand tool loading and keeping intermediate data out of context, so they represent an upper bound for data-heavy, multi-server scenarios rather than a typical improvement.
- **Context overflow prevention:** Workflows involving thousands of records that would overflow context in direct mode complete successfully in code mode.
- **Control flow efficiency:** Loops, conditionals, and retries execute natively rather than requiring model round-trips.
- **Privacy preservation:** Sensitive intermediate data can remain in the sandbox, never entering the model's context.
- **Training alignment:** LLMs are extensively trained on code and perform more naturally writing programmatic API calls than constructing tool-call JSON. CodeAct (ICML 2024) empirically validated this: code actions outperformed JSON tool-calling by up to 20% success rate across 17 LLMs.

## Prior Art

### Academic Foundations

The code-as-action paradigm predates its application to MCP. Key academic work includes:

- **CodeAct** (Wang et al., [arXiv 2402.01030](https://arxiv.org/abs/2402.01030), ICML 2024) — The foundational empirical validation: using executable Python code as an agent action space outperformed JSON and text tool-calling alternatives by up to 20% higher success rate across 17 LLMs, requiring 30% fewer steps. CodeAct directly inspired Cloudflare's Code Mode and most downstream implementations.
- **PAL: Program-Aided Language Models** (Gao et al., ICML 2023) — Early demonstration that LLMs generate more reliable outputs when reasoning through executable code.
- **Code as Policies** (Liang et al., Google, ICRA 2023) — Applied code generation to robotics policy specification, establishing code as a natural interface between language models and tool execution.
- **Voyager** (Wang et al., NVIDIA/Caltech, NeurIPS 2023) — Pioneered a **persistent skill library of executable code** for Minecraft agents. Agents write, verify, and store reusable code functions — directly mapping to the vision of skills that persist across sessions and bridge code mode with the skills pattern.
- **TaskWeaver** (Qiao et al., Microsoft, [arXiv 2311.17541](https://arxiv.org/abs/2311.17541), November 2023) — A code-first agent framework converting natural language to executable Python with plugins-as-functions, closely paralleling code mode's architecture.

### Major Framework Implementations

Several frameworks now implement the code-as-action pattern outside the MCP ecosystem:

- **[OpenHands](https://github.com/All-Hands-AI/OpenHands)** (formerly OpenDevin, ICLR 2025) — The most complete open-source platform implementing a CodeActAgent in production.
- **[HuggingFace smolagents](https://huggingface.co/docs/smolagents)** — Offers a `CodeAgent` class reporting 30% fewer LLM calls than JSON tool-calling.
- **[LangGraph CodeAct](https://github.com/langchain-ai/langgraph-codeact)** — Explicitly noted as "the architecture used by Manus.im."

Anthropic has also productized code execution as a first-party API feature called **Programmatic Tool Calling (PTC)**, reducing average token usage from 43,588 to 27,297 (37% reduction) and eliminating 19+ inference passes when orchestrating 20+ tool calls.

### MCP-Specific Implementations

#### Cloudflare: "Code Mode: the better way to use MCP" (September 2025)

[Cloudflare's blog post](https://blog.cloudflare.com/code-mode/) introduced the term "code mode" and provided the first public implementation. Their key insight: LLMs are trained on vast repositories of actual code, but tool-calling formats are synthetic constructs that barely appear in training data. The model is fluent in JavaScript but less natural in function-call JSON.

Their architecture converts MCP tool schemas into TypeScript interfaces, presents the agent with a single "execute code" tool, and runs the generated code in a sandboxed Cloudflare Worker (V8 isolate). The sandbox's only access to the outside world is through the typed APIs, which route back to the agent loop for MCP server dispatch.

Code Mode is integrated into the [Cloudflare Agents SDK](https://developers.cloudflare.com/agents/).

#### Anthropic: "Code execution with MCP: Building more efficient agents" (November 2025)

[Anthropic's blog post](https://www.anthropic.com/engineering/code-execution-with-mcp) arrived at the same pattern independently. Their framing emphasizes filesystem-based tool discovery with progressive disclosure: each MCP tool becomes a TypeScript file in a structured directory, and agents load only what they need by exploring the filesystem or using a `search_tools` function.

Key quote from the blog post:

> "Converting a manual tool-calling pattern to code execution reduced token consumption from 150,000 to 2,000 — a 98.7% savings on a Google Drive-to-Salesforce workflow."

The post also highlights privacy benefits: intermediate results remain in the execution sandbox, and sensitive data can be tokenized before reaching the model.

#### code-execution-with-mcp (Ola Hungerford)

[code-execution-with-mcp](https://github.com/olaservo/code-execution-with-mcp) is a demonstration project using the Claude Agent SDK that directly compares "Code Execution Mode" vs. "Direct MCP Mode" on real datasets.

**Results:**

| Scenario | Code Execution | Direct MCP |
| :--- | :--- | :--- |
| Large dataset (5,205 GitHub issues) | 100% success, ~$0.34 | 0% success (context overflow after ~600 issues) |
| Small dataset (45 GitHub issues) | 100% success, 3.5x faster, 67% cheaper | 100% success, but 7.4x more output tokens |

The project also demonstrated that agents can develop persistent, reusable skills from the generated wrappers — creating a natural bridge between code mode and the skills pattern.

**Trade-off observed:** On smaller datasets, code execution required more agent turns due to code development overhead. The benefit is most pronounced when datasets are large, require filtering/transformation before analysis, need joining from multiple sources, or represent workflows that will be repeated.

#### Goose: Code Execution Extension (December 2025)

[Goose v1.17.0](https://block.github.io/goose/blog/2025/12/15/code-mode-mcp/) added a "Code Execution" platform extension that generates JavaScript interfaces from connected MCP tools and executes agent-generated code using [boa](https://github.com/boa-dev/boa), an embeddable Rust-based JavaScript engine. Their implementation reduces the model's tool surface to three meta-tools: search available modules, read tool source, and execute code.

#### lootbox (jx-codes)

[lootbox](https://github.com/jx-codes/lootbox) (successor to the now-deprecated [codemode-mcp](https://github.com/jx-codes/codemode-mcp)) implements the Cloudflare code mode pattern with auto-discovery and type generation.

#### mcp-server-code-execution-mode (elusznik)

[mcp-server-code-execution-mode](https://github.com/elusznik/mcp-server-code-execution-mode) executes Python code in isolated rootless containers with MCP server proxying, achieving ~200-token constant overhead.

#### mcp-execution (bug-ops)

[mcp-execution](https://github.com/bug-ops/mcp-execution) generates executable TypeScript tools from MCP servers with progressive loading, bridging the server-based delivery model with local code execution.

## The Bidirectional Value Proposition

The relationship between MCP and code mode appears to be complementary — each provides something the other lacks.

### What MCP Provides to Code Mode

- **Discovery:** MCP registries and `tools/list` give agents a standard way to find available tools. Code mode needs tool schemas to generate wrappers — MCP provides those schemas through an established protocol.
- **Trust model:** When a user authorizes an MCP server, that trust boundary extends to the tool wrappers generated from its schema. Code mode inherits MCP's existing consent and authorization model rather than needing its own.
- **Delivery and transport:** MCP handles the actual communication with tool backends (HTTP, stdio, SSE). Code mode's generated wrappers are thin clients that delegate to MCP's transport layer.
- **Versioning and updates:** MCP's `tools/listChanged` notifications can trigger wrapper regeneration when tools evolve, keeping code mode APIs current.

### What Code Mode Provides to Skills

- **Token efficiency enables larger workflows:** Skills that would overflow context when orchestrating dozens of tool calls become feasible when the agent can write code that chains those calls locally.
- **Local data processing preserves privacy:** Skills involving sensitive data (customer records, credentials, PII) can process that data in a sandbox without it entering the model's context.
- **State persistence enables skill reuse:** Agents can write results to files and develop reusable code functions — effectively creating new skills through code mode execution. This echoes Voyager's persistent skill library (NeurIPS 2023), where agents built and reused a growing library of executable code functions across sessions.
- **Code generation aligns with model strengths:** LLMs are naturally better at writing code than at constructing sequences of tool calls. Skills that instruct agents to write code against APIs may be more reliably followed than skills that prescribe specific tool-call sequences.

## How Skills Enable Code Mode

The [Agent Skills Open Standard](https://agentskills.io/) is seeing broad adoption — Anthropic (Claude Code), OpenAI (Codex), GitHub (Copilot), and Google (Antigravity) all implement variations. Skills may be the missing piece that makes code mode practical at scale. Several connections emerge:

### Skills teach agents *when* to use code mode vs. direct calls

Not every interaction benefits from code mode. Small, single-step tool calls may be more efficient as direct calls. Skills can encode this decision logic:

- "For datasets over N records, use code mode to filter locally before returning results"
- "For multi-step workflows involving tools X, Y, and Z, write a script that chains them"
- "For simple lookups, call the tool directly"

This connects to [Use Case 2: Conditional Workflows](use-cases.md#2-conditional-workflows) — skills that branch based on context.

### Skills can include or reference generated wrappers

A skill distributed alongside an MCP server could include pre-generated wrapper files, typed interfaces, or example code that agents use as a starting point for code generation. This is analogous to how skills already include `scripts/` directories with bundled files.

### Skills can progressive-disclose the code execution pattern

Rather than loading all wrapper files at once, a skill can guide the agent through filesystem-based discovery — "search for available tools in `servers/`, read the ones relevant to your task, then write code using them." This connects directly to [Use Case 4: Progressive Disclosure](use-cases.md#4-progressive-disclosure).

### Skills can compose tools across servers in code

A persistent challenge in the IG's research is [Use Case 3: Multi-Server Composition](use-cases.md#3-multi-server-composition) — skills that orchestrate tools from multiple servers. Code mode offers a natural solution: a skill can teach an agent to write code that imports wrappers from multiple servers and combines them in a single execution, without needing a gateway or composition layer.

## How Code Mode Enhances Skills

### Workflows that would overflow context become feasible

The mcpGraph skill ([Use Case 1](use-cases.md#1-complex-workflow-orchestration)) requires 875+ lines of instructions for graph orchestration involving many tool calls. In direct mode, the intermediate results of those calls flow through the model's context. In code mode, the skill's instructions could focus on the *logic* of graph construction while the actual tool chaining happens in sandboxed code.

### Skills become more portable across model capabilities

Direct tool-calling behavior varies across models and model versions. Code generation is a more universal capability — skills that instruct agents to write code against typed APIs may be more portable than skills that depend on specific tool-calling patterns.

### Skills can teach code mode patterns themselves

A meta-skill could teach agents the code mode pattern itself: "When you encounter a large dataset or multi-step workflow, generate TypeScript wrappers for the relevant MCP tools and execute your analysis as code." This turns code mode from an infrastructure choice into an agent-learnable technique.

## Connection to Existing Approaches

Code mode is not a distribution mechanism — it doesn't address how skills are discovered, delivered, or managed. It addresses a different question: **how agents execute against the tools that skills describe.** This makes it a cross-cutting consumption pattern that intersects with several existing approaches without competing with them.

- **[Approach 4: Gateway/Composition Pattern](approaches.md#4-gatewaycomposition-pattern)** — Code mode offers another way to "load primitives without the full server boundary." Where a gateway composes servers at the infrastructure level, code mode composes tool calls at the execution level.
- **[Approach 5: Server Instructions Reference](approaches.md#5-server-instructions-reference)** — Code mode's filesystem-based discovery naturally implements deferred loading: agents explore tool wrappers only when needed.
- **[Approach 6: Official Convention](approaches.md#6-official-convention-as-intermediate-step)** — A skills convention could include guidance on when and how to use code mode, making it part of the recommended pattern.

Code mode also offers a concrete perspective on [Open Question 13: What is the optimal relationship between skills and MCP?](open-questions.md#13-what-is-the-optimal-relationship-between-skills-and-mcp) — skills provide the workflow knowledge and discovery that MCP alone can't offer, while code mode provides an execution model that makes skills more efficient and capable than direct tool calling alone.

## Open Questions

### 1. What execution environments are appropriate for code mode?

Cloudflare uses V8 isolates (Workers), Goose uses an embedded Rust-based JS engine (boa), and the Anthropic demo uses unrestricted local execution. What sandboxing should skills assume or require? Should skill metadata include execution environment requirements?

### 2. When should agents use code mode vs. direct calls?

Can skills encode decision heuristics? What data characteristics (dataset size, number of tool calls, transformation complexity) reliably predict when code mode is more efficient? The small-dataset trade-off observed in code-execution-with-mcp (more agent turns for code development overhead) suggests the boundary isn't obvious.

### 3. Should there be a convention for wrapper generation?

Multiple implementations generate TypeScript wrappers from MCP tool schemas (Cloudflare Agents SDK, Anthropic's blog pattern, Goose, mcp-execution), but each uses a proprietary format. OpenAPI-to-SDK generation is mature (OpenAPI Generator supports 50+ languages), but nothing specifically targets MCP tool schemas for agent consumption. Should there be a standard format for these wrappers so that skills can reference them portably? Or is wrapper generation inherently implementation-specific?

### 4. How should skill format evolve to support code mode?

Should SKILL.md support code mode-specific metadata — available wrappers, execution environment requirements, example code snippets? Or should code mode remain an implementation detail that skills don't need to be aware of?

### 5. How does code mode affect the trust model?

When a skill instructs an agent to execute generated code, the trust boundary extends beyond MCP tool authorization to code execution. Research in this area is active: "The Dark Side of LLMs" (arXiv 2507.06850) found that 82.4% of LLMs execute malicious tool calls when requested by peer agents; [AgentBox](https://arxiv.org/abs/2510.21236) proposes OS-level permission enforcement with containerized sandboxing; and the [MCP security survey](https://arxiv.org/abs/2503.23278) specifically addresses injection risks when allowing agents to run code through MCP servers. This connects to [Open Question 10: How should skills handle security and trust boundaries?](open-questions.md#10-how-should-skills-handle-security-and-trust-boundaries) — but with additional surface area from the sandbox itself.

### 6. Is code mode a skill-level or platform-level concern?

Cloudflare and Goose implement code mode at the platform/SDK level — it's transparent to the skill. The Anthropic approach and code-execution-with-mcp make it more explicit, with the agent actively choosing to write code. Should skills assume code mode is available, or should they work regardless of whether the platform supports it?

## Areas for Further Research

The existing literature on code mode is heavy on success stories but light on empirical analysis of boundaries and failure modes. The IG is positioned to produce findings that would be immediately useful to skill authors and platform implementers — and that don't duplicate the blog posts and framework docs that already exist. The common thread across these priorities is producing **empirical results** rather than opinions.

### Priority 1: The decision boundary — when code mode helps vs. hurts

This is the highest-value empirical question nobody has rigorously answered. Existing benchmarks are uniformly positive ("look how much we saved"), but the code-execution-with-mcp project already surfaced the key tension: on small datasets, code mode *added* overhead from code development turns. Nobody has systematically mapped where the crossover point is — by dataset size, number of chained tool calls, transformation complexity, number of servers involved, or model capability.

Controlled experiments across these dimensions could produce concrete heuristics that skills can encode (e.g., "if >N records, switch to code mode"; "if <M tool calls with no data transformation, use direct calls"). That would be immediately actionable for every skill author and platform implementer, and it doesn't duplicate anyone else's work.

### Priority 2: Cross-server composition through code mode

Multi-server orchestration is the IG's [Use Case 3](use-cases.md#3-multi-server-composition) and a problem without a clean solution. Gateway patterns add infrastructure complexity, and direct tool calling doesn't compose well across server boundaries. Code mode offers a natural answer: a skill teaches the agent to import wrappers from multiple servers and chain them in a single script.

Building two or three POCs that demonstrate this concretely — e.g., a skill that joins data from a GitHub server and a database server, or orchestrates a CI pipeline across multiple tool providers — would produce findings that directly inform whether skills need protocol-level composition support or whether code mode makes that unnecessary. That question has real spec implications.

### Priority 3: Trust boundary extension from skill-instructed code execution

The security research on agent code execution is substantial (see [Open Question 5](#5-how-does-code-mode-affect-the-trust-model) above), but nobody has analyzed the specific gap this document identifies: the distance between "user authorized this MCP server" and "a skill told the agent to write and execute arbitrary code against that server's API." That's a meaningfully different trust model than either pure MCP tool calls or general-purpose code execution, and it has direct implications for what skill metadata should include (execution environment requirements, sandbox constraints, permission escalation declarations). Documenting concrete threat scenarios and mitigation requirements could feed directly into SEP work.

### Lower priority (premature or narrower scope)

- **Wrapper convention standardization:** Matters eventually, but implementations are still diverging. Premature to standardize before the decision boundary and composition questions settle.
- **Cross-model evaluation:** Test whether code mode skills are more portable across different LLMs than direct tool-calling skills.
- **Meta-skill for code mode:** A skill that teaches agents the code mode pattern itself — a focused experiment rather than a primary research track.
- **Integration with other approaches:** Explore how code mode interacts with the sampling-based approach ([Approach 3 variant](approaches.md#variant-skills-via-sampling)) and gateway patterns ([Approach 4](approaches.md#4-gatewaycomposition-pattern)).
