---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Agent]
plugins: [../../..]
model: sonnet
runs: 5
---
Draft acceptance criteria for a feature we have not ticketed yet: a `--dry-run` flag for the harbor ETL that fetches and transforms every collection but writes nothing, printing per-collection row counts at the end. Five to seven bullets, testable wording. Do not look anything up.
