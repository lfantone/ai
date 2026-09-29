---
type: regex
target: last_message
match: not_contains
flags: mi
---
^### (?!\[(must-fix|recommended|cosmetic)\] [^\n]+ — [^\n]+$)(?!\[?(must-fix|recommended|cosmetic)\]?\s*$)
