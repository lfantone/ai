---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
model: sonnet
runs: 5
---
List this plan's acceptance criteria as short bullets, one per criterion, in plain language. Do not design tests or verification steps.

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
