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

Surfaces in play: cli only. There is no web UI and no HTTP API for this change; it is a Python batch step run inside a Docker container. Environment: local Docker stack, `docker compose exec worker <command>`, Redis at `redis:6379` inside the stack, mutating scenarios allowed (each scenario must clean up the Redis keys it creates).

## Acceptance criteria
- [ ] AC1 — `python -m pipeline.compact --stream orders` exits 0 and logs `compact: removed <n> entries` when the stream has acknowledged entries older than 24h.
- [ ] AC2 — When the stream has zero acknowledged entries, the command exits 0, logs `compact: nothing to do`, and the stream length (`XLEN orders`) is unchanged.
- [ ] AC3 — When Redis is unreachable, the command exits 2 and logs `compact: redis unavailable`, without creating the state key `pipeline:compact:last-run`.

## Change map
| Area | File(s) | New / Modify | Responsibility |
| --- | --- | --- | --- |
| Pipeline | `pipeline/compact.py` | New | CLI entry, XTRIM by age, state key write |
| Pipeline | `pipeline/redis_client.py` | Modify | connection timeout 2s, raise `RedisUnavailable` |

## Testing notes
- Unit tests mock Redis. Nothing exercises a real stream yet.
