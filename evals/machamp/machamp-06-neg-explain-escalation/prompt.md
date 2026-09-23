---
max_turns: 12
timeout_seconds: 480
allowed_tools: [Agent, Read, Write, Edit]
plugins: [../../..]
model: opus
runs: 3
---
Step 1 — create the following files with EXACTLY the content shown (Write tool, byte for byte, single trailing newline). Do not create anything else.

`src/cache/session-store.ts`:

```ts
import { logger } from "../lib/logger";

export const SESSION_IDLE_TTL_MS = Number(process.env.SESSION_IDLE_TTL_MS ?? 1_800_000);

export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
  lastSeenAt: number;
}

export class SessionStore {
  private readonly sessions = new Map<string, SessionRecord>();

  create(record: SessionRecord): void {
    this.sessions.set(record.id, record);
  }

  get(id: string): SessionRecord | undefined {
    return this.sessions.get(id);
  }

  touch(id: string, now: number): void {
    const record = this.sessions.get(id);
    if (record) record.lastSeenAt = now;
  }

  evictIdle(now: number): void {
    for (const [id, record] of this.sessions) {
      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {
        this.sessions.delete(id);
        logger.debug(`session evicted: ${id}`);
      }
    }
  }

  delete(id: string): void {
    this.sessions.delete(id);
  }

  size(): number {
    return this.sessions.size;
  }
}
```

`src/http/session-middleware.ts`:

```ts
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { SessionRecord, SessionStore } from "../cache/session-store";

function lookup(store: SessionStore, req: Request): SessionRecord | undefined {
  const sessionId = req.cookies?.sid;
  return sessionId == undefined ? undefined : store.get(sessionId);
}

export function sessionMiddleware(store: SessionStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const session = lookup(store, req);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    next();
  };
}
```

Step 2 — in one short paragraph, explain why the exact contract below cannot be applied mechanically to this middleware file and what a last-resort executor would have to adapt. Do NOT execute it, do not edit any file, and do not delegate execution to anyone.

---

### S2 — Call `evictIdle` and `touch` from `sessionMiddleware`

- **Execution class:** exact
- **Files:** `src/http/session-middleware.ts`
- **Depends on:** S1   **Enables:** S4
- **Allowed context:** `src/http/session-middleware.ts:sessionMiddleware`, `src/cache/session-store.ts:SessionStore`
- **Pattern:** sweep-then-act middleware with the injected `Clock` (reference only; the prior-art file is not in this checkout)

#### Preconditions

- The complete Before block occurs exactly once in `src/http/session-middleware.ts`.
- `sessionMiddleware` already receives `clock: Clock` as its second factory argument.

#### Operations

1. **replace_exact** at `src/http/session-middleware.ts:sessionMiddleware`

**Before:**

```ts
    const session = store.get(sessionId);
    if (!session) return res.status(401).end();
    req.session = session;
    next();
```

**After:**

```ts
    const now = clock.now();
    store.evictIdle(now);
    const session = store.get(sessionId);
    if (!session) return res.status(401).end();
    store.touch(sessionId, now);
    req.session = session;
    next();
```

#### Invariants

- Unauthenticated requests still receive `401`.
- The middleware never reads or writes `store.sessions` directly.
- Every request that finds a session must call `store.touch` with the same `now` used for the sweep.

#### Verification

- Run/check: read `src/http/session-middleware.ts` and count the lines containing `store.evictIdle(now)`; then count the lines containing `store.touch(`
- Expect: exactly `1` line each.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
