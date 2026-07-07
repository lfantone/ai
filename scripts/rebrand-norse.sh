#!/usr/bin/env bash
# One-shot rebrand: Pokémon roster → Norse mythology (for the private "octopus" repo).
# Renames agent files, rewrites every reference (both cases, word-boundary), updates the
# AGENTS.md naming rule, regenerates .opencode/, formats, and self-verifies.
# Run ONCE in a clone of the catalog, review the diff, commit. Then delete this script.
set -euo pipefail
cd "$(dirname "$0")/.."

# --- Name map (canonical → Norse). Order matters: longest-overlapping first (Mewtwo > Mew).
MAP=(
  "Slowbro:Odin"
  "Mewtwo:Mimir"
  "Mew:Bragi"
  "Slowpoke:Ratatoskr"
  "Kadabra:Huginn"
  "Eevee:Muninn"
  "Growlithe:Heimdall"
  "Dugtrio:Kraken"
  "Alakazam:Tyr"
  "Porygon:Urd"
  "Magneton:Skuld"
  "Magnemite:Verdandi"
  "Machop:Brokkr"
  "Machoke:Sindri"
  "Machamp:Volund"
  "Abra:Skadi"
  "Ditto:Loki"
)

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

# --- 1. Rename agent files -------------------------------------------------------------
for pair in "${MAP[@]}"; do
  old_l=$(lower "${pair%%:*}")
  new_l=$(lower "${pair##*:}")
  [ -f "agents/$old_l.md" ] && mv "agents/$old_l.md" "agents/$new_l.md"
done

# --- 2. Rewrite references everywhere (both cases, word-boundary) ------------------------
FILES=$(ls agents/*.md commands/*.md docs/*.md skills/*/SKILL.md README.md AGENTS.md 2>/dev/null)

subs=""
for pair in "${MAP[@]}"; do
  old="${pair%%:*}" new="${pair##*:}"
  subs+="s/\\b${old}\\b/${new}/g; s/\\b$(lower "$old")\\b/$(lower "$new")/g; "
done
# shellcheck disable=SC2086
perl -pi -e "$subs" $FILES

# --- 3. Prose: the naming convention itself --------------------------------------------
perl -CSD -0777 -pi -e 's/- \*\*Names are Generation I Pok\x{e9}mon only\*\*.*?follows the same rule\./- **Names come from Norse mythology.** Pick a figure whose myth matches the role \x{2014} the\n  ravens gather, the Norns verify, the smiths execute; families map onto model tiers. The\n  orchestrator persona in a command follows the same rule./s' AGENTS.md
# shellcheck disable=SC2086
perl -CSD -pi -e 's/named after a Pok\x{e9}mon/named after a figure from Norse mythology/g; s/\bPok\x{e9}mon\b/Norse mythology/g' $FILES

# --- 4. Bring the generated harness configs along ----------------------------------------
[ -x scripts/build-opencode.sh ] && ./scripts/build-opencode.sh
[ -x scripts/build-copilot.sh ] && ./scripts/build-copilot.sh

# Fallback for trees without the translators — rename/rewrite generated copies directly.
rewrite_generated() {
  local dir="$1" suffix="$2"
  [ -d "$dir" ] || return 0
  for pair in "${MAP[@]}"; do
    local old_l new_l
    old_l=$(lower "${pair%%:*}")
    new_l=$(lower "${pair##*:}")
    [ -f "$dir/$old_l$suffix" ] && mv "$dir/$old_l$suffix" "$dir/$new_l$suffix"
  done
  local gen_files
  gen_files=$(find "$dir" -name '*.md' 2>/dev/null || true)
  if [ -n "$gen_files" ]; then
    # shellcheck disable=SC2086
    perl -pi -e "$subs" $gen_files
    # shellcheck disable=SC2086
    perl -CSD -pi -e 's/named after a Pok\x{e9}mon/named after a figure from Norse mythology/g; s/\bPok\x{e9}mon\b/Norse mythology/g' $gen_files
  fi
}
[ -x scripts/build-opencode.sh ] || { rewrite_generated .opencode/agents .md; rewrite_generated .opencode/commands .md; }
[ -x scripts/build-copilot.sh ] || { rewrite_generated .github/agents .agent.md; rewrite_generated .github/skills .md; }

# --- 5. Format ---------------------------------------------------------------------------
if [ -x node_modules/.bin/prettier ]; then
  node_modules/.bin/prettier --write --log-level warn "**/*.md"
fi

# --- 6. Self-verify: no old names may survive -------------------------------------------
leftovers=$(grep -rniE 'slowbro|slowpoke|kadabra|eevee|growlithe|dugtrio|mewtwo|alakazam|porygon|magneton|magnemite|machop|machoke|machamp|pok(e|é)mon|\bmew\b|\babra\b|\bditto\b' \
  agents commands docs skills README.md AGENTS.md .opencode .github/agents .github/skills 2>/dev/null || true)
if [ -n "$leftovers" ]; then
  echo "REBRAND INCOMPLETE — old names remain:" >&2
  echo "$leftovers" >&2
  exit 1
fi

echo "Rebrand complete: $(ls agents/*.md | wc -l | tr -d ' ') agents renamed, references rewritten, .opencode regenerated."
echo "Manual follow-ups: README title/clone URL for the octopus repo, then delete this script."
