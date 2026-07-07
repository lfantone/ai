# GitHub Copilot setup

The repo ships **`.github/agents/`** — the catalog translated to GitHub Copilot's custom
agents format (`*.agent.md`), read by the **Copilot CLI**, **VS Code**, and the **coding
agent** alike. Generated from the canonical `agents/` and `commands/` by a build script;
the canonical files stay the source of truth — never edit `.github/agents/` by hand.

## What's generated

- **16 worker agents** (`.github/agents/*.agent.md`, `user-invocable: false`) —
  frontmatter converted: Copilot `model` id, a `tools` array derived from each agent's
  canonical tools list, body verbatim.
- **4 orchestrator command-skills** (`.github/skills/<name>/SKILL.md`) — VS Code/Copilot
  invoke workflows as **skills**, so each command ships in the agentskills format: ask
  for it by name ("run the plan-orchestrator for IE-1234") or let the description
  trigger it; `$ARGUMENTS` is mapped to "the user's request". No model pin — they run on
  whatever model you've selected.
- **Catalog skills** (tea-cli, gh-cli, bruno-cli, repo-learnings) — per-skill symlinks
  inside `.github/skills/`; Copilot consumes the agentskills `SKILL.md` format natively
  (manage with `/skills` in the CLI).

## Model mapping

| Tier   | Copilot model      |
| ------ | ------------------ |
| haiku  | `claude-haiku-4.5` |
| sonnet | `claude-sonnet-5`  |
| opus   | `claude-opus-4.8`  |

Edit `map_model` in `scripts/build-copilot.sh` to retarget; your install's valid ids are
listed under `model` in `copilot help config`.

## Tools mapping

The `tools` array uses a **dual vocabulary** — CLI names (`shell`, `write`) and VS Code
aliases (`runCommands`, `editFiles`) side by side. That's deliberate: the custom-agents
spec silently ignores unknown tool names, so one list serves every surface, and the
canonical least-privilege split survives (executors get write access; reviewers and
verifiers don't).

## Regenerating

```bash
./scripts/build-copilot.sh
```

The **pre-push hook** runs it automatically and aborts the push on drift — same guarantee
as the OpenCode config.

## Deployment

Same pattern as [OpenCode](./opencode.md) — never symlink the whole `.github/` (projects
own it: workflows, templates); link per file:

```bash
<project>/.agents/scripts/deploy-copilot.sh <project>
```

Links the 16 worker agents into `<project>/.github/agents/` and every skill — the 4
catalog skills plus the 4 orchestrator command-skills — into `<project>/.github/skills/`.
Since `.github/` is usually committed, gitignore the symlinks if you don't want them in
the project's repo.
