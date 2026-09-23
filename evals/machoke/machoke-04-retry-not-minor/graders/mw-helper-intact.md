---
type: regex
target: {source: file, path: src/http/session-middleware.ts}
match: contains
---
const session = resolveSession\(store, req\);
