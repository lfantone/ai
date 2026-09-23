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

There is no plan artifact for this one. Surfaces in play: api. Environment: local, the service runs with `docker compose up` (service `api` on http://localhost:8080, service `db` is Postgres).

Expectation, as described by the developer: "`GET /health` should return 200 with a JSON body `{ "status": "ok", "version": "<semver>" }` where version matches the `version` field in package.json. If the database is unreachable it should instead return 503 with `{ "status": "degraded", "checks": { "db": "down" } }`, and it must answer within 2 seconds either way."
