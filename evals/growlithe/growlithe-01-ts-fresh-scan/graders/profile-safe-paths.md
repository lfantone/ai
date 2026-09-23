---
type: regex
target: {source: file, path: .agents/cache/security-profile.md}
match: contains
---
requireAdmin[\s\S]*redactSession|redactSession[\s\S]*requireAdmin
