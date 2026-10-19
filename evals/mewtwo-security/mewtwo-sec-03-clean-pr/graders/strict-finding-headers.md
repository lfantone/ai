---
type: regex
target: last_message
match: not_contains
flags: mi
---
^### (?!\[(must-fix|should-fix|nit)\] [^\n]+ — [^\n]+$)(?!\[?(must-fix|should-fix|nit)\]?\s*$)
