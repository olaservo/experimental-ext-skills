# Client Research: File-Based Agent Skills

> **Scope.** A baseline survey of how fifteen notable host clients implement *file-based* agent skills today, measured against the [agentskills.io client implementation guide](https://agentskills.io/client-implementation/adding-skills-support). Closed-source harnesses (Claude Code, Cursor, Sourcegraph Amp) are out of scope for this pass since the loader / catalog renderer / activation logic isn't readable.
>
> **Methodology.** Read each client's loader, catalog renderer, and tests directly. All file links are GitHub permalinks pinned to the commit that was checked at survey time (table below).

## Snapshot

| Client | Repo | Commit |
| :--- | :--- | :--- |
| adk-python | [google/adk-python](https://github.com/google/adk-python) | [`69fa777`](https://github.com/google/adk-python/commit/69fa777881b3cb161e5b3dcb005def9a2ad86904) |
| agent-framework | [microsoft/agent-framework](https://github.com/microsoft/agent-framework) | [`bc42874`](https://github.com/microsoft/agent-framework/commit/bc428746909966ae8dbe08d8ffa9f2cf1132d771) |
| cline | [cline/cline](https://github.com/cline/cline) | [`86f4634`](https://github.com/cline/cline/commit/86f463496cc814cf0055dbca4132b7f827425c53) |
| codex | [openai/codex](https://github.com/openai/codex) | [`67849d9`](https://github.com/openai/codex/commit/67849d950d843c954102adb0db0e11f993aefdb7) |
| crewAI | [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | [`c9100cb`](https://github.com/crewAIInc/crewAI/commit/c9100cb51d357f6e3ba7d9969a000571f051ca64) |
| deepagents | [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | [`a64ff43`](https://github.com/langchain-ai/deepagents/commit/a64ff430f14b76607dfb1d78234f928ed88a3af0) |
| fast-agent | [evalstate/fast-agent](https://github.com/evalstate/fast-agent) | [`502d32e`](https://github.com/evalstate/fast-agent/commit/502d32e266f3221d744977f38b7a9b4bc5b93947) |
| gemini-cli | [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) | [`4e17552`](https://github.com/google-gemini/gemini-cli/commit/4e175527a2b241a68afd5f1509a8bebc21a44dfe) |
| goose | [aaif-goose/goose](https://github.com/aaif-goose/goose) | [`45d8bf8`](https://github.com/aaif-goose/goose/commit/45d8bf81d09d478ceedba8f6d1f0ad906123a981) |
| hermes-agent | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | [`363cc93`](https://github.com/NousResearch/hermes-agent/commit/363cc936746c3f2964427b635f80f57df528da54) |
| mastra | [mastra-ai/mastra](https://github.com/mastra-ai/mastra) | [`560dd4f`](https://github.com/mastra-ai/mastra/commit/560dd4f521246b988e1244e7691230ad61bc1501) |
| openclaw | [openclaw/openclaw](https://github.com/openclaw/openclaw) | [`8a1e220`](https://github.com/openclaw/openclaw/commit/8a1e2202734476d79b462bbdf66e6291c26104d7) |
| opencode | [anomalyco/opencode](https://github.com/anomalyco/opencode) | [`ce89bcb`](https://github.com/anomalyco/opencode/commit/ce89bcb8e238401ea8fee000dc54539057d47dc4) |
| Roo-Code | [RooCodeInc/Roo-Code](https://github.com/RooCodeInc/Roo-Code) | [`ad25634`](https://github.com/RooCodeInc/Roo-Code/commit/ad256349058d3f84fd97517aabce4a119a234bbf) |
| vscode | [microsoft/vscode](https://github.com/microsoft/vscode) (API surface) + [microsoft/vscode-copilot-chat](https://github.com/microsoft/vscode-copilot-chat) (extension impl) | API [`530cb5d`](https://github.com/microsoft/vscode/commit/530cb5de713aec2e96059e2f6cf41a95403cdb3d) · ext [`9e668cb`](https://github.com/microsoft/vscode-copilot-chat/commit/9e668cb12144c701cf0f2c6b3458c00fe3da20f1) |

## At-a-glance comparison

| Client | Catalog format to model | Activation | Trust gating | Open issues/PRs to watch |
| :--- | :--- | :--- | :--- | :--- |
| **codex** (OpenAI) | Markdown `## Skills` section with optional alias table; 2% token budget | Mention-based (`$SkillName` or description match); full SKILL.md (frontmatter retained) | Repo scope gated on workspace trust; live filesystem watcher | Case-sensitivity bug [#20637](https://github.com/openai/codex/issues/20637) (`SKILL.MD` filename); per-plugin disable [#19268](https://github.com/openai/codex/issues/19268) |
| **gemini-cli** (Google) | XML `<available_skills>` block in system prompt (`name` + `description` + `location`); also enum-constrained on `activate_skill` tool schema; activation returns `<activated_skill>` XML with `<instructions>` + `<available_resources>` folder tree | Dedicated `activate_skill` tool with confirmation UI; body only | Workspace trust gate; per-skill confirmation prompt | Consent dialog UX [#26431](https://github.com/google-gemini/gemini-cli/pull/26431); path-based visibility for `.agents/skills` [#25833](https://github.com/google-gemini/gemini-cli/issues/25833) |
| **adk-python** (Google ADK) | XML `<available_skills><skill><name>…<description>…` from `format_skills_as_xml()` | Three tools: `list_skills`, `load_skill`, `load_skill_resource`; body returned by `load_skill` | Path-prefix checks on resource loads | Tracking issue [#3611](https://github.com/google/adk-python/issues/3611) (full Claude-skill compat); session-state injection PR [#5405](https://github.com/google/adk-python/pull/5405) |
| **deepagents** (LangChain) | Markdown bullets in system prompt: `- **name**: description … -> Read \`/path/SKILL.md\` for full instructions` | Standard `read_file` tool; no dedicated activation tool | Symlink-containment check against allowed skill roots | Loader bug [#2446](https://github.com/langchain-ai/deepagents/issues/2446) (`read_file` truncates SKILL.md); skill-pack PR [#1992](https://github.com/langchain-ai/deepagents/pull/1992) |
| **fast-agent** | XML `<available_skills>` with `<location>`, `<directory>`, and resolved `<scripts>`/`<references>`/`<assets>` paths | Dedicated `read_skill` MCP tool with absolute-path allowlist | Allowlist of skill directories enforced at tool boundary | _none yet — add as found_ |
| **opencode** | Catalog *not* prebuilt — `available_skills` block built on demand by `Skill.fmt`; activation returns `<skill_content>` block with sampled `<skill_files>` | Dedicated `skill` tool; calls `ctx.ask({permission: "skill", …})` for confirmation each load | Per-skill permission gate at activation; agent-level deny via `Permission.evaluate` | REST-API gap [#25686](https://github.com/anomalyco/opencode/issues/25686) (project skills missing in API sessions); multi-skill composition [#25570](https://github.com/anomalyco/opencode/issues/25570) |
| **openclaw** | XML `<available_skills>` from `formatSkillsForPrompt`; paths compacted to `~/...` to save tokens (~5–6 tokens/path) | Documented as "use the read tool to load a skill's file"; no bespoke activation tool | `SkillExposure.includeInAvailableSkillsPrompt` and per-skill `disableModelInvocation` opt-out | RFC [#74594](https://github.com/openclaw/openclaw/issues/74594) (Skill Capability Manifests v0); spec-conformance [#69475](https://github.com/openclaw/openclaw/issues/69475) |
| **goose** (Block) | Bullet list (`• name - description`) appended to MCP server instructions; no XML | Dedicated `load_skill(name)` tool (also accepts `name/path` for supporting files) | None visible in the loader | goose 2.0 Skills Management migration [#8686](https://github.com/block/goose/issues/8686); Windows user-skills bug [#8552](https://github.com/block/goose/issues/8552) |
| **vscode** (GitHub Copilot) | **No model-facing catalog string.** Skills become `vscode.ChatSkill` items surfaced via `ChatSessionCustomizationProvider` API | Editor-managed; the SKILL.md `Uri` is handed to the chat session, not the model directly | VS Code workspace trust + per-extension scoping | [vscode-copilot-chat#5101](https://github.com/microsoft/vscode-copilot-chat/issues/5101) (capability fields in SKILL.md frontmatter); [vscode#304721](https://github.com/microsoft/vscode/issues/304721) (extension-API for contributing skill folders) |
| **cline** | Markdown bullets (`- "name": description`) injected by `getSkillsSection()` | `use_skill(skill_name)` tool — single shot, no re-invocation per skill | Per-source toggles; remote `globalSkills` with `alwaysEnabled` admin lock that bypasses user UI | Loader error UX [#10455](https://github.com/cline/cline/pull/10455); slash-command precedence [#9281](https://github.com/cline/cline/pull/9281) |
| **Roo-Code** | XML `<available_skills>` paired with mandatory three-step skill-check directive; `modeSlugs` array scopes skills to specific personas | Dedicated `skill` tool with `skill` + `args`; per-invocation `askApproval` user gate | Approval flow + mode-scoping; no `allowed-tools` enforcement | Surface load errors PR [#12198](https://github.com/RooCodeInc/Roo-Code/pull/12198); discovery cap [#12194](https://github.com/RooCodeInc/Roo-Code/issues/12194); `.agents/skills` support [#11368](https://github.com/RooCodeInc/Roo-Code/issues/11368) |
| **crewAI** | **No catalog**; activated skill bodies are **eagerly concatenated into the task prompt** at agent init via `append_skill_context()` | Eager: `Crew.setup_agents()` discovers + activates every skill before the first model call | None visible; `allowed-tools` parsed but never referenced | _none — open `skill` issues in the repo currently refer to A2A AgentCard skills, not the SKILL.md format_ |
| **mastra** | XML `<available_skills>` (also `json` / `markdown`), sorted by name for cache stability | Three tools: `skill` (load), `skill_search` (BM25/vector/hybrid), `skill_read` (single resource); strategy resolved via `'live'`/`'latest'`/pinned `versionId` | Permission at tool layer; versioned skills resolved through content-addressable `BlobStore` | S3 perf blocker [#15457](https://github.com/mastra-ai/mastra/issues/15457); duplicate-context DX [#15908](https://github.com/mastra-ai/mastra/issues/15908) |
| **agent-framework** (Microsoft) | XML metadata in system prompt (~100 tokens/skill); `load_skill` returns raw SKILL.md body or richer XML envelope for code-defined skills | Three tools: `load_skill`, `read_skill_resource`, `run_skill_script` (last conditionally registered when any skill has scripts) | None at framework level; script execution delegated to pluggable `SkillScriptRunner` Protocol | Multi-source rewrite PR [#5584](https://github.com/microsoft/agent-framework/pull/5584); `apm.yml`-as-`package.json` RFC [#5571](https://github.com/microsoft/agent-framework/issues/5571) |
| **hermes-agent** (Nous Research) | Markdown with **category grouping** (from `DESCRIPTION.md` per category); two-layer cache (LRU + disk snapshot) keyed on tool/toolset/platform availability; conditional via `requires_tools`/`requires_toolsets` | Three paths: slash command (`/skill-name`), `--skill` CLI preload, dedicated `skill_view(name, file_path?)` tool. All paths run a template-variable + inline-shell preprocessor before injection | Disabled-skills list (per-platform); path containment; **prompt-injection pattern scanning** at load; pluggable secret-collection callback for `setup.collect_secrets` and `required_environment_variables` | Data-loss bug [#18659](https://github.com/NousResearch/hermes-agent/issues/18659) (`scan_skill_commands` clears state on failure); lifecycle-tier RFC [#17583](https://github.com/NousResearch/hermes-agent/issues/17583) |

## Per-client deep dives

### codex (OpenAI)

Implementation lives in the Rust crate at [`codex-rs/core-skills/`](https://github.com/openai/codex/tree/67849d950d843c954102adb0db0e11f993aefdb7/codex-rs/core-skills). The catalog record at [`core-skills/src/model.rs`](https://github.com/openai/codex/blob/67849d950d843c954102adb0db0e11f993aefdb7/codex-rs/core-skills/src/model.rs) carries a richer policy/interface model than any other client surveyed:

```rust
pub struct SkillMetadata {
    pub name: String,
    pub description: String,
    pub short_description: Option<String>,
    pub interface: Option<SkillInterface>,
    pub dependencies: Option<SkillDependencies>,
    pub policy: Option<SkillPolicy>,
    /// Path to the SKILLS.md file that declares this skill.
    pub path_to_skills_md: AbsolutePathBuf,
    pub scope: SkillScope,
}
```

`SkillPolicy.allow_implicit_invocation` and `SkillPolicy.products` let a skill opt out of model-driven activation or restrict itself to specific Codex products.

The catalog is rendered into the system prompt as markdown by [`render_available_skills_body`](https://github.com/openai/codex/blob/67849d950d843c954102adb0db0e11f993aefdb7/codex-rs/core-skills/src/render.rs). With aliases, the output is:

```
## Skills
A skill is a set of local instructions to follow that is stored in a `SKILL.md` file. ...
### Skill roots
- `r0` = `/Users/.../skills`
### Available skills
- alpha-skill: ab (file: r0/skill-name/SKILL.md)
### How to use skills
- Discovery: ...
- Trigger rules: If the user names a skill (with `$SkillName` or plain text) OR the task clearly matches a skill's description shown above, you must use that skill for that turn. ...
```

A 2 % session-token budget ([`SKILL_METADATA_CONTEXT_WINDOW_PERCENT`](https://github.com/openai/codex/blob/67849d950d843c954102adb0db0e11f993aefdb7/codex-rs/core-skills/src/render.rs)) is enforced. Descriptions are truncated equally before any skill is dropped, and a warning is appended once average truncation crosses 100 chars.

**Activation** is mention-based: [`injection.rs`](https://github.com/openai/codex/blob/67849d950d843c954102adb0db0e11f993aefdb7/codex-rs/core-skills/src/injection.rs)`::build_skill_injections` reads the full SKILL.md (frontmatter retained) and emits a `SkillInjection { name, path, contents }`. There is no dedicated `activate_skill` tool. [`core/src/skills_watcher.rs`](https://github.com/openai/codex/blob/67849d950d843c954102adb0db0e11f993aefdb7/codex-rs/core/src/skills_watcher.rs) hot-reloads on filesystem change — unique among the surveyed clients.

**Open issues/PRs to watch:**
- [#20637](https://github.com/openai/codex/issues/20637) — Codex skill discovery silently misses global skill when entry file is `SKILL.MD` (case-sensitivity bug).
- [#19268](https://github.com/openai/codex/issues/19268) — Support per-skill disable for plugin-contributed skills.
- [#20923](https://github.com/openai/codex/pull/20923) — Add plugin ID to skill analytics.

---

### gemini-cli (Google)

Implementation lives in [`packages/core/src/skills/`](https://github.com/google-gemini/gemini-cli/tree/4e175527a2b241a68afd5f1509a8bebc21a44dfe/packages/core/src/skills). Frontmatter parsing is [**dual-mode**](https://github.com/google-gemini/gemini-cli/blob/4e175527a2b241a68afd5f1509a8bebc21a44dfe/packages/core/src/skills/skillLoader.ts) — `js-yaml` first, falling back to a simple line parser that tolerates colons in description values. The [loaded record](https://github.com/google-gemini/gemini-cli/blob/4e175527a2b241a68afd5f1509a8bebc21a44dfe/packages/core/src/skills/skillLoader.ts) is intentionally minimal:

```ts
export interface SkillDefinition {
  name: string;
  description: string;
  location: string;       // absolute path
  body: string;           // SKILL.md after frontmatter
  disabled?: boolean;
  isBuiltin?: boolean;
  extensionName?: string;
}
```

The catalog is injected into the system prompt by [`renderAgentSkills`](https://github.com/google-gemini/gemini-cli/blob/4e175527a2b241a68afd5f1509a8bebc21a44dfe/packages/core/src/prompts/snippets.ts):

```
# Available Agent Skills

You have access to the following specialized skills. To activate a skill and receive its detailed instructions, call the activate_skill tool with the skill's name.

<available_skills>
  <skill>
    <name>web-research</name>
    <description>Structured approach to research</description>
    <location>/abs/path/web-research/SKILL.md</location>
  </skill>
</available_skills>
```

The dedicated `activate_skill` tool reinforces this with its [generated description](https://github.com/google-gemini/gemini-cli/blob/4e175527a2b241a68afd5f1509a8bebc21a44dfe/packages/core/src/tools/definitions/dynamic-declaration-helpers.ts) — the JSON schema constrains `name` to the discovered enum, and the description text inlines the available skill names:

```
Activates a specialized agent skill by name (Available: 'skill1', 'skill2'). Returns the skill's instructions wrapped in `<activated_skill>` tags. ... ONLY use names exactly as they appear in the `<available_skills>` section.
```

When invoked, [`ActivateSkillTool` returns XML](https://github.com/google-gemini/gemini-cli/blob/4e175527a2b241a68afd5f1509a8bebc21a44dfe/packages/core/src/tools/activate-skill.ts) wrapping the body plus a tree of bundled resources:

```ts
return {
  llmContent: `<activated_skill name="${skillName}">
  <instructions>
    ${skill.body}
  </instructions>

  <available_resources>
    ${folderStructure}
  </available_resources>
</activated_skill>`,
  // ...
};
```

Activation is gated by [`getConfirmationDetails`](https://github.com/google-gemini/gemini-cli/blob/4e175527a2b241a68afd5f1509a8bebc21a44dfe/packages/core/src/tools/activate-skill.ts) for non-built-in skills, showing the description and resource tree before the user confirms. The skill's directory is then added to the workspace context so subsequent file reads on bundled scripts/refs do not re-prompt.

**Open issues/PRs to watch:**
- [#26431](https://github.com/google-gemini/gemini-cli/pull/26431) — `fix(cli)#21297: clear skills consent dialog before reload` (very fresh).
- [#25833](https://github.com/google-gemini/gemini-cli/issues/25833) — Add path-based skill visibility controls for `.agents/skills`.
- [#26377](https://github.com/google-gemini/gemini-cli/issues/26377) — "Concise is key" in skills-creator strips instructions during update (meta-skill prompt bug).

---

### adk-python (Google ADK)

ADK is the only surveyed client where callers explicitly construct a list of `Skill` objects and pass them to `SkillToolset` rather than the framework auto-loading from the filesystem.

Validation is the strictest of any client. [`models.py`](https://github.com/google/adk-python/blob/69fa777881b3cb161e5b3dcb005def9a2ad86904/src/google/adk/skills/models.py) defines a Pydantic `Frontmatter` with kebab/snake-case name regex, max 64-char name, max 1024-char description, and an `allowed-tools` alias for the YAML-friendly key:

```python
class Frontmatter(BaseModel):
  model_config = ConfigDict(extra="allow", populate_by_name=True)

  name: str
  description: str
  license: Optional[str] = None
  compatibility: Optional[str] = None
  allowed_tools: Optional[str] = Field(
      default=None,
      alias="allowed-tools",
      serialization_alias="allowed-tools",
  )
  metadata: dict[str, Any] = {}
```

[`Skill`](https://github.com/google/adk-python/blob/69fa777881b3cb161e5b3dcb005def9a2ad86904/src/google/adk/skills/models.py) is a three-layer envelope mapping cleanly onto the agentskills.io progressive-disclosure tiers — `frontmatter` (L1), `instructions` (L2), `resources` (L3 with `references` / `assets` / `scripts`).

The catalog rendered to the model is XML ([`prompt.py`](https://github.com/google/adk-python/blob/69fa777881b3cb161e5b3dcb005def9a2ad86904/src/google/adk/skills/prompt.py)), HTML-escaped, and only contains `<name>` + `<description>` per skill:

```xml
<available_skills>
<skill>
<name>web-research</name>
<description>Structured approach to conducting thorough web research</description>
</skill>
</available_skills>
```

The XML is preceded in the system prompt by `_DEFAULT_SKILL_SYSTEM_INSTRUCTION` from [`skill_toolset.py`](https://github.com/google/adk-python/blob/69fa777881b3cb161e5b3dcb005def9a2ad86904/src/google/adk/tools/skill_toolset.py), which explains the four-tool activation contract:

```
You can use specialized 'skills' to help you with complex tasks. You MUST use the skill tools to interact with these skills.

Skills are folders of instructions and resources that extend your capabilities for specialized tasks. Each skill folder contains:
- **SKILL.md** (required): The main instruction file with skill metadata and detailed markdown instructions.
- **references/** (Optional): Additional documentation or examples for skill usage.
- **assets/** (Optional): Templates, scripts or other resources used by the skill.
- **scripts/** (Optional): Executable scripts that can be run via bash.

This is very important:

1. If a skill seems relevant to the current user query, you MUST use the `load_skill` tool with `skill_name="<SKILL_NAME>"` to read its full instructions before proceeding.
2. Once you have read the instructions, follow them exactly as documented before replying to the user. ...
3. The `load_skill_resource` tool is for viewing files within a skill's directory (e.g., `references/*`, `assets/*`, `scripts/*`). Do NOT use other tools to access these files.
4. Use `run_skill_script` to run scripts from a skill's `scripts/` directory. ...
```

Activation is split into three tools exposed by [`SkillToolset`](https://github.com/google/adk-python/blob/69fa777881b3cb161e5b3dcb005def9a2ad86904/src/google/adk/tools/skill_toolset.py): `list_skills` returns the XML above, `load_skill(skill_name)` returns the body, and `load_skill_resource` returns a single reference/asset/script with a path-prefix guard.

**Open issues/PRs to watch:**
- [#3611](https://github.com/google/adk-python/issues/3611) — Long-running tracking issue: support Claude skill feature.
- [#5405](https://github.com/google/adk-python/pull/5405) — `feat(skills): inject session state into SKILL.md via adk_inject_state` (runtime state interpolation).
- [#5398](https://github.com/google/adk-python/issues/5398) — Memory plugins: optional flag to promote recurring patterns into SKILL.md artifacts.

---

### deepagents (LangChain)

The middleware lives at [`libs/deepagents/deepagents/middleware/skills.py`](https://github.com/langchain-ai/deepagents/blob/a64ff430f14b76607dfb1d78234f928ed88a3af0/libs/deepagents/deepagents/middleware/skills.py) and is **backend-agnostic** — the middleware accepts a list of `sources` (paths in any backend: filesystem, in-memory state, remote) rather than scanning the filesystem directly.

The [in-memory record](https://github.com/langchain-ai/deepagents/blob/a64ff430f14b76607dfb1d78234f928ed88a3af0/libs/deepagents/deepagents/middleware/skills.py) is a `TypedDict` — minimal and JSON-friendly:

```python
class SkillMetadata(TypedDict):
    path: str
    name: str
    description: str
    license: str | None
    compatibility: str | None
    metadata: dict[str, str]
    allowed_tools: list[str]
    module: NotRequired[str | None]  # experimental: POSIX path to a JS/TS QuickJS REPL entrypoint
```

The catalog is **markdown bullets** injected into the system prompt by [`modify_request`](https://github.com/langchain-ai/deepagents/blob/a64ff430f14b76607dfb1d78234f928ed88a3af0/libs/deepagents/deepagents/middleware/skills.py) (formatter at [`_format_skills_list`](https://github.com/langchain-ai/deepagents/blob/a64ff430f14b76607dfb1d78234f928ed88a3af0/libs/deepagents/deepagents/middleware/skills.py)). A representative rendered prompt:

```markdown
## Skills System

You have access to a skills library that provides specialized capabilities and domain knowledge.

**User Skills**: `/skills/user/`
**Project Skills**: `/skills/project/` (higher priority)

**Available Skills:**

- **web-research**: Structured approach to conducting thorough web research on any topic
  -> Read `/skills/user/web-research/SKILL.md` for full instructions
- **code-review**: Systematic code review process following best practices and style guides
  -> Read `/skills/project/code-review/SKILL.md` for full instructions
```

The system prompt instructs the model to load the body via the standard `read_file` tool with `limit=1000`. There is no dedicated activation tool. Trust is enforced at file-read time by symlink-containment checks against `allowed_roots` in [`libs/cli/deepagents_cli/skills/load.py`](https://github.com/langchain-ai/deepagents/blob/a64ff430f14b76607dfb1d78234f928ed88a3af0/libs/cli/deepagents_cli/skills/load.py).

**Open issues/PRs to watch:**
- [#2446](https://github.com/langchain-ai/deepagents/issues/2446) — Skills not working: `read_file` for `SKILL.md` not read fully before execution (loader bug).
- [#1992](https://github.com/langchain-ai/deepagents/pull/1992) — `feat(sdk): add skill pack support to skills middleware` (experimental bundling/distribution).
- [#2081](https://github.com/langchain-ai/deepagents/issues/2081) — Prebuilt LangChain/LangSmith skills + install command.

---

### fast-agent

Parsing uses the `frontmatter` library; missing `name` or `description` is logged and the skill is skipped. The [record](https://github.com/evalstate/fast-agent/blob/502d32e266f3221d744977f38b7a9b4bc5b93947/src/fast_agent/skills/registry.py) is a frozen dataclass:

```python
@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str
    body: str
    path: Path  # Absolute path to SKILL.md
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] | None = None
    allowed_tools: list[str] | None = None
```

The model-facing catalog ([`format_skills_for_prompt`](https://github.com/evalstate/fast-agent/blob/502d32e266f3221d744977f38b7a9b4bc5b93947/src/fast_agent/skills/registry.py)) is XML with absolute paths and resolves the standard resource subdirectories alongside:

```xml
<available_skills>
<skill>
  <name>web-research</name>
  <description>Structured approach to research</description>
  <location>/abs/path/web-research/SKILL.md</location>
  <directory>/abs/path/web-research</directory>
  <scripts>/abs/path/web-research/scripts</scripts>
  <references>/abs/path/web-research/references</references>
</skill>
</available_skills>
```

The XML is preceded by an instructional preamble (same `format_skills_for_prompt` function):

```
Skills provide specialized capabilities and domain knowledge. Use a Skill if it seems relevant to the user's task, intent, or would increase your effectiveness.
To use a Skill, read its SKILL.md file from the specified location using the 'read_skill' tool.
Prefer that file-reading tool over shell commands when loading skill content or skill resources.
The <location> value is the absolute path to the skill's SKILL.md file, and <directory> is the resolved absolute path to the skill's root directory.
When present, <scripts>, <references>, and <assets> provide resolved absolute paths for standard skill resource directories.
When a skill references relative paths, resolve them against the skill's directory (the parent of SKILL.md) and use absolute paths in tool calls.
Only use Skills listed in <available_skills> below.
```

The [`read_skill` tool itself](https://github.com/evalstate/fast-agent/blob/502d32e266f3221d744977f38b7a9b4bc5b93947/src/fast_agent/tools/skill_reader.py) constructs an allowlist from each manifest's parent directory and rejects any path outside it — even absolute paths — so models can read SKILL.md and bundled resources but not the wider filesystem.

**Open issues/PRs to watch:** _none yet — add as found_.

---

### opencode

The [in-memory record](https://github.com/anomalyco/opencode/blob/ce89bcb8e238401ea8fee000dc54539057d47dc4/packages/opencode/src/skill/index.ts) is an Effect `Schema.Struct` with a Zod adapter exposed as a static — opencode is Effect-first internally but advertises a Zod view for callers that expect one:

```ts
export const Info = Schema.Struct({
  name: Schema.String,
  description: Schema.String,
  location: Schema.String,
  content: Schema.String,
}).pipe(withStatics((s) => ({ zod: zod(s) })))
```

[Failures during parse](https://github.com/anomalyco/opencode/blob/ce89bcb8e238401ea8fee000dc54539057d47dc4/packages/opencode/src/skill/index.ts) are published to the bus, not raised. Duplicate names log a warning but do not fail loading.

The model-facing catalog is **lazy** — [`Skill.fmt(list, {verbose: true})`](https://github.com/anomalyco/opencode/blob/ce89bcb8e238401ea8fee000dc54539057d47dc4/packages/opencode/src/skill/index.ts) builds the XML only when requested:

```text
<available_skills>
  <skill>
    <name>example-skill</name>
    <description>Example description</description>
    <location>file:///path/to/example-skill/SKILL.md</location>
  </skill>
</available_skills>
```

(Note the `file://` URI form via `pathToFileURL`, distinct from every other client's raw absolute path.)

Activation is a dedicated [`skill` tool](https://github.com/anomalyco/opencode/blob/ce89bcb8e238401ea8fee000dc54539057d47dc4/packages/opencode/src/tool/skill.ts). Each call:

1. Looks up `Info` by `params.name`.
2. Calls `ctx.ask({ permission: "skill", patterns: [params.name], always: [params.name] })` — explicit user consent each load.
3. Returns a wrapped block with sampled file list:

```text
<skill_content name="example-skill">
# Skill: example-skill

<body>

Base directory for this skill: file:///path/to/example-skill
Relative paths in this skill (e.g., scripts/, reference/) are relative to this base directory.
Note: file list is sampled.

<skill_files>
<file>/.../scripts/extract.py</file>
...
</skill_files>
</skill_content>
```

The [`available()` API](https://github.com/anomalyco/opencode/blob/ce89bcb8e238401ea8fee000dc54539057d47dc4/packages/opencode/src/skill/index.ts) additionally filters by per-agent permissions via `Permission.evaluate("skill", skill.name, agent.permission)` — the only surveyed implementation that scopes catalog visibility per agent.

**Open issues/PRs to watch:**
- [#25686](https://github.com/anomalyco/opencode/issues/25686) — Project-level skills missing from available-skills in REST API sessions.
- [#25570](https://github.com/anomalyco/opencode/issues/25570) — `[FEATURE]: Support Multiple Skills in a Single Prompt` (composition request).
- [#24852](https://github.com/anomalyco/opencode/pull/24852) — `feat: add skills.format config option for skill serialization format`.

---

### openclaw

Openclaw delegates the canonical `Skill` shape to the upstream `@mariozechner/pi-coding-agent` SDK. A [`compactHomePath`](https://github.com/openclaw/openclaw/blob/8a1e2202734476d79b462bbdf66e6291c26104d7/src/agents/skills/workspace.ts) step rewrites absolute paths to start with `~/` before injection to save ~5–6 tokens per skill.

The XML catalog is generated by [`formatSkillsForPrompt`](https://github.com/openclaw/openclaw/blob/8a1e2202734476d79b462bbdf66e6291c26104d7/src/agents/skills/skill-contract.ts):

```ts
const lines = [
  "\n\nThe following skills provide specialized instructions for specific tasks.",
  "Use the read tool to load a skill's file when the task matches its description.",
  "When a skill file references a relative path, resolve it against the skill directory ...",
  "",
  "<available_skills>",
];
for (const skill of skills) {
  lines.push("  <skill>");
  lines.push(`    <name>${escapeXml(skill.name)}</name>`);
  lines.push(`    <description>${escapeXml(skill.description)}</description>`);
  lines.push(`    <location>${escapeXml(skill.filePath)}</location>`);
  lines.push("  </skill>");
}
lines.push("</available_skills>");
```

The comment on this function — *"Keep this formatter's XML layout byte-for-byte aligned with the upstream Agent Skills formatter"* — is the strongest cross-implementation anchor in the survey.

There is no dedicated activation tool; the preamble tells the model to use the standard `read` tool. Visibility is governed by the [`SkillExposure`](https://github.com/openclaw/openclaw/blob/8a1e2202734476d79b462bbdf66e6291c26104d7/src/agents/skills/types.ts) record (`includeInAvailableSkillsPrompt`, `includeInRuntimeRegistry`, `userInvocable`); the per-skill `disableModelInvocation` invocation flag is what flips `includeInAvailableSkillsPrompt` off in [`workspace.ts`](https://github.com/openclaw/openclaw/blob/8a1e2202734476d79b462bbdf66e6291c26104d7/src/agents/skills/workspace.ts).

**Open issues/PRs to watch:**
- [#74594](https://github.com/openclaw/openclaw/issues/74594) — `RFC: Skill Capability Manifests v0 — make skill capabilities visible before enforcing them` (significant safety/permissions RFC).
- [#69475](https://github.com/openclaw/openclaw/issues/69475) — Skill SKILL.md description + size fixes per Anthropic skill spec (spec conformance).
- [#58142](https://github.com/openclaw/openclaw/pull/58142) — `feat(skills): add per-skill model routing via SKILL.md frontmatter`.

---

### goose (Block)

Implementation lives in [`crates/goose/src/skills/`](https://github.com/aaif-goose/goose/tree/45d8bf81d09d478ceedba8f6d1f0ad906123a981/crates/goose/src/skills). Built-in skills are Rust-embedded via `mod builtin`.

[Frontmatter](https://github.com/aaif-goose/goose/blob/45d8bf81d09d478ceedba8f6d1f0ad906123a981/crates/goose/src/skills/mod.rs) is intentionally lenient — `name` is `Option<String>`, `description` defaults to empty:

```rust
#[derive(Debug, Deserialize)]
pub struct SkillFrontmatter {
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub description: String,
}
```

The catalog presented to the model is a **bullet list** appended to the MCP server's `InitializeResult` instructions ([`client.rs`](https://github.com/aaif-goose/goose/blob/45d8bf81d09d478ceedba8f6d1f0ad906123a981/crates/goose/src/skills/client.rs)):

```rust
instructions.push_str(
    "\n\nYou have these skills at your disposal, when it is clear they can help you solve a problem or you are asked to use them:",
);
for skill in &skills {
    instructions.push_str(&format!("\n• {} - {}", skill.name, skill.description));
}
```

No XML, no path; the model only sees `name - description`. Activation is via a [`load_skill(name)` MCP tool](https://github.com/aaif-goose/goose/blob/45d8bf81d09d478ceedba8f6d1f0ad906123a981/crates/goose/src/skills/client.rs); passing `"skill-name/path"` returns a supporting file (canonicalized and verified to live under the skill directory). The tool reply re-walks `discover_skills` on every call.

**Open issues/PRs to watch:**
- [#8686](https://github.com/block/goose/issues/8686) — `commands to acp+ migration (goose 2.0) — Skills Management` (major migration tracking issue).
- [#8552](https://github.com/block/goose/issues/8552) — Summon detects project skills but not user-level skills on Windows (platform bug).
- [#7895](https://github.com/block/goose/issues/7895) — `[Feature Request] Delegate sub-agents should auto-inherit current skill context` (multi-agent skill inheritance).

---

### vscode (GitHub Copilot)

VS Code is the architectural outlier — there is no catalog *string* presented to the model. The implementation spans two repos: the **API contract** lives in [`microsoft/vscode`](https://github.com/microsoft/vscode) (proposed-API `.d.ts` files plus the `extHost` plumbing), while the **extension implementation** lives in [`microsoft/vscode-copilot-chat`](https://github.com/microsoft/vscode-copilot-chat) (the actively-maintained Copilot Chat source).

Skills surface through the editor's [chat API (`ChatSkill`)](https://github.com/microsoft/vscode/blob/530cb5de713aec2e96059e2f6cf41a95403cdb3d/src/vscode-dts/vscode.proposed.chatPromptFiles.d.ts):

```ts
export interface ChatSkill {
  readonly uri: Uri;             // .agent.md, .instructions.md, .prompt.md, or SKILL.md
  readonly name: string;
  readonly description?: string;
  readonly source: ChatResourceSource;
  readonly sessionTypes?: readonly string[];
  readonly extensionId?: string;
  readonly pluginUri?: Uri;
  readonly userInvocable?: boolean;
}
```

The [Claude session integration](https://github.com/microsoft/vscode-copilot-chat/blob/9e668cb12144c701cf0f2c6b3458c00fe3da20f1/src/extension/chatSessions/vscode-node/claudeCustomizationProvider.ts) exposes each skill as a `ChatSessionCustomizationItem` of type `ChatSessionCustomizationType.Skill`. The Copilot extension delegates the actual skill-loading semantics to the embedded session (Copilot CLI / Claude Code), rather than reformatting SKILL.md content into the conversation itself. The proposed-API plumbing in [`extHostChatAgents2.ts`](https://github.com/microsoft/vscode/blob/530cb5de713aec2e96059e2f6cf41a95403cdb3d/src/vs/workbench/api/common/extHostChatAgents2.ts) wires skills through the chat API; the editor — not the model — is the consumer.

**Open issues/PRs to watch:**
- [microsoft/vscode-copilot-chat#5101](https://github.com/microsoft/vscode-copilot-chat/issues/5101) — Add capability declaration fields (tools, mcp-servers, hooks, model) to SKILL.md frontmatter (directly relevant to skills-over-MCP).
- [microsoft/vscode#304721](https://github.com/microsoft/vscode/issues/304721) — Support contributing agent-skill folders with supporting files from extensions (extension-API surface).
- [microsoft/vscode#309463](https://github.com/microsoft/vscode/issues/309463) — Feature request: locale-aware loading for `chatSkills` contributions.

### cline

Implementation lives in [`src/core/context/instructions/user-instructions/skills.ts`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/context/instructions/user-instructions/skills.ts) (loader) and [`src/shared/skills.ts`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/shared/skills.ts) (types). The in-memory record is small:

```ts
export interface SkillMetadata {
  name: string
  description: string
  path: string
  source: "global" | "project"
}

export interface SkillContent extends SkillMetadata {
  instructions: string
}
```

Frontmatter parsing ([`frontmatter.ts`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/context/instructions/user-instructions/frontmatter.ts)) is fail-open — only `name` and `description` are extracted; missing or malformed frontmatter yields `{data: {}, body: markdown}` rather than skipping the skill. Discovery scans six directories ([`disk.ts:207-216`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/storage/disk.ts#L207-L216)): project `.clinerules/skills/`, `.cline/skills/`, `.claude/skills/`, `.agents/skills/`, then user-global `~/.cline/skills/` and `~/.agents/skills/`. The cross-tool `.claude/` and `.agents/` paths are honored as a portability convention.

The catalog rendered into the system prompt is **markdown bullets** ([`getSkillsSection`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/prompts/system-prompt/components/skills.ts)):

```
SKILLS

Available skills:
  - "skill-name": Skill description
  ...

To use a skill:
1. Match the user's request to a skill based on its description
2. Call use_skill with the skill_name parameter set to the exact skill name
3. Follow the instructions returned by the tool
```

Activation is via the [`use_skill` tool](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/prompts/system-prompt/tools/use_skill.ts) — a single `skill_name` parameter that loads the body from disk (or remote cache) on demand. The tool description explicitly tells the model to call `use_skill` *once* per skill, then follow the instructions directly without re-invocation.

**Enterprise remote skills.** [`RemoteConfigSchema`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/shared/remote-config/schema.ts#L228) defines `globalSkills: GlobalInstructionsFileSchema[]`, each carrying `{ alwaysEnabled: boolean, name: string, contents: string }` — the `contents` string is the full SKILL.md body with frontmatter. Remote skills are fetched through an authenticated API call ([`remote-config/fetch.ts`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/storage/remote-config/fetch.ts#L39-L90)), validated against frontmatter via [`parseRemoteSkillEntries`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/context/instructions/user-instructions/skills.ts#L38-L58) (which logs a warning if `entry.name` drifts from `frontmatter.name`), cached to disk, and merged into the same catalog as local skills by [`discoverSkills`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/context/instructions/user-instructions/skills.ts#L153-L184). Remote entries marked `alwaysEnabled: true` are enforced in [`applyRemoteConfig`](https://github.com/cline/cline/blob/86f463496cc814cf0055dbca4132b7f827425c53/src/core/storage/remote-config/utils.ts#L303-L384) — they bypass the user toggle UI and cannot be disabled. This admin-lockable enterprise primitive distinguishes Cline from every other surveyed harness.

**Open issues/PRs to watch:**
- [#10455](https://github.com/cline/cline/pull/10455) — `fix(skills): give actionable errors for invalid SKILL.md files` (loader error UX), paired with underlying issue [#10341](https://github.com/cline/cline/issues/10341).
- [#9281](https://github.com/cline/cline/pull/9281) — `feat: enable direct skill slash commands with skill-first precedence` (invocation routing).

---

### Roo-Code

Implementation lives in [`src/services/skills/SkillsManager.ts`](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/src/services/skills/SkillsManager.ts) with the type record at [`packages/types/src/skills.ts`](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/packages/types/src/skills.ts):

```ts
export interface SkillMetadata {
  name: string
  description: string
  path: string
  source: "global" | "project"
  mode?: string          // @deprecated: use modeSlugs
  modeSlugs?: string[]   // undefined/empty = any mode; array = mode-scoped
}
```

The `modeSlugs` array is the most distinctive Roo extension over the spec — it pins a skill to one or more Roo personas. Resolution at [`SkillsManager.ts:144-158`](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/src/services/skills/SkillsManager.ts#L144) follows a three-tier priority: frontmatter `modeSlugs` array > frontmatter `mode` string (legacy) > directory-derived mode (`skills-{mode}/`).

Discovery scans both unscoped and mode-scoped variants under four roots in priority order (project overrides global; `.roo/` overrides `.agents/` within the same scope) at [`SkillsManager.ts:567-622`](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/src/services/skills/SkillsManager.ts#L567): `~/.agents/skills*/`, `~/.roo/skills*/`, `<project>/.agents/skills*/`, `<project>/.roo/skills*/`. Symlinks are followed transparently via `fs.realpath()`. A `vscode.createFileSystemWatcher` keeps the in-memory `Map<string, SkillMetadata>` (keyed by `{source}:{primaryMode}:{name}`) hot-reloaded.

The catalog ([`getSkillsSection`](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/src/core/prompts/sections/skills.ts)) is XML and pairs the listing with a **mandatory three-step evaluation directive**: evaluate user request against all skill descriptions; if a skill matches, call the `skill` tool; otherwise proceed normally. The preamble explicitly enforces L3 progressive disclosure — *"Do NOT load every skill up front"* and *"Avoid reading multiple linked files unless required"* (inline at [`skills.ts:82-90`](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/src/core/prompts/sections/skills.ts#L82)):

```xml
<available_skills>
  <skill>
    <name>skill-name</name>
    <description>When to use this skill</description>
    <location>/abs/path/SKILL.md</location>
  </skill>
</available_skills>
```

Activation is the [`skill` tool](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/src/core/prompts/tools/native-tools/skill.ts) with both `skill` (name) and `args` (optional context string) parameters. Execution at [`SkillTool.ts:71`](https://github.com/RooCodeInc/Roo-Code/blob/ad256349058d3f84fd97517aabce4a119a234bbf/src/core/tools/SkillTool.ts#L71) routes through `askApproval("tool", …)` — a per-invocation user-approval gate. There is no per-tool `allowed-tools` enforcement; the trust boundary is the approval flow plus the discovery directory restriction.

A previous bundled-skills mechanism (`built-in-skills.ts`, `generate-built-in-skills.ts`, and bundled `create-mcp-server` / `create-mode` SKILL.md files, ~700 lines total) was removed wholesale in early 2026; only file-based discovery remains.

**Open issues/PRs to watch:**
- [#12198](https://github.com/RooCodeInc/Roo-Code/pull/12198) — `fix: surface skill loading errors to users instead of silently dropping them`.
- [#12194](https://github.com/RooCodeInc/Roo-Code/issues/12194) — `[BUG] Only 5 of 30 manually copied skills appear in Settings → Skills` (discovery cap).
- [#11368](https://github.com/RooCodeInc/Roo-Code/issues/11368) — `[ENHANCEMENT] Support .agents/skills folder` (cross-client convention alignment).

---

### crewAI

CrewAI implements skills as **filesystem-discovered, eagerly prompt-injected** content. Validation matches the spec strictly via [`SkillFrontmatter`](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/lib/crewai/src/crewai/skills/models.py#L43-L92) (Pydantic, regex-validated kebab-case `name` ≤64 chars, `description` ≤1024 chars; optional `license`, `compatibility`, `metadata`, `allowed-tools`). The skill record carries a three-level disclosure enum:

```python
class DisclosureLevel(IntEnum):
    METADATA = 1      # frontmatter only
    INSTRUCTIONS = 2  # full SKILL.md body
    RESOURCES = 3     # plus references/scripts/assets catalog
```

Discovery and activation flow is opinionated: [`Crew.setup_agents`](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/lib/crewai/src/crewai/crews/utils.py#L58-L79) calls `_resolve_crew_skills` once at agent construction time, which discovers all crew-level skill paths and **auto-activates** every discovered skill to `INSTRUCTIONS` level. [`Agent.set_skills`](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/lib/crewai/src/crewai/agent/core.py#L405-L472) merges agent-level paths the same way and emits `SkillDiscoveryStartedEvent`, `SkillLoadedEvent`, and `SkillActivatedEvent` to the `crewai_event_bus` for observability.

The model never sees an `<available_skills>` catalog and there is no `activate_skill` or `load_skill` tool. Instead, [`Agent._prepare_task_prompt`](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/lib/crewai/src/crewai/agent/core.py#L533-L547) calls [`append_skill_context(self, task_prompt)`](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/lib/crewai/src/crewai/agent/utils.py#L216-L237), which mutates the task prompt string by appending each activated skill's body:

```python
task_prompt += "\n\n" + "\n\n".join(skill_sections)
```

The same call site is repeated at [`_setup_and_validate_tools` (line 1487)](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/lib/crewai/src/crewai/agent/core.py#L1487) so messages flowing into the LLM also carry the appended context. There is no model-driven progressive disclosure in the standard Crew flow; the lower-level `discover_skills` / `activate_skill` API exists in [`loader.py`](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/lib/crewai/src/crewai/skills/loader.py) for callers that want explicit two-stage loading, but that path is not what `Crew(agents=..., skills=...)` exercises.

`allowed-tools` is parsed by a `@model_validator` and stored on the dataclass, but a codebase-wide search for references to the field outside `models.py` finds **none** — it is purely metadata, as documented in [`docs/en/concepts/skills.mdx`](https://github.com/crewAIInc/crewAI/blob/c9100cb51d357f6e3ba7d9969a000571f051ca64/docs/en/concepts/skills.mdx#L296).

**Open issues/PRs to watch:** _none directly relevant_. The open issues containing "skill" in the crewAI repo (e.g., PR [#5615](https://github.com/crewAIInc/crewAI/pull/5615) on `allow A2A delegation by skill ID as well as endpoint URL`, issue [#3897](https://github.com/crewAIInc/crewAI/issues/3897)) refer to A2A AgentCard "skill" objects, not the SKILL.md format. Re-search at next pass with stricter terms (`SKILL.md`, `crewai/skills`, `discover_skills`).

---

### mastra

Implementation lives across `packages/core/src/workspace/skills/`. The model-facing layer is [`SkillsProcessor.formatAvailableSkills`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/processors/processors/skills.ts#L122) (XML, JSON, or markdown — XML default, sorted by name for cache stability):

```xml
<available_skills>
  <skill>
    <name>brand-guidelines</name>
    <description>Guidance on brand colors and typography</description>
    <location>skills/brand-guidelines/SKILL.md</location>
    <source>local</source>
  </skill>
</available_skills>
```

Discovery is wired via the `Workspace` constructor, accepting either static paths, glob patterns (`skills/**`), or a context-driven function:

```ts
new Workspace({
  filesystem: new LocalFilesystem({ basePath: './data' }),
  skills: (ctx) => ctx.requestContext?.get('userTier') === 'premium'
    ? ['skills/basic', 'skills/premium']
    : ['skills/basic'],
})
```

Frontmatter is parsed by `gray-matter` ([`publish.ts:220`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/workspace/skills/publish.ts#L220)) and validated by [`schemas.ts:263`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/workspace/skills/schemas.ts#L263) — kebab-case `name` ≤64 chars, `description` ≤1024 chars, soft warnings at 500 lines / 5000 tokens.

Activation is split across **three tools** ([`tools.ts`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/workspace/skills/tools.ts)):

- `skill(name)` — load the full body and lists of references/scripts/assets;
- `skill_search(query, topK?)` — BM25 by default, with `'vector'` and `'hybrid'` (with `vectorWeight`) modes;
- `skill_read(name, path, lineRange?)` — read a single file under `references/`/`scripts/`/`assets/` with symlink resolution.

A system instruction printed alongside the catalog reminds the model: *"Do not call skill names directly as tool names. To use a skill, call the `skill` tool with the skill name as the 'name' parameter."*

**Versioning architecture.** A `'live'`/`'latest'`/pinned-`versionId` resolution model layers on top of file discovery. The storage layer at [`packages/core/src/storage/types.ts:1826`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/storage/types.ts#L1826) splits skills into two records: `StorageSkillType` (id, status `'draft'|'published'|'archived'`, `activeVersionId`) and `StorageSkillSnapshotType` (full content + `SkillVersionTree` mapping relative paths to `SkillVersionTreeEntry { blobHash, size, mimeType, encoding }`). Blob bodies live in a content-addressable [`BlobStore`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/storage/domains/blobs/base.ts) (LibSQL/Postgres/MongoDB/S3/GCS/Azure backends). [`VersionedSkillSource`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/workspace/skills/versioned-skill-source.ts) reads through the tree + blob store with no filesystem; `CompositeVersionedSkillSource` mounts multiple skill versions as a virtual tree with optional fallback to live FS for drafts. [`publishSkillFromSource`](https://github.com/mastra-ai/mastra/blob/560dd4f521246b988e1244e7691230ad61bc1501/packages/core/src/workspace/skills/publish.ts#L260) walks a directory, hashes everything, deduplicates blobs, and snapshots into the `skill_versions` table.

**Open issues/PRs to watch:**
- [#15457](https://github.com/mastra-ai/mastra/issues/15457) — Skills + S3 filesystem latency: skills are SUPER slow (~1 minute) (perf blocker for the BlobStore-backed flow).
- [#15908](https://github.com/mastra-ai/mastra/issues/15908) — DX: prevent duplicate skill context when SkillSearchProcessor-loaded skills also read via workspace file tools.

---

### agent-framework (Microsoft)

Implementation spans Python and .NET, with a notable asymmetry: the .NET surface uses a richer decorator-based composition model (per ADR-0021), while the Python surface on `main` is deliberately flat. The Python module ([`python/packages/core/agent_framework/_skills.py`](https://github.com/microsoft/agent-framework/blob/bc428746909966ae8dbe08d8ffa9f2cf1132d771/python/packages/core/agent_framework/_skills.py)) consists of:

- `Skill` — bundles instructions, name, description, optional `path`, and mutable lists of `SkillResource`/`SkillScript`. Decorators `@skill.resource` and `@skill.script` allow runtime attachment.
- `SkillResource` — name, optional description, either `content` (static) or `function` (sync/async, with `**kwargs` introspection cached up front).
- `SkillScript` — code-defined (`function`) or file-based (`path`); code-based scripts auto-generate a JSON schema from the callable signature.
- `SkillsProvider` — a `ContextProvider` that takes `skill_paths` and/or pre-built `skills`, advertises XML metadata in the system prompt, and registers `load_skill`, `read_skill_resource`, and `run_skill_script` tools (the last only if any skill has scripts).
- `SkillScriptRunner` — a Protocol; pluggable execution strategies (subprocess, cloud function, callback).

There is no `SkillsSource`, `InlineSkill`, `FileSkill`, `_AggregatingSkillsSource`, or composable source decorator on `main` today. Caching and filtering are built directly into `SkillsProvider`. A multi-source rewrite that would mirror the .NET decorator pattern is in flight in [open PR #5584](https://github.com/microsoft/agent-framework/pull/5584) (*"Python: [Breaking] Restructure agent skills to use multi-source architecture"*) but not yet merged.

The .NET surface at [`dotnet/src/Microsoft.Agents.AI/Skills/`](https://github.com/microsoft/agent-framework/tree/bc428746909966ae8dbe08d8ffa9f2cf1132d771/dotnet/src/Microsoft.Agents.AI/Skills) **does** have the decorator-based composition pattern: `AgentSkillsProvider`, `AgentFileSkillsSource`, `AgentInMemorySkillsSource`, plus `FilteringAgentSkillsSource`, `CachingAgentSkillsSource`, `DeduplicatingAgentSkillsSource`, and `AggregatingAgentSkillsSource`. [ADR-0021 `docs/decisions/0021-agent-skills-design.md`](https://github.com/microsoft/agent-framework/blob/bc428746909966ae8dbe08d8ffa9f2cf1132d771/docs/decisions/0021-agent-skills-design.md) is the source for that pattern; it describes file/inline/class-based skills as composable sources with explicit filtering and caching as decorators.

Discovery in both languages reads `SKILL.md` files up to two directory levels deep from each configured path; standard subdirectories `references/`, `assets/`, `scripts/` are auto-discovered with configurable extension filters. Frontmatter validation matches the spec (`name` ≤64 chars kebab-case, `description` ≤1024 chars, plus optional `license`, `compatibility`, `allowed-tools`, `metadata`).

The catalog rendered into the system prompt is XML metadata only (~100 tokens per skill). On `load_skill(name)`, file-based skills return raw SKILL.md body (frontmatter stripped); code-defined skills return a richer XML envelope including `<resources>` and `<scripts>` children. `run_skill_script` is **conditionally registered** — the system prompt only includes script-runner instructions when at least one skill in the active provider has scripts, avoiding cluttering prompts that don't need it.

**Open issues/PRs to watch:**
- [#5584](https://github.com/microsoft/agent-framework/pull/5584) — `Python: [Breaking] Restructure agent skills to use multi-source architecture` (still open; would bring Python in line with the .NET decorator pattern from ADR-0021).
- [#5571](https://github.com/microsoft/agent-framework/issues/5571) — `RFC: Treat apm.yml as package.json for skills — load SKILL.md as agent entrypoint` (packaging proposal).
- [#5610](https://github.com/microsoft/agent-framework/pull/5610) — `.NET: Fix YAML block scalar parsing for file skills` (multiline frontmatter fix paired with bug #5586).

### hermes-agent (Nous Research)

Hermes Agent is a Python CLI / agent library with the most extended skills surface in the survey set. The frontmatter parser at [`agent/skill_utils.py:parse_frontmatter`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/agent/skill_utils.py#L52) accepts the standard `name`/`description` plus a wide range of optional fields documented in [`tools/skills_tool.py`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/tools/skills_tool.py#L28):

```yaml
---
name: skill-name
description: Brief description
platforms: [macos]                # OS filter — skill hidden if mismatch
required_environment_variables:   # Triggers runtime secret prompt
  - name: API_KEY
    prompt: "API key for…"
    optional: false
setup:
  collect_secrets:                # Pluggable callback — gateway prompts user
    - env_var: API_KEY
      provider_url: https://…
metadata:
  hermes:
    tags: [fine-tuning, llm]
    related_skills: [peft, lora]
requires_tools: [bash, edit]      # Catalog hides skill if tool set lacks these
fallback_for_tools: [...]
---
```

Discovery scans `~/.hermes/skills/` (auto-created and seeded on first run), each entry in `config.yaml`'s `skills.external_dirs` (with `~`/`${VAR}` expansion and dedupe), and a plugin namespace where `plugin:skill-name` resolves through the lazy plugin manager. Platform filtering eliminates skills incompatible with the current OS before any later processing.

The catalog itself is markdown grouped by category, built by [`build_skills_system_prompt`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/agent/prompt_builder.py#L712) and backed by a **two-layer cache**: an in-process LRU keyed by `(skills_dir, external_dirs, available_tools, available_toolsets, platform_hint, disabled_skills)` plus a disk snapshot at `~/.hermes/.skills_prompt_snapshot.json` with an mtime/size manifest of every SKILL.md and DESCRIPTION.md file. Category-level `DESCRIPTION.md` files inject a per-category summary so readers don't have to inspect every skill's frontmatter:

```
## Skills (mandatory)
Before replying, scan the skills below. If a skill matches or is even partially relevant
to your task, you MUST load it with skill_view(name) and follow its instructions.

  mlops: Fine-tuning and LLM training utilities
    - axolotl: Fast, efficient fine-tuning framework
    - peft: Parameter-efficient fine-tuning library
  general:
    - web-research: Structured approach to web research
```

Activation has three entry points, all of which run skill content through a configurable preprocessor (`agent/skill_preprocessing.py`) that expands `${HERMES_SKILL_DIR}`, `${HERMES_SESSION_ID}`, and inline `` !`shell command` `` snippets when the corresponding `skills.template_vars` / `skills.inline_shell` flags are enabled:

1. **Slash commands** — `/skill-name` is normalised by [`build_skill_invocation_message`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/agent/skill_commands.py#L406) and the full body is prepended with an `[IMPORTANT: The user has invoked the "skill_name" skill …]` banner.
2. **`--skill` CLI preload** — [`build_preloaded_skills_prompt`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/agent/skill_commands.py#L453) inlines one or more skills into the initial system prompt for the whole session.
3. **`skill_view` tool** — [`tools/skills_tool.py:skill_view`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/tools/skills_tool.py#L849) accepts `name` (or `category/name`) and an optional `file_path` for bundled references/templates/scripts. Returns JSON with `{ success, name, content, description, linked_files, readiness_status }`; the `[Skill directory: …]` block tells the agent where to find supporting files without a second call.

Trust gating is layered. Disabled skills are filtered globally via `skills.disabled` and per-platform via `skills.platform_disabled.{platform}`. Path containment logs a security warning if a skill resolves outside the configured roots. Most distinctively, **load-time prompt-injection scanning** runs a `_INJECTION_PATTERNS` list in [`tools/skills_tool.py`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/tools/skills_tool.py#L133) against every skill body and flags matches of phrases like `ignore previous instructions`, `system prompt:`, or `<system>` tags. Runtime secret prompting (`setup.collect_secrets`, `required_environment_variables`) is delegated to a callback the gateway surface implements; `skill_view` returns `{ readiness_status: "setup_needed", setup_note: "…" }` when prerequisites are missing so the agent can surface the gap to the user. `allowed-tools` is parsed but stored as metadata only — there's no per-skill tool allowlist enforced at the model boundary.

Beyond catalog/activation, hermes-agent ships a **curator lifecycle process** ([`agent/curator.py`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/agent/curator.py)) that indexes, summarises, and auto-archives inactive skills using the usage tracker at [`tools/skill_usage.py`](https://github.com/NousResearch/hermes-agent/blob/363cc936746c3f2964427b635f80f57df528da54/tools/skill_usage.py), and a `skill_manage` tool that lets the agent patch existing skills, create new ones, and edit supporting files mid-session — closing the authoring loop inside the same agent that consumes them.

**Open issues/PRs to watch:**
- [#18659](https://github.com/NousResearch/hermes-agent/issues/18659) — `scan_skill_commands` unconditionally clears `_skill_commands` before try block; silent skill loss on scan failure (data-loss bug).
- [#17583](https://github.com/NousResearch/hermes-agent/issues/17583) — Skills: user-locked vs self-improving tiers + user-feedback-driven skill updates (governance/lifecycle RFC).
- [#19254](https://github.com/NousResearch/hermes-agent/pull/19254) — `docs(skills): explain restoring bundled skills`.

## Cross-cutting observations

1. **Catalog rendering splits along ecosystem lines.** XML `<available_skills>` is dominant in adk-python, gemini-cli, fast-agent, opencode, and openclaw — openclaw's source comment ("byte-for-byte aligned with the upstream Agent Skills formatter") explicitly anchors to a shared format. Markdown bullets show up in deepagents and goose. Codex uses a hybrid markdown structure with a budget-aware truncation pass. Gemini-cli notably belt-and-suspenders this by *also* embedding the skill list in the `activate_skill` tool description and enum-constraining the schema, so the model sees the catalog three times.

2. **Activation splits three ways.** *Standard file-read* (deepagents via `read_file`) keeps the harness simplest. *Dedicated tool* (gemini-cli `activate_skill`, adk-python `load_skill`, fast-agent `read_skill`, opencode `skill`, goose `load_skill`) is the most common pattern and is where confirmation/permission UX lives. *Implicit mention-based* (codex `$SkillName`) is unique to codex. Most strip frontmatter on activation; codex retains it.

3. **Trust models diverge meaningfully.** Per-skill confirmation each load (opencode `ctx.ask`, gemini-cli's `getConfirmationDetails`), workspace trust gate (gemini-cli, codex repo scope), allowlist of skill directories enforced at the tool boundary (fast-agent, deepagents symlink containment), or none visible (goose). For skills-over-MCP this matters — any equivalent over the wire needs an equally explicit story.

4. **vscode reframes the problem.** Because skills surface through `ChatSessionCustomizationProvider` and not as text in the conversation, VS Code's role is closer to a *registry* than a *prompt-builder*. This is worth flagging in skills-over-MCP discussions: a host can legitimately treat installed SKILL.md directories as configuration metadata for an embedded agent rather than as system-prompt content.

5. **Codex's policy model is unique.** `SkillPolicy.allow_implicit_invocation`, `SkillInterface.icon_*`, and `SkillDependencies.tools` (with transport/command/url) are not present in any other client surveyed — they hint at where the spec could grow if more clients adopt cross-skill orchestration patterns.

6. **Enterprise / remote skill distribution emerges as a new dimension.** Cline's `globalSkills` (admin-locked, fetched via authenticated API and merged into the same catalog as local skills) and Mastra's `BlobStore`-backed versioned skills (content-addressable, draft→publish, multi-backend storage) both address the org-distribution problem the spec leaves to implementers. Cline's `alwaysEnabled: true` flag bypasses the user toggle UI entirely — a lockable enterprise primitive worth flagging in skills-over-MCP discussions.

7. **Frontmatter extension is now visibly fragmented.** Codex's `SkillPolicy.allow_implicit_invocation`, Roo Code's `modeSlugs` array, and Mastra's `metadata`/`license`/`compatibility` plus its versioning identifiers are all spec-extending fields used today by at least one harness. Anthropic's reference contract (`name`, `description`, `allowed-tools`, `disable-model-invocation`) is a starting set; the working implementations are layering vendor-specific fields on top with no portability story.

8. **CrewAI's eager-injection model breaks the progressive-disclosure assumption.** Of the fifteen surveyed clients, only CrewAI's standard `Crew(agents, skills=...)` flow eagerly inlines every activated skill body into the task prompt at agent-init time, with no model-driven activation tool. This is a meaningful divergence from the L1→L2→L3 disclosure pattern: a host can ship "skills support" while skipping progressive disclosure entirely. CrewAI's lower-level `discover_skills` / `activate_skill` API does support staged loading, but standard Crew use does not exercise it.

9. **Skill-content trust is mostly implicit.** Of the fifteen clients, only hermes-agent runs **load-time prompt-injection pattern scanning** (`_INJECTION_PATTERNS` in `tools/skills_tool.py` flags phrases like `ignore previous instructions`, `system prompt:`, `<system>` on every skill body). Other harnesses treat the skills directory as a trusted root and don't inspect content for adversarial patterns — a meaningful gap if skills can come from third-party registries (which several hosts now support).

10. **Skill content can also be dynamic.** Hermes Agent and Codex both run preprocessing on skill bodies before injection: Codex retains frontmatter and applies its own templating; hermes-agent expands `${HERMES_SKILL_DIR}`/`${HERMES_SESSION_ID}` template variables and inline `` !`shell` `` snippets gated behind config flags. Most other clients treat SKILL.md as static markdown and pass the body through unmodified — an implicit assumption worth flagging for skills-over-MCP, where the wire format may need to declare whether content is templated.

11. **The author/consumer loop is rare.** Most clients only consume skills; hermes-agent's `skill_manage` tool plus its background curator process let the agent edit, archive, and create skills mid-session. Codex's hot-reload via `skills_watcher` and Roo Code's `vscode.createFileSystemWatcher` are weaker forms of the same pattern — they pick up out-of-band edits but don't author them. Closing this loop inside the agent that consumes skills changes how skill authoring is expected to feel: less like editing config files, more like a continuous teaching surface.

## TODO (next pass)

- **Re-pin commits** for all rows. The original survey was taken in early 2026 and the snapshot table should be re-anchored before publication.
- **Refresh the issues/PRs column.** The "Open issues/PRs to watch" entries were collected on 2026-05-04 via `gh search` plus targeted WebFetch. Re-search each repo at the next pass with these terms: `is:open skill in:title`, `is:open SKILL.md`, `is:open skills/ in:body`. Drop entries that have closed; promote new high-signal ones.
- **Watch the convergence signals.** Two issues, in particular, are worth tracking because they bear directly on cross-client portability:
  - [microsoft/vscode-copilot-chat#5101](https://github.com/microsoft/vscode-copilot-chat/issues/5101) — proposes capability-declaration fields (`tools`, `mcp-servers`, `hooks`, `model`) in SKILL.md frontmatter. Directly relevant to the skills-over-MCP design and to observation 7 (frontmatter fragmentation).
  - [microsoft/agent-framework#5571](https://github.com/microsoft/agent-framework/issues/5571) — proposes treating `apm.yml` as `package.json` for skills. Touches the same packaging-and-distribution question Cline (`globalSkills`) and Mastra (versioned `BlobStore`) address differently.
- **Cross-link with the resources research.** A reader investigating "how does this client surface skills?" almost always also wants "how does it surface MCP resources?" — link `clients-skills-research.md` and `client-resources-research.md` from each other so the pivot is one click.
