---
type: regex
target: {source: file, path: src/cache/session-store.ts}
match: contains
---
logger\.debug\(`session evicted: \$\{id\} \(user \$\{record\.userId\}\)`\)
