---
type: regex
target: {source: file, path: src/http/session-middleware.ts}
match: contains
---
if \(!session\) return res\.status\(401\)\.json\(\{ error: "unauthenticated" \}\);\n    store\.touch\(sessionId, now\);
