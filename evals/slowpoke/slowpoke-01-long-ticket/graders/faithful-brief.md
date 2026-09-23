---
type: llm
focus: last_message
---
The answer is a requirement brief extracted from a long Jira story. The story has a two-sentence goal, eight "This story is done when" criteria (python folder, .env files mirroring properties, REST-only loading of nine collections, SQLite persistence, cron start, Kafka topics via one publish function, a --parquets INSERT+FILES mode with S3 buckets, and retry/notify/quarantine error handling), two long design-rationale sections (windowed collection walk, incremental cursor), and a final sentence excluding the reporting module and report UI tasks. All claims must hold to pass.

1. The Acceptance criteria bullets correspond to the eight "done when" items. Design-rationale details (page-depth limits, ChangedSince being ignored, sub-cursors, the live-API test) may appear under Constraints or Scope but are NOT presented as acceptance criteria, and nothing is invented.
2. The Out of scope section names the reporting module / report UI tasks. It is not merged into Scope and not omitted.
3. The brief is a summary, not a dump: no paragraph of the description is reproduced verbatim, and the whole answer is compact (about 200 words or fewer).
4. There is no preamble, no narration of what the agent did, and no trailing commentary.
