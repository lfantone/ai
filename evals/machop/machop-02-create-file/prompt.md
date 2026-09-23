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

### S3 — Store tests: eviction, touch refresh, default TTL

- **Execution class:** exact
- **Files:** `src/cache/__tests__/session-store.test.ts`
- **Depends on:** S1   **Enables:** none
- **Allowed context:** `src/cache/session-store.ts:SessionStore`
- **Pattern:** `src/cache/__tests__/rate-limit-store.test.ts`

#### Preconditions

- The path `src/cache/__tests__/session-store.test.ts` does not exist.

#### Operations

1. **create_file** at `src/cache/__tests__/session-store.test.ts`

**Content:**

```ts
import { describe, expect, it, vi } from "vitest";
import { SESSION_IDLE_TTL_MS, SessionStore } from "../session-store";
import { logger } from "../../lib/logger";

const record = (id: string, lastSeenAt: number) => ({
  id,
  userId: `u-${id}`,
  createdAt: lastSeenAt,
  lastSeenAt,
});

describe("SessionStore idle eviction", () => {
  it("evicts a session idle longer than the TTL and logs its id", () => {
    const store = new SessionStore();
    const debug = vi.spyOn(logger, "debug");
    store.create(record("a", 0));
    store.evictIdle(SESSION_IDLE_TTL_MS + 1);
    expect(store.get("a")).toBeUndefined();
    expect(debug).toHaveBeenCalledWith("session evicted: a");
  });

  it("keeps a session touched within the TTL", () => {
    const store = new SessionStore();
    store.create(record("b", 0));
    store.touch("b", 1000);
    store.evictIdle(SESSION_IDLE_TTL_MS + 500);
    expect(store.get("b")?.lastSeenAt).toBe(1000);
  });

  it("defaults the TTL to 30 minutes", () => {
    expect(SESSION_IDLE_TTL_MS).toBe(1_800_000);
  });
});
```

#### Invariants

- No production file is modified.

#### Verification

- Run/check: read `src/cache/__tests__/session-store.test.ts` and count the lines containing `it(`
- Expect: exactly `3` lines.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
