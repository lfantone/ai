#!/usr/bin/env python3
"""Regenerate the abra-* cases.

Case 01 derives its brief from the shared synthetic plan in ../../magneton/fixture/plan-TK-412.md
(sections 1, 4 and 9, exactly what the verify orchestrator injects). The other briefs are
inline below. Re-run after editing either.
"""
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
PLAN = (SUITE.parent / "magneton" / "fixture" / "plan-TK-412.md").read_text()


def section(md: str, number: int) -> str:
    m = re.search(rf"^## {number}\. .*?(?=^## \d+\. |\Z)", md, re.S | re.M)
    assert m, f"section {number} not found"
    return m.group(0).strip()


FRONT = """---
max_turns: 8
timeout_seconds: 480
allowed_tools: [Agent]
plugins: [../../..]
model: sonnet
runs: 5
---
"""

DESIGN = """Design the verification scenarios for the change described below with a sub-agent. Do not design them yourself and do not look for the repository; the brief is the only input. Return the sub-agent's checklist verbatim and nothing else. Each scenario must use exactly this shape:

```text
V1 · surface: web · mutating: no · criterion: <which>
  pre: <preconditions, or none>
  steps: <numbered, concrete>
  expect: <observable result>
```

---

"""


def replace_once(text: str, old: str, new: str) -> str:
    n = text.count(old)
    assert n == 1, f"expected exactly one match, found {n}: {old[:60]!r}"
    return text.replace(old, new)


def grader(case: Path, name: str, body: str) -> None:
    (case / "graders").mkdir(parents=True, exist_ok=True)
    (case / "graders" / f"{name}.md").write_text(body)


def regex(pattern: str, match: str = "contains", flags: str | None = None) -> str:
    fm = f"---\ntype: regex\ntarget: last_message\nmatch: {match}\n"
    if flags:
        fm += f"flags: {flags}\n"
    return fm + f"---\n{pattern}\n"


def llm(rubric: str) -> str:
    return f"---\ntype: llm\nfocus: last_message\n---\n{rubric.strip()}\n"


# Routing is a trajectory check, reported for visibility but kept out of Δ (with arm only,
# token weight; the runner rejects weight 0).
ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Abra\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Abra\nmin: 0\nmax: 0\narm: both\n---\n"

HEADER = r"^V\d+ · surface: (web|api|cli) · mutating: (yes|no) · criterion: \S"
LOOSE_HEADER = r"^V\d+\b(?! · surface: (web|api|cli) · mutating: (yes|no) · criterion: )"
VAGUE = r"expect:[^\n]*(works correctly|as expected|behaves (correctly|properly)|functions properly|should work|is correct\b)"

EXECUTABLE = """
The answer is a checklist of verification scenarios (V1, V2, ...). All claims must hold to pass.

1. Every `expect:` names something a driver can assert without judgment: an HTTP status code, a response field and value, visible text or UI state, an exit code, a stdout line, a log line, or a stored value. An expect such as "works correctly", "behaves as expected" or "the feature is applied" fails this claim. When the brief defines the exact status or text for a situation, an either/or hedge (such as "401/404") also fails this claim.
2. Steps are executable as written: api steps carry the HTTP method and path (and payload when there is a body); web steps carry the route and what to click or fill; cli steps carry the exact command.
3. Every `mutating:` flag matches the steps with respect to application data: a scenario that creates, updates or deletes data (POST/PUT/PATCH/DELETE, saving or deleting through the UI, a command that writes or may delete records, including a prune run without a dry-run flag) is `yes`; a pure read is `no`. Environment manipulation done in `pre:` (stopping or starting a service, setting a test clock header, restarting with a different env var) does not by itself decide the flag; either value is acceptable for it.
4. No scenario verifies a runtime criterion by reading or grepping source code text instead of exercising behavior.
5. The answer is the checklist only: no preamble beyond one short sentence, no explanation after it, no questions back.
"""


def fire_case(slug: str, brief: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + DESIGN + brief.strip() + "\n")
    grader(case, "strict-header-present", regex(HEADER, flags="m"))
    grader(case, "strict-no-loose-headers", regex(LOOSE_HEADER, match="not_contains", flags="m"))
    grader(case, "no-vague-expects", regex(VAGUE, match="not_contains", flags="i"))
    grader(case, "executable-and-observable", llm(EXECUTABLE))
    grader(case, "routed-to-abra", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def neg_case(slug: str, prompt: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt.strip() + "\n")
    grader(case, "no-scenario-checklist", regex(r"^V\d+ · surface:", match="not_contains", flags="m"))
    grader(case, "not-routed-to-abra", NOT_ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def covers(*ids: str) -> dict[str, str]:
    return {f"covers-{i.lower()}": regex(rf"criterion:[^\n]*\b{i}\b") for i in ids}


# ---------------------------------------------------------------- 01 — api, from the plan
brief_01 = f"""
Surfaces in play: api (Express HTTP server). Environment: local dev server on http://localhost:3000, mutating scenarios allowed. Sessions are created with `POST /api/login` (body `{{ "user": "<name>" }}`, sets cookie `sid`) and inspected with `GET /api/me` (200 with `{{ "userId", "lastSeenAt" }}` for a live session; 401 with `{{ "error": "unauthenticated" }}` when the cookie is missing or the session is gone). Server debug logs are written to stdout. The server reads `SESSION_IDLE_TTL_MS` at startup. Test clock: the server honors an `X-Test-Now` header (epoch ms) when `NODE_ENV=test`.

{section(PLAN, 1)}

{section(PLAN, 4)}

{section(PLAN, 9)}
"""
fire_case(
    "abra-01-api-session-ttl",
    brief_01,
    {
        **covers("AC1", "AC2", "AC3", "AC4"),
        "api-only": regex(r"surface: (web|cli)", match="not_contains"),
        "has-mutating-yes": regex(r"mutating: yes"),
    },
)

# ---------------------------------------------------------------- 02 — web, shared staging
brief_02 = """
Surfaces in play: web (React app). Environment: shared staging at https://staging.orders.example — other testers use it, so mutating scenarios are discouraged and must clean up after themselves. A test account `qa-filters@example.com` exists with 24 orders (8 status=shipped, 16 status=pending).

## Acceptance criteria
- [ ] AC1 — On `/orders`, choosing status=shipped and clicking "Save filter", then entering the name "Shipped only", shows a "Shipped only" entry in the left sidebar under "Saved filters".
- [ ] AC2 — Clicking a saved filter in the sidebar narrows the orders table to matching rows and the table header shows "8 orders".
- [ ] AC3 — Hovering a saved filter and clicking its trash icon removes it from the sidebar; the table returns to the unfiltered "24 orders" state.
- [ ] AC4 — With no saved filters, the sidebar section shows the text "No saved filters yet".

## Change map
| Area | File(s) | New / Modify | Responsibility |
| --- | --- | --- | --- |
| UI | `src/pages/Orders.tsx` | Modify | filter bar, "Save filter" button |
| UI | `src/components/SavedFilters.tsx` | New | sidebar list, delete icon, empty state |
| API client | `src/api/filters.ts` | New | `listFilters`, `createFilter`, `deleteFilter` |

## Testing notes
- Component tests cover the empty state and the delete confirmation. No end-to-end coverage exists yet.
"""
fire_case(
    "abra-02-web-saved-filters",
    brief_02,
    {
        **covers("AC1", "AC2", "AC3", "AC4"),
        "web-only": regex(r"surface: (api|cli)", match="not_contains"),
        "has-mutating-yes": regex(r"mutating: yes"),
        "has-mutating-no": regex(r"mutating: no"),
    },
)

# ---------------------------------------------------------------- 03 — no plan, described expectation
brief_03 = """
There is no plan artifact for this one. Surfaces in play: api. Environment: local, the service runs with `docker compose up` (service `api` on http://localhost:8080, service `db` is Postgres).

Expectation, as described by the developer: "`GET /health` should return 200 with a JSON body `{ "status": "ok", "version": "<semver>" }` where version matches the `version` field in package.json. If the database is unreachable it should instead return 503 with `{ "status": "degraded", "checks": { "db": "down" } }`, and it must answer within 2 seconds either way."
"""
fire_case(
    "abra-03-no-plan-health-endpoint",
    brief_03,
    {
        "covers-200": regex(r"\b200\b"),
        "covers-503": regex(r"\b503\b"),
        "api-only": regex(r"surface: (web|cli)", match="not_contains"),
        "db-down-precondition": llm("""
The answer is a checklist of verification scenarios for a /health endpoint. All claims must hold to pass.

1. There is a scenario for the healthy path expecting HTTP 200 and a body with `status` equal to `ok` and a `version` field (ideally compared against package.json).
2. There is a scenario for the degraded path expecting HTTP 503 and a body with `status` equal to `degraded` and `checks.db` equal to `down`.
3. The degraded scenario has an explicit `pre:` that makes the database unreachable in a concrete way (for example stopping the `db` compose service, or pointing the api at a wrong DB host) and, if it changes shared state, says how to restore it. A degraded scenario with `pre: none` fails this claim.
4. At least one scenario asserts the response time bound (answers within 2 seconds).
"""),
    },
)

# ---------------------------------------------------------------- 04 — collision area + two surfaces
brief_04 = """
Surfaces in play: api (http://localhost:3000, local, mutating allowed) and cli (the `sessions` admin tool, run as `npm run sessions -- <args>` from the repo root).

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
"""
fire_case(
    "abra-04-collision-regression",
    brief_04,
    {
        **covers("AC1", "AC2", "AC3"),
        "has-api-surface": regex(r"surface: api"),
        "has-cli-surface": regex(r"surface: cli"),
        "has-regression-scenario": regex(r"regression|collision", flags="i"),
        "uses-prune-command": regex(r"sessions -- prune"),
        "rate-limit-regression": llm("""
The answer is a checklist of verification scenarios. All claims must hold to pass.

1. At least one scenario is a regression check for the collision area named in the change map: rate limiting still returns 429 after the 21st request within a minute from one IP, and requests under the limit still succeed. Its `criterion:` labels it as a regression or collision check rather than one of AC1..AC3.
2. The cli scenarios run the exact command (`npm run sessions -- prune` and the `--dry-run` variant) and expect the exact stdout text (`pruned <n> sessions`) and exit code 0.
3. The dry-run scenario verifies that nothing was deleted (for example a follow-up `GET /api/me` with an idle session still returns 200, or a second prune reports the same count).
"""),
    },
)

# ---------------------------------------------------------------- 05 — cli-only pipeline, no UI
brief_05 = """
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
"""
fire_case(
    "abra-05-cli-pipeline-no-ui",
    brief_05,
    {
        **covers("AC1", "AC2", "AC3"),
        "cli-only": regex(r"surface: (web|api)", match="not_contains"),
        "uses-compact-command": regex(r"pipeline\.compact"),
        "runtime-not-source": llm("""
The answer is a checklist of cli verification scenarios for a Redis stream compaction command. All claims must hold to pass.

1. Every scenario runs the real command (`python -m pipeline.compact ...`, via `docker compose exec worker` or equivalent) and its `expect:` is a runtime observation: the exit code, the exact log line, or a Redis value read back with a redis-cli command (such as `XLEN orders` or `EXISTS pipeline:compact:last-run`).
2. No scenario satisfies a criterion by reading, grepping or inspecting source code files (`pipeline/compact.py`, `pipeline/redis_client.py`) instead of running the command.
3. The AC1 scenario has a `pre:` that seeds the stream with acknowledged entries older than 24h (for example XADD with explicit old ids and XACK), and the AC3 scenario has a `pre:` that makes Redis unreachable concretely (stop the redis service or point to a wrong host) and restores it afterwards.
4. Scenarios that create Redis entries are `mutating: yes` and state how they clean up.
"""),
    },
)

# ---------------------------------------------------------------- 06 — negative: diagnose a failure
neg_06 = f"""
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

{section(PLAN, 4)}

{section(PLAN, 5)}
"""
neg_case(
    "abra-06-neg-diagnose-failure",
    neg_06,
    {
        "names-s2": regex(r"\bS2\b"),
        "diagnosis": llm("""
The answer is a diagnosis of a failed verification scenario. All claims must hold to pass.

1. It names S2 (the session middleware change in `src/http/session-middleware.ts`) as the primary suspect, because `lastSeenAt` not refreshing after a request means the middleware is not calling the store's touch method (or is calling it before the session is read back).
2. It ties the conclusion to the evidence (200 responses with an unchanged `lastSeenAt`, no eviction logged) rather than guessing.
3. It does NOT produce a new or rewritten scenario checklist.
"""),
    },
)

# ---------------------------------------------------------------- 07 — negative: summarize criteria
neg_07 = f"""
List this plan's acceptance criteria as short bullets, one per criterion, in plain language. Do not design tests or verification steps.

{section(PLAN, 1)}
"""
neg_case(
    "abra-07-neg-summarize-criteria",
    neg_07,
    {
        "mentions-idle-ttl": regex(r"SESSION_IDLE_TTL_MS|lastSeenAt|idle", flags="i"),
        "bullets-only": llm("""
The answer restates a plan's acceptance criteria. All claims must hold to pass.

1. It contains one bullet per criterion (four) covering: eviction of idle sessions with a debug log, lastSeenAt refreshed on each request, sessions within the TTL untouched, and the 30-minute default TTL.
2. It contains no verification scenarios, no numbered test steps, and no `V1`-style scenario ids.
"""),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("abra-")))
