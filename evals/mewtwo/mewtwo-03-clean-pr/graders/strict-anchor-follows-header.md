---
type: regex
target: last_message
match: not_contains
flags: m
---
^### \[(must-fix|should-fix|nit)\](?![^\n]*\(not in diff)[^\n]*\n(?!\*\*Anchor:\*\*)
