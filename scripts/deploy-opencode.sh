#!/usr/bin/env bash
# Links the generated OpenCode agents/commands into a target project's REAL .opencode/
# directory — per file, so they merge with anything OpenCode or you install there.
# Prerequisite: this catalog cloned at <project>/.agents.
#   ./scripts/deploy-opencode.sh <project-dir>
set -euo pipefail

proj="${1:?usage: deploy-opencode.sh <project-dir>}"
src="$proj/.agents/.opencode"

[ -d "$src/agents" ] || {
  echo "error: $src/agents not found — clone the catalog to $proj/.agents first" >&2
  exit 1
}

mkdir -p "$proj/.opencode/agents" "$proj/.opencode/commands"

n=0
for f in "$src"/agents/*.md; do
  ln -sf "../../.agents/.opencode/agents/$(basename "$f")" "$proj/.opencode/agents/$(basename "$f")"
  n=$((n + 1))
done
for f in "$src"/commands/*.md; do
  ln -sf "../../.agents/.opencode/commands/$(basename "$f")" "$proj/.opencode/commands/$(basename "$f")"
  n=$((n + 1))
done

# Skills need nothing: OpenCode natively discovers <project>/.agents/skills/.
echo "Linked $n files into $proj/.opencode/ (agents + commands; skills auto-discovered from .agents/skills/)."
echo "Re-run after 'git pull' in .agents only if files were added/removed — links track content automatically."
