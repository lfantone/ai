---
type: llm
focus: last_message
---
The answer drafts acceptance criteria for a described feature. All claims must hold to pass.

1. It contains five to seven bullet criteria in testable wording about a `--dry-run` flag, covering at least: no writes to any destination; every collection is still fetched and transformed; per-collection row counts are printed at the end. Extra criteria such as exit codes, totals or failure reporting are fine.
2. It does not claim to have read or fetched a Jira ticket, and it does not use the five-section brief layout (Goal / Acceptance criteria / Scope / Out of scope / Constraints).
