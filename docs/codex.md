# Codex setup

Install catalog for [Codex](https://developers.openai.com/codex/) with harness installer:

```bash
./scripts/install.mjs --harness codex --project <project>   # → <project>/.codex/ + .agents/
./scripts/install.mjs --harness codex --global              # → ~/.codex/ + ~/.agents/
./scripts/install.mjs --harness codex --project <p> --names norse
```

Re-run after pulling catalog updates. Add `--dry-run` to preview.

## What's installed

- **Agents** — Codex TOML agent files under `.codex/agents/` or `~/.codex/agents/`.
  Canonical Markdown frontmatter and instructions are converted during installation.
- **Skills** — catalog skills under `.agents/skills/` or `~/.agents/skills/`, matching Codex
  skill discovery paths.
- **Orchestrators** — command workflows exposed as regular skills, because Codex has no
  command directory. Invoke them with `$plan-orchestrator`, `$implement-orchestrator`, and
  related skill names.

Codex persistent instructions remain user- or repository-owned `AGENTS.md` files; installer
does not overwrite them.
