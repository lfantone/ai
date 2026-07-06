# OpenCode setup

The repo ships **`.opencode/`** — the catalog translated to
[OpenCode](https://opencode.ai)'s format, generated from the canonical `agents/` and
`commands/` by a build script. The canonical files stay the source of truth; never edit
`.opencode/` by hand.

## What's generated

- **`.opencode/agents/*.md`** — the 16 agents with OpenCode frontmatter: `mode: subagent`,
  a GitHub Copilot `model`, and a `permission` object derived from each agent's canonical
  `tools` list (least-privilege: `edit: allow` only for executors and cache-writers).
- **`.opencode/commands/*.md`** — the 4 orchestrators (`$ARGUMENTS` works as-is);
  harness terms are mapped (`Agent tool` → `task tool`, `TaskCreate`/`TaskUpdate` →
  `todowrite`).
- **`.opencode/skills`** — a symlink: OpenCode reads the agentskills `SKILL.md` format
  natively, so the skills need no conversion. (It also discovers `.agents/skills/`
  directly — see deployment below.)

## Model mapping

Catalog tiers map to GitHub Copilot model ids (edit `map_model` in the script to
retarget):

| Tier   | OpenCode model                    |
| ------ | --------------------------------- |
| haiku  | `github-copilot/claude-haiku-4.5` |
| sonnet | `github-copilot/claude-sonnet-5`  |
| opus   | `github-copilot/claude-opus-4.8`  |

Deterministic verifiers/executors (Machop, Machoke, Porygon, Magneton, Magnemite) are
pinned to `temperature: 0.1`.

## Regenerating

After any change to the canonical `agents/` or `commands/` (e.g. a rebase from `main`):

```bash
./scripts/build-opencode.sh
```

You can't forget: the **pre-push hook** runs the translator automatically and aborts the
push if the regenerated `.opencode/` differs from what's committed — the canonical
catalog and the generated config can never drift apart on the remote.

## Deployment

Do NOT symlink the whole `.opencode/` directory — OpenCode writes its own things into it
(plugins, your project-local agents), and a directory symlink doesn't merge: everything
would land inside the catalog clone instead. Link **per file** so the catalog's agents
and commands coexist with whatever else lives there:

- **Repo as project tooling (recommended):** clone the catalog to `<project>/.agents`
  (the standard install), then:
  ```bash
  <project>/.agents/scripts/deploy-opencode.sh <project>
  ```
  This creates a real `<project>/.opencode/` (if missing) and symlinks the 16 agents +
  4 commands into it, file by file. Content updates flow through the links on
  `git pull`; re-run the script only when files are added or removed. Skills need
  nothing — OpenCode natively discovers `<project>/.agents/skills/`.
- **Direct:** copy `.opencode/agents` and `.opencode/commands` into the project's
  `.opencode/` (no auto-updates; skills still resolve via `.agents/skills/`).

Verify with `opencode` in the project: the agents appear in the `@` menu, the commands
under `/`.

## Notes

- MCP-dependent agents (Ditto → Chrome DevTools, Slowpoke → Jira) need those MCP servers
  configured in your `opencode.json`; their generated permissions deny `bash`/`edit`, so
  they can only act through their MCPs.
- Copilot model ids drift as GitHub adds models — `opencode models | grep copilot` shows
  what your install offers.
