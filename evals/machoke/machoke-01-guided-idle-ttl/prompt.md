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

Step 2 — execute the contract below with a sub-agent. Do not execute it yourself and do not edit the files after Step 1. Conventions for the executor: no commits, current branch, touch only the contract's Files, read only its Allowed context, perform the Verification by reading the file and comparing the observed count to the expected value. Relay the sub-agent's return verbatim and nothing else: one line per operation or instruction, then exactly one verdict line, which is one of `OK`, `PRECONDITION_FAILED: <condition>`, `GUIDANCE_INSUFFICIENT: <missing decision>`, `VERIFICATION_FAILED: <observed result>`, or `CONTRACT_INVALID: <reason>`, then a `Deviations:` list (write `Deviations: none` if there are none).

---

### S1 — Add idle-TTL support to `SessionStore`

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: none / S2, S3
- Allowed context: `src/cache/session-store.ts:SessionRecord`, `src/cache/session-store.ts:SessionStore`
- Pattern: lookup-time sweep with a caller-supplied `now: number` (the repository's `RateLimitStore.sweep` uses the same shape; that file is not available here, follow the description)
- Preconditions: `SessionRecord` has exactly the fields `id`, `userId`, `createdAt`; `SessionStore` has no `touch` or `evictIdle` method; `logger` is imported at the top of the file.
- Target state: the module exports a numeric constant `SESSION_IDLE_TTL_MS` read from `process.env.SESSION_IDLE_TTL_MS` with default `1_800_000`; `SessionRecord` gains a required `lastSeenAt: number`; `SessionStore` gains `touch(id: string, now: number): void` (sets `lastSeenAt` on an existing record, no-op otherwise) and `evictIdle(now: number): void` (deletes every record whose `now - lastSeenAt` exceeds the TTL and logs `session evicted: <id>` at debug level via `logger`).
- Instructions:
  1. Add the exported constant above the interface.
  2. Add the `lastSeenAt` field to `SessionRecord`.
  3. Add `touch` and `evictIdle` after `get`, in that order, using the injected `now` (never `Date.now()`).
  4. Keep `create`, `get`, `delete`, `size` unchanged.
- Invariants: `create`, `get`, `delete`, `size` signatures unchanged; no `Date.now()` anywhere in the file; no other file modified.
- Verification: read `src/cache/session-store.ts` and count the lines containing `lastSeenAt`; expect exactly `3` lines.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
