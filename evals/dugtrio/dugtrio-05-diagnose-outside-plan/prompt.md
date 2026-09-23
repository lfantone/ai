---
max_turns: 12
timeout_seconds: 300
allowed_tools: [Agent, Read, Write, Edit, Glob, Grep]
plugins: [../../..]
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
    const now = clock.now();
    store.evictIdle(now);
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    store.touch(sessionId, now);
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
Step 2 — a verification scenario failed. With a sub-agent, diagnose the cause: which plan step and file(s) are the suspect, with a one-line cause hypothesis (100 words maximum for the whole return). Do not diagnose it yourself and do not fix anything. Relay the sub-agent's return verbatim and nothing else.

---

Failed scenario:

```text
V2 · surface: api · mutating: yes · criterion: AC2
  pre: session s1 created at X-Test-Now=0
  steps: 1. GET /api/me with sid=s1 at X-Test-Now=5000  2. GET /api/me again at X-Test-Now=6000
  expect: the second response body has lastSeenAt = 5000
```

Evidence: both responses are 200 with body `{ "sessionId": "s1", "userId": "u1" }`; there is no `lastSeenAt` field in either body at all. A REPL read of the store after step 1 shows `lastSeenAt === 5000` on the record, so the store IS being refreshed.

Plan change map:

| Area | File(s) | New / Modify | Responsibility |
| --- | --- | --- | --- |
| Cache | `src/cache/session-store.ts` | Modify | S1: `lastSeenAt`, `touch`, `evictIdle`, TTL const |
| HTTP | `src/http/session-middleware.ts` | Modify | S2: call `evictIdle` + `touch` per request |
| Tests | `src/cache/__tests__/session-store.test.ts` | New | S3: store tests |

Execution-log deviations: none; S1, S2 and S3 applied as specified.
