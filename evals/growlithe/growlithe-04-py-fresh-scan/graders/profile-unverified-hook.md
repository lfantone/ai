---
type: regex
target: {source: file, path: .agents/cache/security-profile.md}
match: contains
flags: i
---
hook[\s\S]*(unverified|no signature|TODO|missing)
