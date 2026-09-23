---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Agent]
plugins: [../../..]
model: opus
runs: 3
---
Review this pull request delta with a sub-agent: correctness, ticket coverage, and repository conventions. Do not review it yourself. There is no checkout and no DIFF_PATH in this environment; the full diff is inline in the brief and is the only source. Return the sub-agent's output verbatim and nothing else. It must start with a `## Ticket coverage` section (one line per acceptance criterion: covered / partial / MISSING) and then give findings, each as its own block:

````text
### [<must-fix|recommended|cosmetic>] <short title> — <file>:<new-file line(s)>
**Anchor:** `<verbatim line copied from the + side of the diff>`
**What's wrong:** <1–2 sentences>

```suggestion
<replacement lines only>
```
````

Empty severity buckets are written as `_None._`. Findings must anchor to lines the diff adds or modifies; an omitted acceptance criterion is reported with location `(not in diff — missing)` and a `(not inline — sketch)` suggestion.

---

## Ticket brief
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

## Implementation brief
PR #88 "TK-412: expire idle sessions" — 4 file(s) changed.
- `src/cache/session-store.ts` — TTL constant, `lastSeenAt`, `touch`, `evictIdle`
- `src/http/session-middleware.ts` — call `evictIdle` and `touch` per request
- `src/cache/__tests__/session-store.test.ts` — store tests
- `src/http/__tests__/session-middleware.test.ts` — middleware tests

## Repository brief (excerpt)
- TypeScript strict mode, Express, vitest. Prettier formatting enforced in CI.
- **Hard rule:** `Date.now()` is forbidden outside `src/lib/clock.ts`. Library code gets the current time either from an injected `Clock` (`src/lib/clock.ts:Clock`, `clock.now(): number`) or as a `now: number` argument supplied by a caller that holds the clock; both forms are compliant.
- The TTL constant is resolved once at module load on purpose (the process is restarted on config change); do not flag that as an issue.
- Logging goes through `src/lib/logger.ts:logger` (`debug`/`info`/`warn`); `console.*` is not used in `src/`.
- Safe path: `SessionStore` is the only owner of the session map; middleware must go through its methods.
- Tests live next to the code under `__tests__/`, one `describe` per unit.

## COORDS
owner/repo: acme/app · PR index: 88 · head_sha: 7d3f1a2c9b8e4f5061728394a5b6c7d8e9f0a1b2 · base_ref: main

## Diff (inline; the only source)

```diff
diff --git a/src/cache/session-store.ts b/src/cache/session-store.ts
--- a/src/cache/session-store.ts
+++ b/src/cache/session-store.ts
@@ -1,24 +1,42 @@
 import { logger } from "../lib/logger";
+
+const parsedIdleTtlMs = Number(process.env.SESSION_IDLE_TTL_MS);
+export const SESSION_IDLE_TTL_MS =
+  Number.isFinite(parsedIdleTtlMs) && parsedIdleTtlMs > 0
+    ? parsedIdleTtlMs
+    : 1_800_000;
 
 export interface SessionRecord {
   id: string;
   userId: string;
   createdAt: number;
+  lastSeenAt: number;
 }
 
 export class SessionStore {
   private readonly sessions = new Map<string, SessionRecord>();
 
-  create(record: SessionRecord): void {
-    this.sessions.set(record.id, record);
+  create(record: Omit<SessionRecord, "lastSeenAt">): void {
+    this.sessions.set(record.id, { ...record, lastSeenAt: record.createdAt });
   }
 
   get(id: string): SessionRecord | undefined {
     return this.sessions.get(id);
   }
 
-  // TODO(TK-412): evict idle sessions here
-  // see docs/sessions.md for the intended TTL semantics
+  touch(id: string, now: number): void {
+    const record = this.sessions.get(id);
+    if (record) record.lastSeenAt = now;
+  }
+
+  evictIdle(now: number): void {
+    for (const [id, record] of this.sessions) {
+      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {
+        this.sessions.delete(id);
+        logger.debug(`session evicted: ${id}`);
+      }
+    }
+  }
 
   delete(id: string): void {
     this.sessions.delete(id);
diff --git a/src/http/session-middleware.ts b/src/http/session-middleware.ts
--- a/src/http/session-middleware.ts
+++ b/src/http/session-middleware.ts
@@ -6,8 +6,11 @@
   return (req: Request, res: Response, next: NextFunction) => {
     const sessionId = req.cookies?.sid;
     if (sessionId == undefined) return res.status(401).json({ error: "unauthenticated" });
+    const now = clock.now();
+    store.evictIdle(now);
     const session = store.get(sessionId);
     if (!session) return res.status(401).json({ error: "unauthenticated" });
+    store.touch(sessionId, now);
     req.session = session;
     next();
   };
diff --git a/src/cache/__tests__/session-store.test.ts b/src/cache/__tests__/session-store.test.ts
--- /dev/null
+++ b/src/cache/__tests__/session-store.test.ts
@@ -0,0 +1,40 @@
+import { afterEach, describe, expect, it, vi } from "vitest";
+import { SESSION_IDLE_TTL_MS, SessionStore } from "../session-store";
+import { logger } from "../../lib/logger";
+
+const record = (id: string, createdAt: number) => ({
+  id,
+  userId: `u-${id}`,
+  createdAt,
+});
+
+afterEach(() => {
+  vi.restoreAllMocks();
+  vi.unstubAllEnvs();
+});
+
+describe("SessionStore idle eviction", () => {
+  it("evicts a session idle longer than the TTL and logs its id", () => {
+    const store = new SessionStore();
+    const debug = vi.spyOn(logger, "debug");
+    store.create(record("a", 0));
+    store.evictIdle(SESSION_IDLE_TTL_MS + 1);
+    expect(store.get("a")).toBeUndefined();
+    expect(debug).toHaveBeenCalledWith("session evicted: a");
+  });
+
+  it("keeps a session touched within the TTL", () => {
+    const store = new SessionStore();
+    store.create(record("b", 0));
+    store.touch("b", 1000);
+    store.evictIdle(SESSION_IDLE_TTL_MS + 500);
+    expect(store.get("b")?.lastSeenAt).toBe(1000);
+  });
+
+  it("falls back to the default when the env var is empty", async () => {
+    vi.stubEnv("SESSION_IDLE_TTL_MS", "");
+    vi.resetModules();
+    const fresh = await import("../session-store");
+    expect(fresh.SESSION_IDLE_TTL_MS).toBe(1_800_000);
+  });
+});
diff --git a/src/http/__tests__/session-middleware.test.ts b/src/http/__tests__/session-middleware.test.ts
--- /dev/null
+++ b/src/http/__tests__/session-middleware.test.ts
@@ -0,0 +1,35 @@
+import { describe, expect, it, vi } from "vitest";
+import { SessionStore } from "../../cache/session-store";
+import { sessionMiddleware } from "../session-middleware";
+
+describe("sessionMiddleware", () => {
+  it("refreshes lastSeenAt on every authenticated request", () => {
+    const store = new SessionStore();
+    store.create({ id: "s1", userId: "u1", createdAt: 0 });
+    const clock = { now: () => 5000 };
+    const mw = sessionMiddleware(store, clock);
+    const req = { cookies: { sid: "s1" } } as any;
+    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;
+    const next = vi.fn();
+
+    mw(req, res, next);
+
+    expect(store.get("s1")?.lastSeenAt).toBe(5000);
+    expect(next).toHaveBeenCalledOnce();
+  });
+
+  it("returns 401 for a session evicted by the sweep", () => {
+    const store = new SessionStore();
+    store.create({ id: "old", userId: "u2", createdAt: 0 });
+    const clock = { now: () => 10_000_000 };
+    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;
+    const next = vi.fn();
+
+    const mw = sessionMiddleware(store, clock);
+    mw({ cookies: { sid: "old" } } as any, res, next);
+
+    expect(res.status).toHaveBeenCalledWith(401);
+    expect(next).not.toHaveBeenCalled();
+    expect(store.get("old")).toBeUndefined();
+  });
+});
```
