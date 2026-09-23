---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
plugins: [../../..]
model: sonnet
runs: 5
---
Which steps of this implementation plan can run at the same time, and which must wait? Answer from the execution plan; do not verify the plan.

---

# Implementation Plan — TK-412 · Expire idle sessions in the token cache

_generated: 2026-09-18 · ticket: TK-412 · author: Mew · mode: precise · status: draft · head: 4f1c9e2a7b3d5c6e8f0a1b2c3d4e5f6a7b8c9d0e_

## 1. Objective

- **Problem / goal.** `SessionStore` keeps every session in memory until logout. Sessions
  abandoned without logout live forever, so the cache grows unbounded on long-running
  instances. Add an idle TTL: a session not touched for `SESSION_IDLE_TTL_MS` is evicted on
  the next request through `sessionMiddleware`, and every authenticated request refreshes
  the session's `lastSeenAt`.
- **Acceptance criteria (observable behavior).**
  - [ ] AC1 — A session whose `lastSeenAt` is older than `SESSION_IDLE_TTL_MS` is evicted
        by the next request through `sessionMiddleware` (absent from the store afterwards)
        and a `debug` log line `session evicted: <id>` is emitted.
  - [ ] AC2 — Each request that passes `sessionMiddleware` updates the session's
        `lastSeenAt` to the current clock value.
  - [ ] AC3 — Sessions touched within the TTL window are returned unchanged.
  - [ ] AC4 — `SESSION_IDLE_TTL_MS` defaults to `1800000` (30 min) when unset.
- **Out of scope.** Persisting sessions across restarts; sliding vs. absolute expiry
  configuration; admin endpoint to list sessions.

## 2. Context & constraints

- Conventions: TypeScript strict mode, `vitest` for tests, injected `Clock` interface
  (`src/lib/clock.ts:Clock`) instead of `Date.now()` in library code.
- Logging goes through `src/lib/logger.ts:logger` (`debug`/`info`/`warn`).
- Safe path: `SessionStore` is the only owner of the session map; middleware must go
  through its methods and never touch the map directly.
- Security profile: session ids are opaque; never log tokens, only ids.

## 3. Design overview

- Add `lastSeenAt` to `SessionRecord`, an `evictIdle(now)` sweep and a `touch(id, now)`
  refresh on `SessionStore`. Middleware calls `evictIdle` then `touch` on every request.
- Rejected: a background timer (adds lifecycle management; lookup-time eviction is enough
  at current traffic), and a `Map` subclass with expiring entries (hides the safe path).

## 4. Change map

| Area       | File(s)                                          | New / Modify | Responsibility                                |
| ---------- | ------------------------------------------------ | ------------ | --------------------------------------------- |
| Cache      | `src/cache/session-store.ts`                     | Modify       | `lastSeenAt`, `touch`, `evictIdle`, TTL const |
| HTTP       | `src/http/session-middleware.ts`                 | Modify       | call `evictIdle` + `touch` per request        |
| Tests      | `src/cache/__tests__/session-store.test.ts`      | New          | store eviction/touch/default TTL              |
| Tests      | `src/http/__tests__/session-middleware.test.ts`  | New          | middleware refreshes `lastSeenAt`             |

## 5. Task checklist

- [ ] S1 — Add `lastSeenAt`, `touch`, `evictIdle` and the TTL constant to `SessionStore`
- [ ] S2 — Call `evictIdle` and `touch` from `sessionMiddleware`
- [ ] S3 — Store tests: eviction, touch refresh, default TTL
- [ ] S4 — Middleware tests: `lastSeenAt` refreshed per request

## 6. Execution plan

- **Wave 1:** S1
- **Wave 2:** S2, S3
- **Wave 3:** S4

Dependency edges:

```
S1 → S2
S1 → S3
S2 → S4
```

Critical path: `S1 → S2 → S4`. Max concurrency: 2.

## 7. Implementation contracts

### S1 — Add `lastSeenAt`, `touch`, `evictIdle` and the TTL constant to `SessionStore`

- **Execution class:** exact
- **Files:** `src/cache/session-store.ts`
- **Depends on:** none   **Enables:** S2, S3
- **Allowed context:** `src/cache/session-store.ts:SessionRecord`,
  `src/cache/session-store.ts:SessionStore`, `src/lib/clock.ts:Clock`,
  `src/lib/logger.ts:logger`
- **Pattern:** `src/cache/rate-limit-store.ts:RateLimitStore.sweep` (lookup-time sweep with
  injected clock)

#### Preconditions

- The complete Before block of operation 1 occurs exactly once in
  `src/cache/session-store.ts`.
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

#### Invariants

- `SessionStore.create` and `SessionStore.delete` signatures are unchanged.
- No other file is modified.

#### Verification

- Run: `npx tsc --noEmit -p .`
- Expect: exit code `0`.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.

### S2 — Call `evictIdle` and `touch` from `sessionMiddleware`

- **Execution class:** exact
- **Files:** `src/http/session-middleware.ts`
- **Depends on:** S1   **Enables:** S4
- **Allowed context:** `src/http/session-middleware.ts:sessionMiddleware`,
  `src/cache/session-store.ts:SessionStore`, `src/lib/clock.ts:Clock`
- **Pattern:** `src/http/rate-limit-middleware.ts:rateLimitMiddleware` (sweep-then-act with
  injected clock)

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

- Unauthenticated requests still receive `401` with an empty body.
- The middleware never reads or writes `store.sessions` directly.

#### Verification

- Run: `npx tsc --noEmit -p .`
- Expect: exit code `0`.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.

### S3 — Store tests: eviction, touch refresh, default TTL

- **Execution class:** exact
- **Files:** `src/cache/__tests__/session-store.test.ts`
- **Depends on:** S1   **Enables:** none
- **Allowed context:** `src/cache/session-store.ts:SessionStore`,
  `src/cache/__tests__/rate-limit-store.test.ts` (fixture style)
- **Pattern:** `src/cache/__tests__/rate-limit-store.test.ts` (fake clock via
  `{ now: () => t }`)

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

- Run: `npx vitest run src/cache/__tests__/session-store.test.ts`
- Expect: exit code `0`, 3 tests passed.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.

### S4 — Middleware tests: `lastSeenAt` refreshed per request

- **Execution class:** exact
- **Files:** `src/http/__tests__/session-middleware.test.ts`
- **Depends on:** S2   **Enables:** none
- **Allowed context:** `src/http/session-middleware.ts:sessionMiddleware`,
  `src/http/__tests__/rate-limit-middleware.test.ts` (request/response doubles)
- **Pattern:** `src/http/__tests__/rate-limit-middleware.test.ts`

#### Preconditions

- The path `src/http/__tests__/session-middleware.test.ts` does not exist.

#### Operations

1. **create_file** at `src/http/__tests__/session-middleware.test.ts`

**Content:**

```ts
import { describe, expect, it, vi } from "vitest";
import { SessionStore } from "../../cache/session-store";
import { sessionMiddleware } from "../session-middleware";

describe("sessionMiddleware", () => {
  it("refreshes lastSeenAt on every authenticated request", () => {
    const store = new SessionStore();
    store.create({ id: "s1", userId: "u1", createdAt: 0, lastSeenAt: 0 });
    const clock = { now: () => 5000 };
    const mw = sessionMiddleware(store, clock);
    const req = { cookies: { sid: "s1" } } as any;
    const res = { status: vi.fn().mockReturnThis(), end: vi.fn() } as any;
    const next = vi.fn();

    mw(req, res, next);

    expect(store.get("s1")?.lastSeenAt).toBe(5000);
    expect(next).toHaveBeenCalledOnce();
  });
});
```

#### Invariants

- No production file is modified.

#### Verification

- Run: `npx vitest run src/http/__tests__/session-middleware.test.ts`
- Expect: exit code `0`, 1 test passed.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.

## 8. Data / interface / schema changes

- `SessionRecord` gains `lastSeenAt: number`. `SessionStore` gains `touch(id, now)` and
  `evictIdle(now)`. New exported constant `SESSION_IDLE_TTL_MS`.

## 9. Testing plan

- AC1, AC3, AC4 → S3. AC2 → S4. Type check via `tsc` in S1 and S2.

## 10. Rollout / migration / feature flags

- No flag. Existing in-memory sessions are created fresh on deploy; nothing to migrate.

## 11. Extension points

- `evictIdle` is the seam for a future background sweep or a per-user TTL.

## 12. Risks & open questions

- Sweeping on every request is O(n) in live sessions; acceptable at current volume, revisit
  above ~50k concurrent sessions.
