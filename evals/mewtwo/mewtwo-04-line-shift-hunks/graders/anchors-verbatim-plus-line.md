---
type: regex
target: last_message
match: contains
flags: m
---
^\*\*Anchor:\*\* `\s*if \(now - record\.lastSeenAt < SESSION_IDLE_TTL_MS\) \{`
