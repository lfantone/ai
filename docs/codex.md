# Codex setup

```bash
./scripts/install.mjs --harness codex --project <project>   # → <project>/.codex/ + .agents/
./scripts/install.mjs --harness codex --global              # → ~/.codex/ + ~/.agents/
./scripts/install.mjs --harness codex --project <p> --names norse
```

Re-run after pulling catalog updates. Add `--dry-run` to preview.

## What's installed

- **Agents**: TOML agent files in `.codex/agents/` or `~/.codex/agents/`, converted from the
  canonical Markdown.
- **Skills**: catalog skills in `.agents/skills/` or `~/.agents/skills/`.
- **Commands**: exposed as skills because Codex has no command directory — invoke them as
  `$investigate`, `$plan`, `$implement`, `$verify`, `$ship`, `$review`. Command model and
  effort pins don't carry over; pick the model in your session.
- **Global only:** the `instructions/AGENTS.md` block in `~/.codex/AGENTS.md`, between
  `<!-- ai-catalog-begin -->` / `<!-- ai-catalog-end -->`. A repository's own `AGENTS.md` is
  never touched.

## State folder

Codex's `workspace-write` sandbox limits writes to the workspace and keeps `.git` and `.agents`
read-only inside it, so the workflow folder must be a writable root. Add it to
`~/.codex/config.toml` as an absolute path:

```toml
[sandbox_workspace_write]
writable_roots = ["/Users/<you>/.agents/work"]
```
