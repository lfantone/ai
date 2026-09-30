# OpenCode setup

```bash
./scripts/install.mjs --harness opencode --project <project>   # → <project>/.opencode/
./scripts/install.mjs --harness opencode --global              # → ~/.config/opencode/
./scripts/install.mjs --harness opencode --project <p> --names norse
./scripts/install.mjs --harness opencode --project <p> --provider claude   # or openai
./scripts/install.mjs --harness opencode-v2 --project <project>   # OpenCode v2 (`@opencode/cli`)
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

## OpenCode v2

`--harness opencode-v2` writes the same dirs, commands, skills, and instructions block, but
emits agents in the v2 schema (verified with `opencode debug agents` on 2.0.20). `--provider`
works the same.

- `permission` → an ordered `permissions` list (`action` / `resource: "*"` / `effect`;
  `bash` → `shell`), appended after v2's allow-all base.
- `reasoning:` → a model variant (`claude-opus-5.5#high`), only where the model has that
  variant — Claude Haiku 4.5 has no `low`, so Machop runs on its default.
- `temperature` → `request.body.temperature`, only for the haiku tier: v2 sends the body as-is,
  and the Sonnet/Opus-tier models reject sampling params.

v2 still loads v1 agent files, but copies `reasoningEffort` and `temperature` into the raw
request body — install with `opencode-v2` once you switch.

## Notes

- The installer copies into a real `.opencode/`. It removes entries it installed before
  (`.ai-catalog-manifest.json`) plus retired catalog names; other tools' entries stay.
- Ditto needs the Chrome DevTools MCP configured in `opencode.json`; `/ticket` needs the
  Atlassian MCP for Jira keys.
