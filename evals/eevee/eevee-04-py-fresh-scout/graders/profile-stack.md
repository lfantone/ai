---
type: regex
target: {source: file, path: .agents/cache/repo-profile.md}
match: contains
flags: i
---
pytest[\s\S]*ruff|ruff[\s\S]*pytest
