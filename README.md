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
- **Commands** — invokable prompts (slash commands) that drive a specific workflow
  end to end, orchestrating agents and skills. Each is a Markdown file with
  frontmatter (`description`, `argument-hint`) and takes arguments via `$ARGUMENTS`.

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
├── agents/     # One Markdown file per agent (spawnable definition)
├── skills/     # One directory per skill (Agent Skills format)
├── commands/   # One Markdown file per command (invokable workflow)
├── docs/       # Human-facing documentation
└── README.md
```

## Installation

This repository is designed to be deployed as the **`.agents/`** directory of a target
project — clone or symlink it there:

```bash
git clone git@github.com:lfantone/ai.git <project>/.agents
# or symlink a single local clone:
ln -s ~/Workspace/ai <project>/.agents
```

That gives the project `.agents/agents/`, `.agents/commands/`, `.agents/skills/`, and a
runtime `.agents/cache/` (see [Code review › Caching](./docs/code-review.md#caching)).
Add `.agents/` to the target project's `.gitignore`.

> Symlinking one clone into several projects makes them **share `.agents/cache/`**, and the
> repo-level caches (`repo-profile.md`, `security-profile.md`) are project-specific — clone
> per project if you don't want them to collide.

## Conventions

- Each agent and skill is self-contained in its own directory.
- Skills conform to the Agent Skills format; keep `name` and `description` accurate
  since they are what agents use to decide when a skill is relevant.

See [AGENTS.md](./AGENTS.md) for how to author skills and agents, including
token-efficiency practices.

## Documentation

- [Code review](./docs/code-review.md) — the `/review-orchestrator` command.
- [Implementation planning](./docs/plan.md) — the `/plan-orchestrator` command.

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
