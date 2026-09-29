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
  `$ticket`, `$verify`, `$ship`, `$pr-review`, `$pr-feedback`.
- **Global only:** the `instructions/AGENTS.md` block in `~/.codex/AGENTS.md`, between
  `<!-- ai-catalog-begin -->` / `<!-- ai-catalog-end -->`. A repository's own `AGENTS.md` is
  never touched.
