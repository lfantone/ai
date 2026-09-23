---
type: regex
target: last_message
match: not_contains
flags: m
---
\*\*Acceptance criteria\*\*[^\n]*\n\s*[-*] (?!_?None|N/A|n/a|none)\S
