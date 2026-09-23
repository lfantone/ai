---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
model: sonnet
runs: 5
---
Verification scenario V2 failed and I need to know which implementation step to suspect. Do not redesign or rewrite the scenarios; answer with the suspect step id, the file, and a one-paragraph rationale.

Failed scenario and evidence:

```text
V2 · surface: api · mutating: yes · criterion: AC2
  pre: session s1 created via POST /api/login at X-Test-Now=0
  steps: 1. GET /api/me with cookie sid=s1 and X-Test-Now=5000  2. GET /api/me again with X-Test-Now=6000
  expect: second response body has lastSeenAt = 5000 (refreshed by the first request)
```

Actual: both responses returned 200, but `lastSeenAt` stayed `0` in both bodies. Server log shows `session evicted:` was never printed and no errors.

Execution log deviations: none; all four contracts applied as specified.

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
