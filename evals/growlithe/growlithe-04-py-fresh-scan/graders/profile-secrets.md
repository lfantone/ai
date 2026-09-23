---
type: regex
target: {source: file, path: .agents/cache/security-profile.md}
match: contains
flags: i
---
KAFKA_SASL_PASSWORD|secrets|\.env
