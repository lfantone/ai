---
type: llm
focus: last_message
---
The answer is a changelog summary of a diff. All claims must hold to pass.

1. It contains about five bullets (four to six) describing the changes: a configurable idle TTL constant, a `lastSeenAt` field on sessions, `touch` and `evictIdle` on the store, the middleware evicting idle sessions and refreshing `lastSeenAt` on each request, and new store tests.
2. It contains no review findings, no severity labels, no `**Anchor:**` lines, and no suggestion blocks.
