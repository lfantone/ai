#!/usr/bin/env bash
# Set a Jira issue's description from an ADF document:
#   acli-set-description.sh IE-123 doc.adf.json
# acli's --description-file leaves the description empty; --from-json with
# {description, issues} works.
set -euo pipefail

usage="usage: acli-set-description.sh <KEY> <doc.adf.json>"
key="${1:?$usage}"
doc="${2:?$usage}"

jq -e '.type == "doc" and .version == 1 and (.content | type == "array")' "$doc" >/dev/null ||
  { echo "not an ADF document: $doc" >&2; exit 1; }

workitem="$(mktemp)"
trap 'rm -f "$workitem"' EXIT
jq --arg key "$key" '{description: ., issues: [$key]}' "$doc" >"$workitem"
acli jira workitem edit --from-json "$workitem" --yes
