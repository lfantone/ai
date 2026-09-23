---
type: regex
target: last_message
match: count:1
flags: m
---
^`?(OK — S\d+ done|failed: .+?)`?\s*$
