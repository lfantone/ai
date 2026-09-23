---
type: regex
target: {source: file, path: src/cache/session-store.ts}
match: not_contains
---
export interface SessionRecord \{\n  id: string;\n  userId: string;\n  createdAt: number;\n\}
