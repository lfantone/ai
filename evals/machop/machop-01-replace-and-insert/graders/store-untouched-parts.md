---
type: regex
target: {source: file, path: src/cache/session-store.ts}
match: contains
---
size\(\): number \{\n    return this\.sessions\.size;
