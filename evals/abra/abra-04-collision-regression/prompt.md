---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
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

Surfaces in play: api (http://localhost:3000, local, mutating allowed) and cli (the `sessions` admin tool, run as `npm run sessions -- <args>` from the repo root). Sessions are created with `POST /api/login` (body `{ "user": "<name>" }`, sets cookie `sid`) and inspected with `GET /api/me` (200 for a live session, 401 `{ "error": "unauthenticated" }` otherwise). Test clock: with `NODE_ENV=test` the server honours an `X-Test-Now` header (epoch ms) and the CLI honours a `SESSIONS_NOW` environment variable (epoch ms), so a session can be made idle by advancing the clock rather than waiting.

## Acceptance criteria
- [ ] AC1 — `npm run sessions -- prune` deletes every session idle longer than `SESSION_IDLE_TTL_MS`, prints `pruned <n> sessions` and exits 0.
- [ ] AC2 — `npm run sessions -- prune --dry-run` prints the same count but deletes nothing and exits 0.
- [ ] AC3 — After a prune, `GET /api/me` with a pruned session cookie returns 401; with a live session it still returns 200.

## Change map
| Area | File(s) | New / Modify | Responsibility |
| --- | --- | --- | --- |
| CLI | `src/cli/sessions.ts` | New | `prune` command, `--dry-run` |
| HTTP | `src/http/session-middleware.ts` | Modify | expose `evictIdle` result count |
| HTTP | `src/http/rate-limit-middleware.ts` | Modify | **collision area:** shares the middleware chain and the `Clock` injection with session middleware; rate limiting (429 after 20 requests/min per IP) must be unaffected |

## Testing notes
- Unit tests exist for the prune counting logic. Rate limiting has an existing integration test that hits the endpoint 21 times.
