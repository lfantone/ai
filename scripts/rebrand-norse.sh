#!/usr/bin/env bash
# One-shot rebrand: Pokémon roster → Norse mythology (for the non-Pokémon fans).
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

# --- 4. Generated harness configs -------------------------------------------------------
# Nothing to do: harness configs are built at install time by scripts/install.mjs (which
# has its own --names norse mode). Update its NORSE map if you change the map above.

# --- 5. Format ---------------------------------------------------------------------------
if [ -x node_modules/.bin/prettier ]; then
  node_modules/.bin/prettier --write --log-level warn "**/*.md"
fi

# --- 6. Self-verify: no old names may survive -------------------------------------------
leftovers=$(grep -rniE 'slowbro|slowpoke|kadabra|eevee|growlithe|dugtrio|mewtwo|alakazam|porygon|magneton|magnemite|machop|machoke|machamp|pok(e|é)mon|\bmew\b|\babra\b|\bditto\b' \
  agents commands docs skills README.md AGENTS.md 2>/dev/null || true)
if [ -n "$leftovers" ]; then
  echo "REBRAND INCOMPLETE — old names remain:" >&2
  echo "$leftovers" >&2
  exit 1
fi

echo "Rebrand complete: $(ls agents/*.md | wc -l | tr -d ' ') agents renamed, references rewritten."
echo "Manual follow-ups: adjust the README title/clone URL for your repo, then delete this script."
