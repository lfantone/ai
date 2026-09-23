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

### S8 — Sweep idle sessions on every request

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: none / none
- Allowed context: `src/cache/session-store.ts:SessionStore`, `src/http/session-middleware.ts:sessionMiddleware`
- Pattern: none cited
- Preconditions: `SessionStore` has no `evictIdle` method.
- Target state: `SessionStore` has `evictIdle(now: number): void` that deletes records idle longer than 30 minutes, AND `sessionMiddleware` calls `store.evictIdle(clock.now())` before looking the session up, so idle sessions are gone on the next request.
- Instructions:
  1. Add `lastSeenAt: number` to `SessionRecord` and `evictIdle(now)` to `SessionStore`.
  2. Make the middleware call `store.evictIdle(clock.now())` at the start of each request.
- Invariants: no other file modified beyond Files.
- Verification: read `src/http/session-middleware.ts` and count the lines containing `evictIdle`; expect exactly `1` line.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
