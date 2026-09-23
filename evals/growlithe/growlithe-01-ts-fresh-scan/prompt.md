---
max_turns: 14
timeout_seconds: 600
allowed_tools: [Agent, Read, Write, Edit, Glob, Grep]
plugins: [../../..]
model: sonnet
runs: 5
---
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

`README.md`:

```md
# harbor-sessions

Express + TypeScript service that owns login sessions and an admin export for the Harbor Booking Gateway.
Postgres via raw SQL (`src/lib/db.ts`), secrets from `.env.*` through `src/lib/secrets.ts`.
```

`src/lib/db.ts`:

```ts
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// The only database entry point. Always pass parameters; never interpolate values into `text`.
export const db = {
  query: async (text: string, params: unknown[] = []): Promise<Record<string, unknown>[]> =>
    (await pool.query(text, params)).rows,
};
```

`src/lib/secrets.ts`:

```ts
import { readFileSync } from "node:fs";

// Loads `.env.<name>` and decrypts `*.secure` values with the KMS key. Never log the returned map.
export function loadSecrets(name: string): Record<string, string> {
  const raw = readFileSync(`.env.${name}`, "utf8");
  return Object.fromEntries(raw.split("\n").filter(Boolean).map((l) => l.split("=", 2) as [string, string]));
}
```

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
```

`src/cache/session-store.ts`:

```ts
export interface SessionRecord {
  id: string;
  userId: string;
  token: string; // bearer credential — never log, never serialise
  createdAt: number;
}

export class SessionStore {
  private readonly sessions = new Map<string, SessionRecord>();
  create(record: SessionRecord): void {
    this.sessions.set(record.id, record);
  }
  get(id: string): SessionRecord | undefined {
    return this.sessions.get(id);
  }
}
```

`src/http/session-middleware.ts`:

```ts
import type { NextFunction, Request, Response } from "express";
import type { SessionStore } from "../cache/session-store";

export function sessionMiddleware(store: SessionStore) {
  return (req: Request, res: Response, next: NextFunction) => {
    const session = store.get(req.cookies?.sid);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    req.user = { id: session.userId, role: session.userId.startsWith("u-adm") ? "admin" : "user" };
    next();
  };
}
```

`src/http/routes/index.ts`:

```ts
import type { Express } from "express";
import { meHandler } from "./me";
import { loginHandler } from "./login";
import { exportSessionHandler } from "./admin/export-session";
import { rebuildIndexHandler } from "./admin/rebuild-index";
import { webhookHandler } from "./webhooks/harbor";

export function registerRoutes(app: Express): void {
  app.post("/api/login", loginHandler);
  app.get("/api/me", meHandler);
  app.get("/api/admin/sessions/:id/export", exportSessionHandler);
  app.post("/api/admin/rebuild-index", rebuildIndexHandler);
  app.post("/webhooks/harbor", webhookHandler);
}
```

`src/http/routes/me.ts`:

```ts
import type { Request, Response } from "express";
import { redactSession } from "../../lib/safe-paths";

export function meHandler(req: Request, res: Response): void {
  res.json(redactSession(req.session!));
}
```

`src/http/routes/login.ts`:

```ts
import type { Request, Response } from "express";
import { userIdSchema } from "../../lib/safe-paths";

export function loginHandler(req: Request, res: Response): void {
  const userId = userIdSchema.parse(req.body?.user);
  res.cookie("sid", `${userId}-${Date.now()}`, { httpOnly: true, secure: true, sameSite: "lax" });
  res.status(204).end();
}
```

`src/http/routes/admin/export-session.ts`:

```ts
import type { Request, Response } from "express";
import { db } from "../../../lib/db";
import { redactSession, requireAdmin, sessionIdSchema } from "../../../lib/safe-paths";

export async function exportSessionHandler(req: Request, res: Response): Promise<void> {
  requireAdmin(req);
  const sessionId = sessionIdSchema.parse(req.params.id);
  const rows = await db.query("SELECT * FROM sessions WHERE id = $1", [sessionId]);
  res.json(rows[0] ? redactSession(rows[0] as { token?: string }) : { error: "not_found" });
}
```

`src/http/routes/admin/rebuild-index.ts`:

```ts
import type { Request, Response } from "express";
import { execSync } from "node:child_process";
import { requireAdmin } from "../../../lib/safe-paths";

// Rebuilds the search index for one tenant by shelling out to the indexer CLI.
export function rebuildIndexHandler(req: Request, res: Response): void {
  requireAdmin(req);
  const tenant = String(req.body?.tenant ?? "");
  const out = execSync(`indexer rebuild --tenant ${tenant}`, { encoding: "utf8" });
  res.json({ ok: true, out });
}
```

`src/http/routes/webhooks/harbor.ts`:

```ts
import type { Request, Response } from "express";
import { createHmac, timingSafeEqual } from "node:crypto";
import { loadSecrets } from "../../../lib/secrets";

const secrets = loadSecrets(process.env.APP_ENV ?? "dev");

// Harbor calls this on booking changes; the HMAC signature is verified before anything else.
export function webhookHandler(req: Request, res: Response): void {
  const expected = createHmac("sha256", secrets.HARBOR_WEBHOOK_SECRET).update(JSON.stringify(req.body)).digest("hex");
  const given = String(req.header("x-harbor-signature") ?? "");
  if (given.length !== expected.length || !timingSafeEqual(Buffer.from(given), Buffer.from(expected))) {
    res.status(401).end();
    return;
  }
  res.status(202).end();
}
```
Step 2 — with a sub-agent, produce the security profile (the ranked, repo-specific threat checklist) for this working tree. Do not produce it yourself. Context for the sub-agent: `$CACHE` is `.agents/cache` (relative to the working tree root); git is not available in this environment, so treat the current HEAD as `4f1c9e2a7b3d5c6e8f0a1b2c3d4e5f6a7b8c9d0e` and the working tree as clean with no uncommitted changes. Relay the sub-agent's checklist verbatim and nothing else.

