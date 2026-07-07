#!/usr/bin/env bash
# Links the generated Copilot agents into a target project's REAL .github/ directory —
# per file, so they merge with anything else living there (workflows, templates, etc.).
# Prerequisite: this catalog cloned at <project>/.agents.
#   ./scripts/deploy-copilot.sh <project-dir>
set -euo pipefail

proj="${1:?usage: deploy-copilot.sh <project-dir>}"
src="$proj/.agents/.github"

[ -d "$src/agents" ] || {
  echo "error: $src/agents not found — clone the catalog to $proj/.agents and run scripts/build-copilot.sh first" >&2
  exit 1
}

mkdir -p "$proj/.github/agents" "$proj/.github/skills"

n=0
for f in "$src"/agents/*.agent.md; do
  ln -sf "../../.agents/.github/agents/$(basename "$f")" "$proj/.github/agents/$(basename "$f")"
  n=$((n + 1))
done

# Skills: link each entry (Copilot discovers .github/skills/<name>/SKILL.md).
# Catalog skills link straight to .agents/skills/ (avoids symlink chains); the generated
# command-skills link to the built .github/skills/ dirs.
for d in "$src"/skills/*/; do
  skill=$(basename "$d")
  if [ -d "$proj/.agents/skills/$skill" ]; then
    ln -sfn "../../.agents/skills/$skill" "$proj/.github/skills/$skill"
  else
    ln -sfn "../../.agents/.github/skills/$skill" "$proj/.github/skills/$skill"
  fi
  n=$((n + 1))
done

echo "Linked $n entries into $proj/.github/ (agents + skills)."
echo "Heads-up: .github/ is usually committed in projects — add the symlinks to .gitignore if you don't want them in the project's repo."
