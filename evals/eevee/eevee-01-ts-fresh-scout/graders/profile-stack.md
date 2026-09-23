---
type: regex
target: {source: file, path: .agents/cache/repo-profile.md}
match: contains
flags: i
---
vitest[\s\S]*Express|Express[\s\S]*vitest
