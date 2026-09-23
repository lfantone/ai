---
type: regex
target: last_message
match: contains
---
rate-limit-store\.ts[^\n]*(\bsweep\b|RateLimitStore)|(\bsweep\b|RateLimitStore)[^\n]*rate-limit-store\.ts
