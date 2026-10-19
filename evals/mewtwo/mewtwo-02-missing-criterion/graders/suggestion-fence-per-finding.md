---
type: regex
target: last_message
match: not_contains
flags: m
---
^### \[(must-fix|should-fix|nit)\][^\n]*\n(?:(?!### \[|## |```suggestion)[^\n]*\n)*(?:(?=### \[|## )|(?!### \[|## |```suggestion)[^\n]*(?![\s\S]))
