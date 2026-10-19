# Claude Code setup

```bash
./scripts/install.mjs --harness claude --project <project>   # → <project>/.claude/
./scripts/install.mjs --harness claude --global              # → $CLAUDE_CONFIG_DIR, else ~/.claude/
./scripts/install.mjs --harness claude --project <p> --names norse
```

Re-run after pulling catalog updates. Add `--dry-run` to preview.

## What's installed

- **Agents, commands, skills**: copied as-is. Claude Code reads the canonical frontmatter,
  including each command's `model` and `effort` pins.
- **Global only:** the `instructions/AGENTS.md` block in `CLAUDE.md` in the same config dir,
  between `<!-- ai-catalog-begin -->` / `<!-- ai-catalog-end -->`. Everything else in that
  file is left alone.

`CLAUDE_CONFIG_DIR` moves all of Claude Code's user-level files, so a global install follows
it when it is set in your shell.

## State folder

The workflow keeps its files in `~/.agents/work/`, outside every project. Allow it once in
your user settings — `$CLAUDE_CONFIG_DIR/settings.json`, else `~/.claude/settings.json`:

```json
{
  "permissions": {
    "additionalDirectories": ["/Users/<you>/.agents/work"],
    "allow": ["Edit(~/.agents/work/**)"]
  }
}
```

- `additionalDirectories` makes the folder readable without prompts; give it the absolute
  path.
- The `Edit` rule pre-approves writes there. Claude Code ignores `Write` rules.
- With the sandbox on, also let shell commands write there (`/review` saves its diff):
  `"sandbox": { "filesystem": { "allowWrite": ["~/.agents/work"] } }`.

## Notes

- A command's `model` applies only to the turn it runs in. Start `/investigate` and `/plan`
  in an Opus session so their follow-up turns keep it.
- `/plan`, `/verify`, and `/review` share names with Claude Code's own commands. The picker
  lists both and marks the catalog's with `(user)`; pick that one.
- Ditto lists no `tools:`, so it inherits your session's MCP servers and finds the Chrome
  DevTools tools under whatever name you registered them; `disallowedTools` keeps it from
  editing files or running commands. `/investigate` needs the Atlassian MCP for Jira keys.
