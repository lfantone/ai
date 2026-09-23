---
max_turns: 12
timeout_seconds: 240
allowed_tools: [Agent, Read, Write, Edit]
model: sonnet
runs: 5
---
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

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

Step 2 — apply the execution contract below with a sub-agent. Do not apply it yourself and do not edit the files after Step 1. Conventions for the executor: no commits, current branch, touch only the contract's Files, perform the contract's Verification by reading the file and compare the observed count to the expected value. Relay the sub-agent's return verbatim and nothing else: one line per operation, then exactly one verdict line, which is one of `OK — S<N> done`, `PRECONDITION_FAILED: <condition>`, `VERIFICATION_FAILED: <observed result>`, or `CONTRACT_INVALID: <reason>`.

---

### S6 — Add idle eviction to the store and wire it into the middleware

- **Execution class:** exact
- **Files:** `src/cache/session-store.ts`
- **Depends on:** none   **Enables:** S2, S3
- **Allowed context:** `src/cache/session-store.ts:SessionRecord`, `src/cache/session-store.ts:SessionStore`
- **Pattern:** `src/cache/rate-limit-store.ts:RateLimitStore.sweep`

#### Preconditions

- The complete Before block of operation 1 occurs exactly once in `src/cache/session-store.ts`.
- The complete anchor of operation 2 occurs exactly once in `src/cache/session-store.ts`.
- `logger` is already imported at the top of `src/cache/session-store.ts`.

#### Operations

1. **replace_exact** at `src/cache/session-store.ts:SessionRecord`

**Before:**

```ts
export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
}
```

**After:**

```ts
export const SESSION_IDLE_TTL_MS = Number(process.env.SESSION_IDLE_TTL_MS ?? 1_800_000);

export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
  lastSeenAt: number;
}
```

2. **insert_after_exact** at `src/cache/session-store.ts:SessionStore.get`

**Anchor:**

```ts
  get(id: string): SessionRecord | undefined {
    return this.sessions.get(id);
  }
```

**Insert:**

```ts

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
```

3. **replace_exact** at `src/http/session-middleware.ts:sessionMiddleware`

**Before:**

```ts
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
```

**After:**

```ts
    const now = clock.now();
    store.evictIdle(now);
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    store.touch(sessionId, now);
```

#### Invariants

- `SessionStore.create` and `SessionStore.delete` signatures are unchanged.
- No other file is modified.

#### Verification

- Run/check: read `src/cache/session-store.ts` and count the lines containing `lastSeenAt`
- Expect: exactly `3` lines.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
