---
type: llm
focus: last_message
---
The answer is a changelog summary of a diff. All claims must hold to pass.

1. It contains about five bullets (four to six) that, in plain language, together cover: idle sessions now expire after a configurable timeout (`SESSION_IDLE_TTL_MS`, default 30 minutes); sessions track their last activity, refreshed on each request; the middleware removes idle sessions on each request; and new tests. Exact function names are not required, and extra accurate details from the diff (the 401 response, the debug log line, middleware tests) are fine.
2. It contains no review findings, no severity labels, no `**Anchor:**` lines, and no suggestion blocks.
