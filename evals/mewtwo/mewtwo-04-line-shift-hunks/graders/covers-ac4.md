---
type: regex
target: last_message
match: contains
flags: m
---
^- [^\n]*\bAC4\b[^\n]*\b(covered|partial|MISSING|descoped)\b
