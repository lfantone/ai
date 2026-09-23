---
max_turns: 12
timeout_seconds: 480
allowed_tools: [Agent, Read, Write, Edit]
model: opus
runs: 3
---
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

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

Step 2 — execute the contract below with a sub-agent. Do not execute it yourself and do not edit the files after Step 1. Conventions for the executor: no commits, current branch, touch only the contract's Files, perform the Verification by reading the file. Relay the sub-agent's return verbatim and nothing else: one line per operation, then exactly one verdict line, which is either `OK — S<N> done` or `failed: <precise reason>`, then a `Deviations:` list detailing how execution differed from the contract (write `Deviations: none` if there were none).

---

**Escalation context (approved by the user).** Machoke returned `PRECONDITION_FAILED: SessionStore has no method named sweep`. The user confirmed the contract author meant the existing eviction method (it is called `evictIdle` in this file) and approved escalation: complete the intent against the method that actually performs the eviction, stay inside Files, and record the name mismatch under Deviations. If the intent cannot be met inside Files, fail with a precise reason.

### S5 — Log evictions with the tenant id

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: S1 / none
- Allowed context: `src/cache/session-store.ts:SessionStore`
- Pattern: none cited
- Preconditions: `SessionStore.sweep(now)` exists and logs `session evicted: <id>` on each eviction.
- Target state: the eviction log line reads `session evicted: <id> (user <userId>)`, nothing else changes.
- Instructions:
  1. In `SessionStore.sweep`, extend the `logger.debug` call to include the record's `userId` in the format above.
- Invariants: method signatures unchanged; no other log lines change.
- Verification: read `src/cache/session-store.ts` and count the lines containing `(user ${record.userId})`; expect exactly `1` line.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
