---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Agent]
plugins: [../../..]
model: opus
runs: 3
---
Explain, in one short paragraph each, what the six items of this threat profile mean for a developer adding a new HTTP handler. Do not review any code and do not produce findings.

## Threat profile (Growlithe, ranked)
generated: 2026-09-18, head: 7d3f1a2c
1. **Entry points:** Express HTTP. Every `/api/admin/*` handler must call `requireAdmin(req)` itself — there is NO router-level guard; the prefix is a naming convention only.
2. **Data access:** raw SQL through `db.query(text, params)`. Only parameterised queries; string interpolation into SQL is forbidden.
3. **Sensitive data:** session tokens (`sessions.token`, also the `sid` cookie value) are credentials. Never log them; API responses go through `redactSession()` before serialisation. Session ids and user ids are not secrets and may be logged.
4. **Input validation:** path and body parameters are validated with the zod schemas in `src/lib/safe-paths.ts` (`sessionIdSchema`, `userIdSchema`) before use.
5. **Cookies:** the `sid` cookie is set with `httpOnly: true, secure: true, sameSite: "lax"`; weakening any attribute is a must-fix.
7. **Credentials:** login verifies the password through `verifyPassword()` in `src/lib/safe-paths.ts` (throws 401); issuing a session without it is a must-fix.
6. **Footguns:** `req.user` is only populated after `sessionMiddleware`; `res.json(record)` serialises every column including `token`.
