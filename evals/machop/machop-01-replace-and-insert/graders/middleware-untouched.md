---
type: regex
target: {source: file, path: src/http/session-middleware.ts}
match: not_contains
---
evictIdle|touch\(
