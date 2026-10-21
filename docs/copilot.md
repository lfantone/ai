# GitHub Copilot setup

Copilot CLI, VS Code, and the coding agent read the same files.

```bash
./scripts/install.mjs --harness github --project <project>   # → .github/agents, .agents/skills
./scripts/install.mjs --harness github --global              # → ~/.copilot/
./scripts/install.mjs --harness github --project <p> --names norse
./scripts/install.mjs --harness github --project <p> --prefix oct- --skip tea-cli
```

Re-run after pulling catalog updates. Add `--dry-run` to preview. `.github/` and `.agents/` are
usually committed, so gitignore the installed entries if they shouldn't land in the project repo.

## What's installed

- **3 agents** (`.github/agents/*.agent.md`, `user-invocable: false`): Copilot `model` id and
  a `tools` array derived from the canonical tools list.
- **6 command-skills** (`.agents/skills/<name>/SKILL.md`): Copilot runs workflows as skills,
  and both VS Code chat and Copilot CLI list skills as slash commands, so each runs as
  `/<name>` (`/oct-plan` with `--prefix oct-`); `$ARGUMENTS` becomes "the user's request".
  They are marked user-run (`disable-model-invocation: true` and a description saying so):
  agent mode and Copilot code review otherwise activate any repo skill that looks relevant.
  That field is a Copilot extension, so strict `agentskills validate` rejects these generated
  skills; Copilot honours it. `metadata` `opencode/autoinvoke` keeps OpenCode from picking them
  too, and a project install writes `.opencode/commands/<name>.md` to load each one, since OpenCode
  2 doesn't turn skills into slash commands. Command model and effort pins don't carry over.
- **Catalog skills** (`.agents/skills/`): copied as-is.
- **Global only:** the `instructions/AGENTS.md` block in
  `~/.copilot/copilot-instructions.md` (verified against Copilot CLI 0.0.418), between
  `<!-- ai-catalog-begin -->` / `<!-- ai-catalog-end -->`.

## Skills folder

Project skills go to `.agents/skills`, the cross-tool folder: VS Code, Copilot CLI, the cloud
agent, and code review read it
([About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)),
and so do OpenCode and Codex — one copy serves them all. Copilot CLI 0.0.398 still read only
`.github/skills`: update older CLIs. A re-install removes the catalog's earlier copies from
`.github/skills` and leaves the project's own skills there; move those to `.agents/skills` too,
so each skill lives in one folder.

## State folder

Copilot CLI asks before touching a directory outside the project, and edits there can still
ask for write approval. Grant the workflow folder per session with `/add-dir ~/.agents/work`,
or at launch with `copilot --add-dir ~/.agents/work` (an alias makes it stick). To save it for
one project, add the absolute path to that project's entry in
`$COPILOT_HOME/permissions-config.json` (default `~/.copilot`):

```json
{
  "locations": {
    "/Users/<you>/work/my-app": {
      "allowed_directories": ["/Users/<you>/.agents/work"]
    }
  }
}
```

Untested on VS Code and the cloud coding agent.

## Copilot code review

Copilot's built-in PR review reads, from the PR's head branch, the root `AGENTS.md`, a root
`REVIEW.md`, `.github/copilot-instructions.md`, and `.github/instructions/**/*.instructions.md`
whose `applyTo` matches a reviewed file. It does not follow links, so rules it must enforce
belong inline. It also activates repo skills that look relevant, and can use:

- **MCP servers** — GitHub and Playwright by default; more through the repository's Copilot
  MCP settings, shared with the cloud agent. Allow read-only tools only; secrets are Agents
  secrets named `COPILOT_MCP_*`; remote servers that need OAuth are not supported.
- **An environment** — `.github/workflows/copilot-setup-steps.yml` (job
  `copilot-setup-steps`), or `copilot-code-review.yml` for review alone, prepares the runner,
  e.g. installs dependencies. It only runs from the default branch, and the integrated
  firewall needs GitHub-hosted runners.

The review session's "Setting up environment" log shows which skills and MCP tools it used.
See [Use Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-code-review)
and [Configure MCP servers](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers).

## Model mapping

Valid ids are listed under `model` in `copilot help config`.

| Tier   | Copilot model       |
| ------ | ------------------- |
| haiku  | `claude-haiku-5.5`  |
| sonnet | `claude-sonnet-5.5` |
| opus   | `claude-opus-5.5`   |

## Tools

Agents that use only portable built-ins get a least-privilege dual-vocabulary `tools` array
(CLI `shell`/`write` plus VS Code `runCommands`/`editFiles`). Ditto needs the Chrome DevTools
MCP, whose server name is installation-specific, so it omits `tools` and Copilot enables all
configured tools. See the
[custom-agent tools reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration#tools).

Global skill discovery in `~/.copilot/skills` varies by Copilot surface and version — check
yours picks them up.
