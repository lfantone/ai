---
type: regex
target: {source: file, path: .agents/cache/repo-profile.md}
match: contains
flags: i
---
Date\.now\(\)[^\n]*(clock|banned|only)
