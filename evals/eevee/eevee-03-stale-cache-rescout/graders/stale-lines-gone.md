---
type: regex
target: {source: file, path: .agents/cache/repo-profile.md}
match: not_contains
flags: m
---
^- Stack: Node 18, TypeScript, Express 4, \*\*jest\*\*, npm\.$|node:18\.20-alpine
