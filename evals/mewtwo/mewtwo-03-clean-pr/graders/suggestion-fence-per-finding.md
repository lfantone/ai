---
type: regex
target: last_message
match: not_contains
flags: m
---
^### \[(must-fix|recommended|cosmetic)\][^\n]*\n(?:(?!### \[|## |```suggestion)[^\n]*\n)*(?:(?=### \[|## )|(?!### \[|## |```suggestion)[^\n]*(?![\s\S]))
