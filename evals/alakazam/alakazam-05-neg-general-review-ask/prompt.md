---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Agent]
model: opus
runs: 3
---
Summarize in five bullets what this diff changes, for the PR description. Do not review it for security or quality, and do not produce findings.

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
+  res.json(redactSession(session));
+}
diff --git a/src/http/routes/index.ts b/src/http/routes/index.ts
--- a/src/http/routes/index.ts
+++ b/src/http/routes/index.ts
@@ -1,7 +1,9 @@
 import type { Express } from "express";
 import { meHandler } from "./me";
+import { exportSessionHandler } from "./admin/export-session";
 
 // server.ts mounts sessionMiddleware on /api/* (populating req.user) before calling registerRoutes.
 export function registerRoutes(app: Express): void {
   app.get("/api/me", meHandler);
+  app.get("/api/admin/sessions/:id/export", exportSessionHandler);
 }
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
+  logger.info(`login ok for ${userId}`);
+  res.cookie("sid", token.value, { httpOnly: true, secure: true, sameSite: "lax" });
+  res.status(204).end();
+}
```
