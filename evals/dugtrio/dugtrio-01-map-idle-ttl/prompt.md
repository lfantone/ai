---
max_turns: 12
timeout_seconds: 300
allowed_tools: [Agent, Read, Write, Edit, Glob, Grep]
model: sonnet
runs: 5
---
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

`src/lib/clock.ts`:

```ts
export interface Clock {
  now(): number;
}

export const systemClock: Clock = { now: () => Date.now() };
```

`src/lib/logger.ts`:

```ts
export const logger = {
  debug: (msg: string): void => console.debug(msg),
  info: (msg: string): void => console.info(msg),
  warn: (msg: string): void => console.warn(msg),
};
```

`src/cache/session-store.ts`:

```ts
import { logger } from "../lib/logger";

export interface SessionRecord {
  id: string;
  userId: string;
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

  delete(id: string): void {
    this.sessions.delete(id);
  }

  size(): number {
    return this.sessions.size;
  }
}
```

`src/cache/rate-limit-store.ts`:

```ts
import { logger } from "../lib/logger";

export const RATE_LIMIT_WINDOW_MS = Number(process.env.RATE_LIMIT_WINDOW_MS ?? 60_000);

interface Bucket {
  count: number;
  windowStartedAt: number;
}

export class RateLimitStore {
  private readonly buckets = new Map<string, Bucket>();

  hit(key: string, now: number): number {
    const bucket = this.buckets.get(key) ?? { count: 0, windowStartedAt: now };
    bucket.count += 1;
    this.buckets.set(key, bucket);
    return bucket.count;
  }

  // Lookup-time sweep: callers pass `now` from the injected Clock; never Date.now() here.
  sweep(now: number): void {
    for (const [key, bucket] of this.buckets) {
      if (now - bucket.windowStartedAt > RATE_LIMIT_WINDOW_MS) {
        this.buckets.delete(key);
        logger.debug(`rate-limit bucket expired: ${key}`);
      }
    }
  }
}
```

`src/http/session-middleware.ts`:

```ts
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { SessionStore } from "../cache/session-store";

export function sessionMiddleware(store: SessionStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const sessionId = req.cookies?.sid;
    if (sessionId == undefined) return res.status(401).json({ error: "unauthenticated" });
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    next();
  };
}
```

`src/http/rate-limit-middleware.ts`:

```ts
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { RateLimitStore } from "../cache/rate-limit-store";

const MAX_PER_WINDOW = 20;

export function rateLimitMiddleware(store: RateLimitStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const now = clock.now();
    store.sweep(now);
    const count = store.hit(req.ip ?? "unknown", now);
    if (count > MAX_PER_WINDOW) return res.status(429).json({ error: "rate_limited" });
    next();
  };
}
```

`src/http/routes/me.ts`:

```ts
import type { Request, Response } from "express";

// Serialises the session record for GET /api/me. Only these two fields are exposed on purpose.
export function meHandler(req: Request, res: Response): void {
  const { id, userId } = req.session!;
  res.json({ sessionId: id, userId });
}
```

`src/cache/__tests__/rate-limit-store.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { RATE_LIMIT_WINDOW_MS, RateLimitStore } from "../rate-limit-store";

describe("RateLimitStore", () => {
  it("expires a bucket after the window", () => {
    const store = new RateLimitStore();
    store.hit("1.2.3.4", 0);
    store.sweep(RATE_LIMIT_WINDOW_MS + 1);
    expect(store.hit("1.2.3.4", RATE_LIMIT_WINDOW_MS + 2)).toBe(1);
  });
});
```
Step 2 — with a sub-agent, map where the change described in the requirement brief below lands in this codebase. Do not do the mapping yourself. Relay the sub-agent's brief verbatim and nothing else. The brief cites `file:symbol` locations and names patterns; it never pastes file bodies. It has exactly these four sections: **Insertion points**, **Prior art to mirror**, **Seams & extension points**, **Collisions**.

---

**Goal** — Sessions abandoned without logout live forever in the in-memory `SessionStore`; add an idle TTL so a session not touched for `SESSION_IDLE_TTL_MS` is evicted on the next request and every authenticated request refreshes its `lastSeenAt`.

**Acceptance criteria**
- AC1 — A session whose `lastSeenAt` is older than `SESSION_IDLE_TTL_MS` is evicted by the next request through `sessionMiddleware` and a debug log line `session evicted: <id>` is emitted.
- AC2 — Each request that passes `sessionMiddleware` updates the session's `lastSeenAt` to the current clock value.
- AC3 — Sessions touched within the TTL window are returned unchanged.
- AC4 — `SESSION_IDLE_TTL_MS` defaults to `1800000` when unset.

**Scope** — `SessionStore`, `sessionMiddleware`, and their tests.

**Out of scope** — Persisting sessions across restarts; an admin endpoint to list sessions.

**Constraints** — Library code takes an injected `Clock`, never `Date.now()`; logging goes through `logger`; `SessionStore` is the only owner of the session map.
