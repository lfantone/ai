---
type: regex
target: last_message
match: contains
---
rate-limit-store\.ts[^\n]*\bsweep\b|\bsweep\b[^\n]*rate-limit-store\.ts
