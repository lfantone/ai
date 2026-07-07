#!/usr/bin/env bash
# Regenerates .github/agents/ from the canonical catalog for GitHub Copilot
# (CLI, VS Code, and the coding agent all read .github/agents/*.agent.md).
# Run after any change to agents/*.md or commands/*.md (the pre-push hook also runs it):
#   ./scripts/build-copilot.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Model mapping: catalog tier -> Copilot model id (edit here to retarget) ---
map_model() {
  case "$1" in
    haiku) echo "claude-haiku-4.5" ;;
    sonnet) echo "claude-sonnet-5" ;;
    opus) echo "claude-opus-4.8" ;;
    *) echo "claude-sonnet-5" ;;
  esac
}

rm -rf .github/agents
mkdir -p .github/agents

# --- Worker agents: convert frontmatter, keep body verbatim ---
# tools: dual vocabulary (CLI: shell/write · VS Code: runCommands/editFiles) —
# unknown tool names are silently ignored per the custom-agents spec, so both are safe.
for f in agents/*.md; do
  name=$(basename "$f" .md)
  display=$(sed -n 's/^name: //p' "$f" | head -1 | sed 's/ #.*//')
  desc=$(sed -n 's/^description: //p' "$f" | head -1)
  tier=$(sed -n 's/^model: \([a-z]*\).*/\1/p' "$f" | head -1)
  tools=$(sed -n 's/^tools: //p' "$f" | head -1)

  tool_list='"read", "search"'
  case "$tools" in Bash* | *" Bash"*) tool_list+=', "shell", "runCommands"' ;; esac
  case "$tools" in *Edit* | *Write*) tool_list+=', "write", "editFiles"' ;; esac

  {
    echo "---"
    echo "name: $display"
    echo "description: $desc"
    echo "model: $(map_model "$tier")"
    echo "tools: [$tool_list]"
    echo "user-invocable: false"
    echo "---"
    awk 'flag{print} /^---$/{c++; if(c==2) flag=1}' "$f"
  } >".github/agents/$name.agent.md"
done

# --- Orchestrator commands become SKILLS (VS Code/Copilot invoke workflows as skills) ---
# .github/skills/ is a real dir: per-skill symlinks to the catalog skills + generated
# command-skills in the agentskills SKILL.md format (which Copilot consumes natively).
rm -rf .github/skills
mkdir -p .github/skills

for d in skills/*/; do
  skill=$(basename "$d")
  ln -sfn "../../skills/$skill" ".github/skills/$skill"
done

for f in commands/*.md; do
  name=$(basename "$f" .md)
  desc=$(sed -n 's/^description: //p' "$f" | head -1)
  mkdir -p ".github/skills/$name"
  {
    echo "---"
    echo "name: $name"
    echo "description: $desc"
    echo "---"
    awk 'flag{print} /^---$/{c++; if(c==2) flag=1}' "$f" |
      sed \
        -e 's/`\$ARGUMENTS`/the user'"'"'s request/g' \
        -e 's/\$ARGUMENTS/the user'"'"'s request/g' \
        -e 's/via the Agent tool/as subagents/g' \
        -e 's/the Agent tool/your subagent mechanism/g' \
        -e 's/TaskCreate/your task list/g' \
        -e 's/TaskUpdate/your task list/g'
  } >".github/skills/$name/SKILL.md"
done

echo "Built .github/: $(ls .github/agents | wc -l | tr -d ' ') worker agents + $(ls commands/*.md | wc -l | tr -d ' ') command skills + $(ls skills | wc -l | tr -d ' ') catalog skills linked."
