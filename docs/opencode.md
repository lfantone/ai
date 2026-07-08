# OpenCode setup

Install the catalog for [OpenCode](https://opencode.ai) with the harness installer — it
builds from the canonical `agents/` and `commands/` at install time, so there is nothing
generated to drift:

```bash
./scripts/install.mjs --harness opencode --project <project>   # → <project>/.opencode/
./scripts/install.mjs --harness opencode --global              # → ~/.config/opencode/
./scripts/install.mjs --harness opencode --project <p> --names norse
```

Re-run after pulling catalog updates. Add `--dry-run` to preview.

## What's installed

- **`agents/*.md`** — the 16 agents with OpenCode frontmatter: `mode: subagent`, a GitHub
  Copilot `model`, and a `permission` object derived from each agent's canonical `tools`
  list (least-privilege: `edit: allow` only for executors and cache-writers).
- **`commands/*.md`** — the 4 orchestrators (`$ARGUMENTS` works as-is); harness terms are
  mapped (`Agent tool` → `task tool`, `TaskCreate`/`TaskUpdate` → `todowrite`).
- **`skills/`** — copied as-is: OpenCode reads the agentskills `SKILL.md` format natively.

## Model mapping

Catalog tiers map to GitHub Copilot model ids (edit `MODEL_MAP.opencode` in
`scripts/install.mjs` to retarget; `opencode models | grep copilot` lists your install's
valid ids):

| Tier   | OpenCode model                    |
| ------ | --------------------------------- |
| haiku  | `github-copilot/claude-haiku-4.5` |
| sonnet | `github-copilot/claude-sonnet-5`  |
| opus   | `github-copilot/claude-opus-4.8`  |

## Agent properties

All three ride through from the **canonical agent frontmatter** (self-contained files —
no installer-side maps, so renames can never orphan them):

- **`temperature: 0.1`** — pinned in the deterministic verifiers/executors (Machop,
  Machoke, Porygon, Magneton, Magnemite).
- **`color`** — a unique hex per agent so the TUI shows at a glance who's working: the
  Pokémon **type color, shaded by evolution stage/tier**. The Fighting executor ladder
  darkens as it escalates (`#E57373` Machop → `#C03028` Machoke → `#8E1B12` Machamp),
  the five Psychics get distinct shades (light Abra → dark Mewtwo), and the
  Magnemite/Magneton pair splits its Electric/Steel dual type. Norse names inherit their
  colors automatically (Mimir wears Mewtwo's purple).
- **`reasoningEffort`** — the canonical `reasoning:` field, renamed to the provider
  pass-through option (e.g. Mewtwo/Alakazam `high`, Porygon/Machop `low`).

Considered and deliberately **unset**: `top_p` (don't tune it and `temperature`
together), `hidden` (workers are `mode: subagent` already — keeping them `@`-able helps
debugging), `textVerbosity` (provider-specific; the compact-brief discipline lives in the
agent prompts, where it's portable). Any other frontmatter key passes through to the
provider as a model option if you need one later.

## Notes

- The installer **copies** into a real `.opencode/` — it merges with whatever OpenCode or
  you already keep there and never symlinks the whole directory.
- MCP-dependent agents (Ditto → Chrome DevTools, Slowpoke → Jira) need those MCP servers
  configured in your `opencode.json`; their permissions deny `bash`/`edit`, so they can
  only act through their MCPs.
- Verify with `opencode` in the project: agents appear in the `@` menu, commands under `/`.
