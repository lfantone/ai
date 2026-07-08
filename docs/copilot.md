# GitHub Copilot setup

Install the catalog for GitHub Copilot (**CLI**, **VS Code**, and the **coding agent**
all read the same files) with the harness installer — it builds from the canonical
`agents/` and `commands/` at install time, so there is nothing generated to drift:

```bash
./scripts/install.mjs --harness github --project <project>   # → <project>/.github/
./scripts/install.mjs --harness github --global              # → ~/.copilot/
./scripts/install.mjs --harness github --project <p> --names norse
```

Re-run after pulling catalog updates. Add `--dry-run` to preview. Since `.github/` is
usually committed in projects, gitignore the installed entries if you don't want them in
the project's repo.

## What's installed

- **16 worker agents** (`.github/agents/*.agent.md`, `user-invocable: false`) —
  frontmatter converted: Copilot `model` id, a `tools` array derived from each agent's
  canonical tools list, body verbatim.
- **4 orchestrator command-skills** (`.github/skills/<name>/SKILL.md`) — VS Code/Copilot
  invoke workflows as **skills**, so each command ships in the agentskills format: ask
  for it by name ("run the plan-orchestrator for IE-1234") or let the description
  trigger it; `$ARGUMENTS` is mapped to "the user's request". No model pin — they run on
  whatever model you've selected.
- **Catalog skills** (tea-cli, gh-cli, bruno-cli, repo-learnings) — copied into
  `.github/skills/`; Copilot consumes the agentskills format natively (manage with
  `/skills` in the CLI).

## Model mapping

Edit `MODEL_MAP.github` in `scripts/install.mjs` to retarget; your install's valid ids
are listed under `model` in `copilot help config`.

| Tier   | Copilot model      |
| ------ | ------------------ |
| haiku  | `claude-haiku-4.5` |
| sonnet | `claude-sonnet-5`  |
| opus   | `claude-opus-4.8`  |

## Tools mapping

The `tools` array uses a **dual vocabulary** — CLI names (`shell`, `write`) and VS Code
aliases (`runCommands`, `editFiles`) side by side. That's deliberate: the custom-agents
spec silently ignores unknown tool names, so one list serves every surface, and the
canonical least-privilege split survives (executors get write access; reviewers and
verifiers don't).

## Notes

- Global installs land in `~/.copilot/agents` and `~/.copilot/skills` — verify your
  Copilot surface picks up global skills; discovery varies by version.
- MCP-dependent agents (Ditto → Chrome DevTools, Slowpoke → Jira) need those MCP servers
  configured for your Copilot surface.
