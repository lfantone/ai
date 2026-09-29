# GitHub Copilot setup

Copilot CLI, VS Code, and the coding agent read the same files.

```bash
./scripts/install.mjs --harness github --project <project>   # → <project>/.github/
./scripts/install.mjs --harness github --global              # → ~/.copilot/
./scripts/install.mjs --harness github --project <p> --names norse
```

Re-run after pulling catalog updates. Add `--dry-run` to preview. `.github/` is usually
committed, so gitignore the installed entries if they shouldn't land in the project repo.

## What's installed

- **4 agents** (`.github/agents/*.agent.md`, `user-invocable: false`): Copilot `model` id and
  a `tools` array derived from the canonical tools list.
- **5 command-skills** (`.github/skills/<name>/SKILL.md`): Copilot runs workflows as skills,
  so each command ships in the agentskills format. Ask for it by name ("run ticket for
  IE-1234"); `$ARGUMENTS` becomes "the user's request".
- **Catalog skills**: copied as-is.
- **Global only:** the `instructions/AGENTS.md` block in
  `~/.copilot/copilot-instructions.md` (verified against Copilot CLI 0.0.418), between
  `<!-- ai-catalog-begin -->` / `<!-- ai-catalog-end -->`.

## Model mapping

Valid ids are listed under `model` in `copilot help config`.

| Tier   | Copilot model      |
| ------ | ------------------ |
| haiku  | `claude-haiku-4.5` |
| sonnet | `claude-sonnet-5`  |
| opus   | `claude-opus-5.5`  |

## Tools

Agents that use only portable built-ins get a least-privilege dual-vocabulary `tools` array
(CLI `shell`/`write` plus VS Code `runCommands`/`editFiles`). Ditto needs the Chrome DevTools
MCP, whose server name is installation-specific, so it omits `tools` and Copilot enables all
configured tools. See the
[custom-agent tools reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration#tools).

Global skill discovery in `~/.copilot/skills` varies by Copilot surface and version — check
yours picks them up.
