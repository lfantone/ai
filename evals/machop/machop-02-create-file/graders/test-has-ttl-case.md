---
type: regex
target: {source: file, path: src/cache/__tests__/session-store.test.ts}
match: contains
---
SESSION_IDLE_TTL_MS \+ 1\)
