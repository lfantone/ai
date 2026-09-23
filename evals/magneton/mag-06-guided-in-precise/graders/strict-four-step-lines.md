---
type: regex
target: last_message
match: count:4
flags: m
---
^\W*(S[1-4]\b\W*)?(OK\W*$|structural error)
