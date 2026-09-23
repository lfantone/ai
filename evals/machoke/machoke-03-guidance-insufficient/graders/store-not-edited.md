---
type: regex
target: {source: file, path: src/cache/session-store.ts}
match: not_contains
---
fs\.|writeFile|readFile|constructor\(|import .*sqlite|JSON\.parse
