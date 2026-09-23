---
type: llm
focus: last_message
---
The answer is a requirement brief for a thin Jira task whose one-line description defers to its parent epic. All claims must hold to pass.

1. The Acceptance criteria are the epic's: declarable windowing strategy, window upper bound clamped to the present, per-window sub-cursors, watermark advancing only when all windows complete, per-tenant concurrency cap. At least four of these five appear.
2. The Scope reflects the task itself: declaring the windowing config for MeterReadings.
3. Out of scope carries the epic's exclusions (page size, partitioning by reading type) or says _None._. Inferring "implementation of the windowing logic" as out of scope from the task's "Config only" wording is acceptable; nothing else is invented.
4. No raw ticket JSON or verbatim description dump; compact; no preamble.
