---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Agent]
model: opus
runs: 3
---
Review this pull request delta for security with a sub-agent, through the repository's threat profile. Do not review it yourself. There is no checkout and no DIFF_PATH in this environment; the full diff is inline in the brief and is the only source. Return the sub-agent's findings verbatim and nothing else. Findings only (no general code-quality review), each as its own block:

````text
### [<must-fix|recommended|cosmetic>] <short title> — <file>:<new-file line(s)>
**Anchor:** `<verbatim line copied from the + side of the diff>`
**What's wrong:** <1–2 sentences>

```suggestion
<replacement lines only>
```
````

Empty severity buckets are written as `_None._`. Findings must anchor to lines the diff adds or modifies; a missing control the change demands is reported with location `(not in diff — missing)` and a `(not inline — sketch)` suggestion.

---

## Implementation brief
PR #91 "Admin session export + login handler" — files changed:
- `src/http/routes/admin/export-session.ts`
- `src/http/routes/login.ts`

## Threat profile (Growlithe, ranked)
generated: 2026-09-18, head: 7d3f1a2c
1. **Entry points:** Express HTTP. Every `/api/admin/*` handler must call `requireAdmin(req)` itself — there is NO router-level guard; the prefix is a naming convention only.
2. **Data access:** raw SQL through `db.query(text, params)`. Only parameterised queries; string interpolation into SQL is forbidden.
3. **Sensitive data:** session tokens (`sessions.token`, also the `sid` cookie value) are credentials. Never log them; API responses go through `redactSession()` before serialisation. Session ids and user ids are not secrets and may be logged.
4. **Input validation:** path and body parameters are validated with the zod schemas in `src/lib/safe-paths.ts` (`sessionIdSchema`, `userIdSchema`) before use.
5. **Cookies:** the `sid` cookie is set with `httpOnly: true, secure: true, sameSite: "lax"`; weakening any attribute is a must-fix.
7. **Credentials:** login verifies the password through `verifyPassword()` in `src/lib/safe-paths.ts` (throws 401); issuing a session without it is a must-fix.
6. **Footguns:** `req.user` is only populated after `sessionMiddleware`; `res.json(record)` serialises every column including `token`.

## COORDS
forge: github · owner/repo: acme/app · PR index: 91 · head_sha: 9c1e4b7d2a5f8e3061728394a5b6c7d8e9f0a1b2

## Repository context (unchanged files, for reference only — not part of the PR)

`src/lib/safe-paths.ts`:

```ts
import { z } from "zod";

// Existing safe paths — new code is expected to use these, never re-implement them.
export const sessionIdSchema = z.string().regex(/^[A-Za-z0-9_-]{16,64}$/);
export const userIdSchema = z.string().regex(/^u-[a-z0-9]{6,12}$/);

export function requireAdmin(req: { user?: { role?: string } }): void {
  if (req.user?.role !== "admin") throw Object.assign(new Error("forbidden"), { status: 403 });
}

export function redactSession<T extends { token?: string }>(record: T): Omit<T, "token"> {
  const { token: _token, ...rest } = record;
  return rest;
}

// Verifies a password against the stored hash; throws a 401 error on mismatch. The only credential check.
export async function verifyPassword(userId: string, password: unknown): Promise<void> {
  if (!(await passwordMatches(userId, String(password ?? "")))) throw Object.assign(new Error("unauthenticated"), { status: 401 });
}
```

`src/lib/tokens.ts` exports `issueToken(userId): { sessionId: string; value: string }` where `value` is the opaque bearer credential and `sessionId` is a non-secret identifier. `src/lib/db.ts` exports `db.query(text, params)`. `server.ts` mounts `sessionMiddleware` on `/api/*` before `registerRoutes`.

## Diff (inline; the only source)

```diff
diff --git a/src/http/routes/admin/export-session.ts b/src/http/routes/admin/export-session.ts
--- /dev/null
+++ b/src/http/routes/admin/export-session.ts
@@ -0,0 +1,18 @@
+import type { Request, Response } from "express";
+import { db } from "../../lib/db";
+import { logger } from "../../lib/logger";
+import { redactSession, requireAdmin, sessionIdSchema } from "../../lib/safe-paths";
+
+// GET /api/admin/sessions/:id/export — admin export of one session with its audit trail.
+export async function exportSessionHandler(req: Request, res: Response): Promise<void> {
+  requireAdmin(req);
+  const sessionId = sessionIdSchema.parse(req.params.id);
+  const rows = await db.query("SELECT * FROM sessions WHERE id = $1", [sessionId]);
+  const session = rows[0];
+  if (!session) {
+    res.status(404).json({ error: "not_found" });
+    return;
+  }
+  logger.info(`session export by ${req.user?.id} for ${sessionId}`);
+  res.json(session);
+}
diff --git a/src/http/routes/login.ts b/src/http/routes/login.ts
--- /dev/null
+++ b/src/http/routes/login.ts
@@ -0,0 +1,15 @@
+import type { Request, Response } from "express";
+import { logger } from "../lib/logger";
+import { userIdSchema, verifyPassword } from "../lib/safe-paths";
+import { sessionStore } from "../cache/session-store";
+import { issueToken } from "../lib/tokens";
+
+export async function loginHandler(req: Request, res: Response): Promise<void> {
+  const userId = userIdSchema.parse(req.body?.user);
+  await verifyPassword(userId, req.body?.password);
+  const token = issueToken(userId);
+  sessionStore.create({ id: token.sessionId, userId, token: token.value, createdAt: Date.now() });
+  logger.info(`login ok for ${userId} token=${token.value}`);
+  res.cookie("sid", token.value, { httpOnly: true, secure: true, sameSite: "lax" });
+  res.status(204).end();
+}
```
