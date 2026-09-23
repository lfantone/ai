---
type: regex
target: {source: file, path: src/http/session-middleware.ts}
match: contains
---
store\.evictIdle\(now\);[\s\S]{0,120}const session = lookup\(store, req\);
