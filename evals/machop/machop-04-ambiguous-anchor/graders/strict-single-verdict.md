---
type: regex
target: last_message
match: count:1
flags: m
---
^`?(OK — S\d+ done|PRECONDITION_FAILED: .+?|VERIFICATION_FAILED: .+?|CONTRACT_INVALID: .+?)`?\s*$
