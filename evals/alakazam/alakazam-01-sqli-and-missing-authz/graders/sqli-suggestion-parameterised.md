---
type: regex
target: last_message
match: contains
---
\$1[\s\S]{0,80}\[sessionId\]|\[sessionId\][\s\S]{0,80}\$1
