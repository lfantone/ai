---
type: regex
target: last_message
match: contains
flags: mi
---
^### \[must-fix\][^\n]*(requireAdmin|authz|authori[sz]ation|admin)[^\n]*— (src/http/routes/admin/export\-session\.ts:(?:8|(?:5|6|7|8)-(?:8|9|10|11))\b|\(not in diff — missing\))
