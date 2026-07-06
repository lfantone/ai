#!/usr/bin/env bash
# Regenerates .opencode/ (agents + commands) from the canonical catalog.
# Run after any change to agents/*.md or commands/*.md (the pre-push hook also runs it):
#   ./scripts/build-opencode.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Model mapping: catalog tier -> GitHub Copilot model id (edit here to retarget) ---
map_model() {
  case "$1" in
    haiku) echo "github-copilot/claude-haiku-4.5" ;;
    sonnet) echo "github-copilot/claude-sonnet-5" ;;
    opus) echo "github-copilot/claude-opus-4.8" ;;
    *) echo "github-copilot/claude-sonnet-5" ;;
  esac
}

rm -rf .opencode/agents .opencode/commands
mkdir -p .opencode/agents .opencode/commands

# --- Agents: convert frontmatter, keep body verbatim ---
for f in agents/*.md; do
  name=$(basename "$f" .md)
  desc=$(sed -n 's/^description: //p' "$f" | head -1)
  tier=$(sed -n 's/^model: \([a-z]*\).*/\1/p' "$f" | head -1)
  tools=$(sed -n 's/^tools: //p' "$f" | head -1)

  # permission: derived from the canonical tools list
  edit=deny
  bash_perm=deny
  case "$tools" in *Edit* | *Write*) edit=allow ;; esac
  case "$tools" in Bash* | *" Bash"*) bash_perm=allow ;; esac

  # deterministic verifiers/executors get a pinned low temperature
  temp=""
  case "$name" in
    machop | machoke | porygon | magneton | magnemite) temp="temperature: 0.1" ;;
  esac

  {
    echo "---"
    echo "description: $desc"
    echo "mode: subagent"
    echo "model: $(map_model "$tier")"
    [ -n "$temp" ] && echo "$temp"
    echo "permission:"
    echo "  edit: $edit"
    echo "  bash: $bash_perm"
    echo "  webfetch: deny"
    echo "---"
    # body = everything after the closing frontmatter fence
    awk 'flag{print} /^---$/{c++; if(c==2) flag=1}' "$f"
  } >".opencode/agents/$name.md"
done

# --- Commands: drop unrecognized keys, map harness terms to OpenCode's ---
for f in commands/*.md; do
  sed \
    -e '/^argument-hint:/d' \
    -e 's/the Agent tool/the task tool/g' \
    -e 's/TaskCreate/todowrite/g' \
    -e 's/TaskUpdate/todowrite/g' \
    "$f" >".opencode/commands/$(basename "$f")"
done

# --- Skills: OpenCode reads the agentskills format natively; just link them ---
ln -sfn ../skills .opencode/skills

echo "Built .opencode/: $(ls .opencode/agents | wc -l | tr -d ' ') agents, $(ls .opencode/commands | wc -l | tr -d ' ') commands, skills symlinked."
