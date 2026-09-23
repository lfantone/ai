---
type: regex
target: last_message
match: not_contains
flags: m
---
^V\d+\b(?! · surface: (web|api|cli) · mutating: (yes|no) · criterion: )
