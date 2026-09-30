# AI

A personal collection of AI agents and skills.

This repository is a workspace for building, iterating on, and cataloging reusable
AI components — autonomous **agents** that carry out multi-step tasks, and **skills**
that package focused capabilities any agent can load on demand.

## What lives here

- **Agents** — self-contained agents with their own prompts, tools, and configuration.
  Each agent solves a particular class of task end to end.
- **Skills** — portable capabilities authored in the open
  [Agent Skills](https://agentskills.io/home) format, so they work across any
  skills-compatible agent (Claude Code, Cursor, Gemini CLI, OpenCode, Goose, and
  many others) rather than being tied to a single tool.
- **Commands** — the prompts you'd otherwise retype (slash commands). The main session
  follows them itself, spawning an agent only where isolation pays. Each is a Markdown
  file with frontmatter (`description`, `argument-hint`) and takes `$ARGUMENTS`.
- **Instructions** — `instructions/AGENTS.md`, a short block of personal working defaults
  that a global install keeps in your harness's user-level instructions file.

## Skill format

Skills follow the [Agent Skills specification](https://agentskills.io/specification).
A skill is a folder containing a `SKILL.md` file with YAML frontmatter (`name` and
`description` are required) plus instructions, and may bundle scripts, references,
and assets:

```
skills/
└── my-skill/
    ├── SKILL.md        # Required: name + description frontmatter, then instructions
    ├── scripts/        # Optional: executable code
    ├── references/     # Optional: documentation the skill can load
    └── assets/         # Optional: templates and other resources
```

Agents load skills through **progressive disclosure**: at startup they read only each
skill's `name` and `description`, pull the full `SKILL.md` into context when a task
matches, and load bundled files only as needed.

## Repository layout

> The structure below is the intended organization; directories are added as
> agents and skills are built.

```
AI/
├── agents/     # One Markdown file per agent (spawnable definition) — canonical
├── skills/     # One directory per skill (Agent Skills format)
├── commands/   # One Markdown file per command (invokable workflow) — canonical
├── instructions/ # Global working-defaults block (installed on --global)
├── docs/       # Human-facing documentation
├── scripts/    # install.mjs (harness installer; --names norse for the non-Pokémon fans)
└── README.md
```

`agents/` and `commands/` are the **canonical** definitions. Nothing generated is
committed: `scripts/install.mjs` builds the config for your harness at install time, so
drift between canonical and installed is impossible by construction. Skills need no
translation — the Agent Skills format is consumed natively by compliant harnesses.

## Installation

One installer covers every harness, project-wise or globally, with either naming set:

```bash
git clone git@github.com:lfantone/ai.git && cd ai

./scripts/install.mjs --harness claude   --project ~/work/my-app   # → .claude/
./scripts/install.mjs --harness opencode --project ~/work/my-app   # → .opencode/
./scripts/install.mjs --harness github   --project ~/work/my-app   # → .github/
./scripts/install.mjs --harness codex    --project ~/work/my-app   # → .codex/ + .agents/

./scripts/install.mjs --harness claude --global                    # → ~/.claude/
./scripts/install.mjs --harness opencode --global --names norse    # Norse-named roster
./scripts/install.mjs --harness codex --global                     # → ~/.codex/ + ~/.agents/
./scripts/install.mjs --harness opencode --project . --provider openai

./scripts/install.mjs --harness github --project . --dry-run       # preview only
```

The installer **builds at install time** from the canonical catalog: per-harness
frontmatter (models, permissions/tools, colors, reasoning effort), commands adapted to
each harness's invocation style (OpenCode commands, Copilot/Codex command-skills, Claude
commands), and skills copied as-is. A `--global` install also writes the
`instructions/AGENTS.md` block between `<!-- ai-catalog-begin -->` / `<!-- ai-catalog-end -->`
markers in the harness's user-level instructions file, leaving the rest of that file alone.
Every install also removes what earlier catalog versions left behind in its target dirs:
entries it no longer ships (including installs that predate the manifest, under either naming
set) and, on project installs, the old orchestrators' `cache/` artifacts. Other tools' files
stay. Preview with `--dry-run` — stale entries print as `would remove stale …`.
Re-run it after pulling catalog updates. Workflow state lives in each project's
`.agents/work/` (see [the workflow](./docs/workflow.md#state)).

OpenCode defaults to GitHub Copilot models. Pass `--provider claude` or
`--provider openai` to use direct Anthropic or OpenAI/Codex models. Claude Code, GitHub
Copilot, and Codex use their native model configuration and do not need provider selection.

Harness details: [OpenCode](./docs/opencode.md) · [Copilot](./docs/copilot.md) · [Codex](./docs/codex.md).

## Conventions

- Each agent and skill is self-contained in its own directory.
- Skills conform to the Agent Skills format; keep `name` and `description` accurate
  since they are what agents use to decide when a skill is relevant.

See [AGENTS.md](./AGENTS.md) for how to author skills and agents, including
token-efficiency practices.

## Documentation

- [**The workflow**](./docs/workflow.md) — `/ticket` → `/verify` → `/ship` →
  `/pr-review` ⇄ `/pr-feedback`, and why there is no orchestrator. **Start here.**
- [OpenCode setup](./docs/opencode.md) — the generated `.opencode/` config.
- [Copilot setup](./docs/copilot.md) — the generated `.github/agents/` config.
- [Codex setup](./docs/codex.md) — the generated `.codex/agents/` and `.agents/skills/` config.

## Development

Install dependencies once after cloning. This also activates the git hooks
(via the `prepare` script, which sets `core.hooksPath` to `.githooks`):

```bash
npm install
```

Markdown is formatted with [Prettier](https://prettier.io):

```bash
npm run format         # format all Markdown in place
npm run format:check   # check formatting without writing
```

A **pre-push hook** (`.githooks/pre-push`) formats tracked Markdown before every
push. If formatting produces changes, the push is aborted so you can review and
commit them — this keeps pushed Markdown consistently formatted.

## License

Released under the [MIT License](./LICENSE).
