---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
plugins: [../../..]
model: sonnet
runs: 5
---
Design the verification scenarios for the change described below with a sub-agent. Do not design them yourself and do not look for the repository; the brief is the only input. Return the sub-agent's checklist verbatim and nothing else. Each scenario must use exactly this shape:

```text
V1 · surface: web · mutating: no · criterion: <which>
  pre: <preconditions, or none>
  steps: <numbered, concrete>
  expect: <observable result>
```

---

Surfaces in play: api (Express HTTP server). Environment: local dev server on http://localhost:3000, mutating scenarios allowed. Sessions are created with `POST /api/login` (body `{ "user": "<name>" }`, sets cookie `sid`) and inspected with `GET /api/me` (200 with `{ "userId", "lastSeenAt" }` for a live session; 401 with `{ "error": "unauthenticated" }` when the cookie is missing or the session is gone). Server debug logs are written to stdout. The server reads `SESSION_IDLE_TTL_MS` at startup. Test clock: the server honors an `X-Test-Now` header (epoch ms) when `NODE_ENV=test`.

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

## 4. Change map

| Area       | File(s)                                          | New / Modify | Responsibility                                |
| ---------- | ------------------------------------------------ | ------------ | --------------------------------------------- |
| Cache      | `src/cache/session-store.ts`                     | Modify       | `lastSeenAt`, `touch`, `evictIdle`, TTL const |
| HTTP       | `src/http/session-middleware.ts`                 | Modify       | call `evictIdle` + `touch` per request        |
| Tests      | `src/cache/__tests__/session-store.test.ts`      | New          | store eviction/touch/default TTL              |
| Tests      | `src/http/__tests__/session-middleware.test.ts`  | New          | middleware refreshes `lastSeenAt`             |

## 9. Testing plan

- AC1, AC3, AC4 → S3. AC2 → S4. Type check via `tsc` in S1 and S2.
