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

  revoke(id: string): void {
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

### S5 — Log every session deletion

- **Execution class:** exact
- **Files:** `src/cache/session-store.ts`
- **Depends on:** none   **Enables:** none
- **Allowed context:** `src/cache/session-store.ts:SessionStore.delete`
- **Pattern:** `src/cache/rate-limit-store.ts:RateLimitStore.clear`

#### Preconditions

- The complete Before block occurs exactly once in `src/cache/session-store.ts`.
- `logger` is already imported at the top of `src/cache/session-store.ts`.

#### Operations

1. **replace_exact** at `src/cache/session-store.ts:SessionStore.delete`

**Before:**

```ts
    this.sessions.delete(id);
  }
```

**After:**

```ts
    this.sessions.delete(id);
    logger.debug(`session deleted: ${id}`);
  }
```

#### Invariants

- No method signature changes.

#### Verification

- Run/check: read `src/cache/session-store.ts` and count the lines containing `session deleted`
- Expect: exactly `1` line.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
