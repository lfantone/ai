# OpenCode setup

```bash
./scripts/install.mjs --harness opencode --project <project>   # → <project>/.opencode/
./scripts/install.mjs --harness opencode --global              # → ~/.config/opencode/
./scripts/install.mjs --harness opencode --project <p> --names norse
./scripts/install.mjs --harness opencode --project <p> --provider claude   # or openai
```

Re-run after pulling catalog updates. Add `--dry-run` to preview.

## What's installed

- **`agents/*.md`**: the 4 agents with `mode: subagent`, the provider's `model`, and a
  `permission` object derived from each agent's canonical `tools` (`edit: allow` only for
  the Machop/Machoke workers).
- **`commands/*.md`**: the 5 commands; `$ARGUMENTS` works as-is.
- **`skills/`**: copied as-is (OpenCode reads `SKILL.md` natively).
- **Global only:** the `instructions/AGENTS.md` block in `~/.config/opencode/AGENTS.md`,
  between `<!-- ai-catalog-begin -->` / `<!-- ai-catalog-end -->`. Everything else in that
  file is left alone.

## Model mapping

`--provider` selects the column (default `copilot`); `opencode models <provider>` lists ids.

| Tier   | Copilot                            | Claude                        | OpenAI/Codex                 |
| ------ | ---------------------------------- | ----------------------------- | ---------------------------- |
| haiku  | `github-copilot/claude-haiku-4.5`  | `anthropic/claude-haiku-4-5`  | `openai/gpt-5.4-mini`        |
| sonnet | `github-copilot/claude-sonnet-5.5` | `anthropic/claude-sonnet-5-5` | `openai/gpt-5.3-codex-spark` |
| opus   | `github-copilot/claude-opus-5.5`   | `anthropic/claude-opus-5-5`   | `openai/gpt-5.6-sol`         |

`temperature`, `color`, and `reasoning` (→ `reasoningEffort`) come from the canonical
agent frontmatter. Colors are the Pokémon type color shaded by tier (Machop `#E57373` →
Machoke `#C03028`); Norse names keep them.

## Notes

- The installer copies into a real `.opencode/`. It removes entries it installed before
  (`.ai-catalog-manifest.json`) plus retired catalog names; other tools' entries stay.
- Ditto needs the Chrome DevTools MCP configured in `opencode.json`; `/ticket` needs the
  Atlassian MCP for Jira keys.
