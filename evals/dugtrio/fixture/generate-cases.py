#!/usr/bin/env python3
"""Regenerate the dugtrio-* cases.

Each prompt lays down a small TypeScript tree (the fixture), then asks a sub-agent either to
MAP where a change lands (requirement brief in Slowpoke's shape) or to DIAGNOSE a failed
verification scenario. Expected answers are known from the fixture, so graders are regexes on
`file:symbol` citations plus one rubric per case. Re-run after editing.
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent

# ----------------------------------------------------------------------------- fixture tree
TREE: dict[str, str] = {
    "src/lib/clock.ts": """\
export interface Clock {
  now(): number;
}

export const systemClock: Clock = { now: () => Date.now() };
""",
    "src/lib/logger.ts": """\
export const logger = {
  debug: (msg: string): void => console.debug(msg),
  info: (msg: string): void => console.info(msg),
  warn: (msg: string): void => console.warn(msg),
};
""",
    "src/cache/session-store.ts": """\
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

  size(): number {
    return this.sessions.size;
  }
}
""",
    "src/cache/rate-limit-store.ts": """\
import { logger } from "../lib/logger";

export const RATE_LIMIT_WINDOW_MS = Number(process.env.RATE_LIMIT_WINDOW_MS ?? 60_000);

interface Bucket {
  count: number;
  windowStartedAt: number;
}

export class RateLimitStore {
  private readonly buckets = new Map<string, Bucket>();

  hit(key: string, now: number): number {
    const bucket = this.buckets.get(key) ?? { count: 0, windowStartedAt: now };
    bucket.count += 1;
    this.buckets.set(key, bucket);
    return bucket.count;
  }

  // Lookup-time sweep: callers pass `now` from the injected Clock; never Date.now() here.
  sweep(now: number): void {
    for (const [key, bucket] of this.buckets) {
      if (now - bucket.windowStartedAt > RATE_LIMIT_WINDOW_MS) {
        this.buckets.delete(key);
        logger.debug(`rate-limit bucket expired: ${key}`);
      }
    }
  }
}
""",
    "src/http/session-middleware.ts": """\
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
""",
    "src/http/rate-limit-middleware.ts": """\
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { RateLimitStore } from "../cache/rate-limit-store";

const MAX_PER_WINDOW = 20;

export function rateLimitMiddleware(store: RateLimitStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const now = clock.now();
    store.sweep(now);
    const count = store.hit(req.ip ?? "unknown", now);
    if (count > MAX_PER_WINDOW) return res.status(429).json({ error: "rate_limited" });
    next();
  };
}
""",
    "src/http/routes/me.ts": """\
import type { Request, Response } from "express";

// Serialises the session record for GET /api/me. Only these two fields are exposed on purpose.
export function meHandler(req: Request, res: Response): void {
  const { id, userId } = req.session!;
  res.json({ sessionId: id, userId });
}
""",
    "src/cache/__tests__/rate-limit-store.test.ts": """\
import { describe, expect, it } from "vitest";
import { RATE_LIMIT_WINDOW_MS, RateLimitStore } from "../rate-limit-store";

describe("RateLimitStore", () => {
  it("expires a bucket after the window", () => {
    const store = new RateLimitStore();
    store.hit("1.2.3.4", 0);
    store.sweep(RATE_LIMIT_WINDOW_MS + 1);
    expect(store.hit("1.2.3.4", RATE_LIMIT_WINDOW_MS + 2)).toBe(1);
  });
});
""",
}

# Diagnosis fixtures: the TK-412 change applied with the touch-before-evict bug.
STORE_AFTER = TREE["src/cache/session-store.ts"].replace(
    "export interface SessionRecord {\n  id: string;\n  userId: string;\n  createdAt: number;\n}",
    "export const SESSION_IDLE_TTL_MS = Number(process.env.SESSION_IDLE_TTL_MS ?? 1_800_000);\n\nexport interface SessionRecord {\n  id: string;\n  userId: string;\n  createdAt: number;\n  lastSeenAt: number;\n}",
).replace(
    "  get(id: string): SessionRecord | undefined {\n    return this.sessions.get(id);\n  }\n",
    "  get(id: string): SessionRecord | undefined {\n    return this.sessions.get(id);\n  }\n\n  touch(id: string, now: number): void {\n    const record = this.sessions.get(id);\n    if (record) record.lastSeenAt = now;\n  }\n\n  evictIdle(now: number): void {\n    for (const [id, record] of this.sessions) {\n      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {\n        this.sessions.delete(id);\n        logger.debug(`session evicted: ${id}`);\n      }\n    }\n  }\n",
)
MW_BUGGY = TREE["src/http/session-middleware.ts"].replace(
    "    const session = store.get(sessionId);\n    if (!session) return res.status(401).json({ error: \"unauthenticated\" });\n",
    "    const now = clock.now();\n    store.touch(sessionId, now);\n    store.evictIdle(now);\n    const session = store.get(sessionId);\n    if (!session) return res.status(401).json({ error: \"unauthenticated\" });\n",
)
MW_CORRECT = TREE["src/http/session-middleware.ts"].replace(
    "    const session = store.get(sessionId);\n    if (!session) return res.status(401).json({ error: \"unauthenticated\" });\n",
    "    const now = clock.now();\n    store.evictIdle(now);\n    const session = store.get(sessionId);\n    if (!session) return res.status(401).json({ error: \"unauthenticated\" });\n    store.touch(sessionId, now);\n",
)
assert "store.touch(sessionId, now);\n    store.evictIdle(now);" in MW_BUGGY
assert "store.evictIdle(now);\n    const session" in MW_CORRECT

BRIEF_TTL = """\
**Goal** — Sessions abandoned without logout live forever in the in-memory `SessionStore`; add an idle TTL so a session not touched for `SESSION_IDLE_TTL_MS` is evicted on the next request and every authenticated request refreshes its `lastSeenAt`.

**Acceptance criteria**
- AC1 — A session whose `lastSeenAt` is older than `SESSION_IDLE_TTL_MS` is evicted by the next request through `sessionMiddleware` and a debug log line `session evicted: <id>` is emitted.
- AC2 — Each request that passes `sessionMiddleware` updates the session's `lastSeenAt` to the current clock value.
- AC3 — Sessions touched within the TTL window are returned unchanged.
- AC4 — `SESSION_IDLE_TTL_MS` defaults to `1800000` when unset.

**Scope** — `SessionStore`, `sessionMiddleware`, and their tests.

**Out of scope** — Persisting sessions across restarts; an admin endpoint to list sessions.

**Constraints** — Library code takes an injected `Clock`, never `Date.now()`; logging goes through `logger`; `SessionStore` is the only owner of the session map.
"""

BRIEF_RATE_BY_USER = """\
**Goal** — Rate limiting currently keys on the client IP, which punishes users behind a shared NAT; key it on the authenticated user id instead, falling back to IP for unauthenticated requests.

**Acceptance criteria**
- AC1 — Requests carrying a valid session are counted per `userId`, not per IP.
- AC2 — Requests without a session are still counted per IP.
- AC3 — The 429 response body and the 20-requests-per-window limit are unchanged.

**Scope** — the rate-limit middleware and, if needed, its store.

**Out of scope** — Per-route limits; changing the window length.

**Constraints** — The session must already be resolved when the rate limiter runs; do not resolve sessions twice per request.
"""

CHANGE_MAP = """\
| Area | File(s) | New / Modify | Responsibility |
| --- | --- | --- | --- |
| Cache | `src/cache/session-store.ts` | Modify | S1: `lastSeenAt`, `touch`, `evictIdle`, TTL const |
| HTTP | `src/http/session-middleware.ts` | Modify | S2: call `evictIdle` + `touch` per request |
| Tests | `src/cache/__tests__/session-store.test.ts` | New | S3: store tests |
"""

# ----------------------------------------------------------------------------- plumbing
FRONT = """---
max_turns: 12
timeout_seconds: 300
allowed_tools: [Agent, Read, Write, Edit, Glob, Grep]
plugins: [../../..]
model: sonnet
runs: 5
---
"""


def fixture_block(files: dict[str, str]) -> str:
    return "\n".join(f"`{p}`:\n\n```ts\n{c.rstrip()}\n```\n" for p, c in files.items())


SETUP = """\
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

"""

MAP_ASK = """\
Step 2 — with a sub-agent, map where the change described in the requirement brief below lands in this codebase. Do not do the mapping yourself. Relay the sub-agent's brief verbatim and nothing else. The brief cites `file:symbol` locations and names patterns; it never pastes file bodies. It has exactly these four sections: **Insertion points**, **Prior art to mirror**, **Seams & extension points**, **Collisions**.

---

"""

DIAG_ASK = """\
Step 2 — a verification scenario failed. With a sub-agent, diagnose the cause: which plan step and file(s) are the suspect, with a one-line cause hypothesis (100 words maximum for the whole return). Do not diagnose it yourself and do not fix anything. Relay the sub-agent's return verbatim and nothing else.

---

"""


def grader(case: Path, name: str, body: str) -> None:
    (case / "graders").mkdir(parents=True, exist_ok=True)
    (case / "graders" / f"{name}.md").write_text(body)


def regex(pattern: str, match: str = "contains", flags: str | None = None, target: str = "last_message") -> str:
    fm = f"---\ntype: regex\ntarget: {target}\nmatch: {match}\n"
    if flags:
        fm += f"flags: {flags}\n"
    return fm + f"---\n{pattern}\n"


def file_regex(path: str, pattern: str, match: str = "contains") -> str:
    return regex(pattern, match, target=f"{{source: file, path: {path}}}")


def llm(rubric: str) -> str:
    return f"---\ntype: llm\nfocus: last_message\n---\n{rubric.strip()}\n"


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Dugtrio\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Dugtrio\nmin: 0\nmax: 0\narm: both\n---\n"
DUMP = r"private readonly (sessions|buckets) = new Map|return \(req: Request, res: Response, next: NextFunction\) =>"
# bold labels or markdown headings, in Dugtrio's order
H = lambda t: rf"(?:\*\*{t}:?\*\*|^#{{1,4}} {t})"
SECTIONS = H("Insertion points") + r"[\s\S]*" + H("Prior art to mirror") + r"[\s\S]*" + H("Seams & extension points") + r"[\s\S]*" + H("Collisions")
ABS_PATHS = r"/private/tmp/|/home/cwd/|/Users/"


def case_dir(slug: str) -> Path:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    return case


def tree_unmodified(case: Path, files: dict[str, str]) -> None:
    # every fixture file still holds a distinctive line -> nothing was edited, no file was dumped
    grader(case, "fixtures-only-created", regex(r"^\S+$", match=f"count:{len(files)}", flags="m", target="files"))


def map_case(slug: str, files: dict[str, str], brief: str, extra: dict[str, str]) -> None:
    case = case_dir(slug)
    (case / "prompt.md").write_text(FRONT + SETUP + fixture_block(files) + MAP_ASK + brief)
    grader(case, "four-sections-in-order", regex(SECTIONS, flags="m"))
    grader(case, "no-file-body-dump", regex(DUMP, match="not_contains"))
    grader(case, "repo-relative-paths", regex(ABS_PATHS, match="not_contains"))
    grader(case, "routed-to-dugtrio", ROUTED)
    tree_unmodified(case, files)
    for name, body in extra.items():
        grader(case, name, body)


def diag_case(slug: str, files: dict[str, str], scenario: str, extra: dict[str, str]) -> None:
    case = case_dir(slug)
    (case / "prompt.md").write_text(FRONT + SETUP + fixture_block(files) + DIAG_ASK + scenario)
    grader(case, "under-100-words", regex(r"(?:\S+\s+){120}", match="not_contains"))
    grader(case, "no-file-body-dump", regex(DUMP, match="not_contains"))
    grader(case, "routed-to-dugtrio", ROUTED)
    tree_unmodified(case, files)
    for name, body in extra.items():
        grader(case, name, body)


# ----------------------------------------------------------------------------- 01 map idle TTL
map_case(
    "dugtrio-01-map-idle-ttl", TREE, BRIEF_TTL,
    {
        "cites-store": regex(r"session-store\.ts:(SessionStore|SessionRecord)"),
        "cites-middleware": regex(r"session-middleware\.ts:sessionMiddleware"),
        "prior-art-sweep": regex(r"rate-limit-store\.ts[^\n]*\bsweep\b|\bsweep\b[^\n]*rate-limit-store\.ts"),
        "prior-art-middleware": regex(r"rate-limit-middleware\.ts"),
        "collision-me-route": regex(r"routes/me\.ts"),
        "seam-clock": regex(r"src/lib/clock\.ts|\bClock\b"),
        "map-is-right": llm("""
The answer maps where an idle-TTL change to `SessionStore` and `sessionMiddleware` lands in a small TypeScript tree. All claims must hold to pass.

1. Insertion points name `src/cache/session-store.ts` (`SessionRecord` and/or `SessionStore`) and `src/http/session-middleware.ts:sessionMiddleware`, and a new test file under `src/cache/__tests__/`.
2. Prior art names `RateLimitStore.sweep` in `src/cache/rate-limit-store.ts` as the lookup-time sweep to mirror (caller-supplied `now`, `logger.debug` on expiry) and `rateLimitMiddleware` in `src/http/rate-limit-middleware.ts` as the sweep-then-act middleware shape, and `src/cache/__tests__/rate-limit-store.test.ts` as the test shape.
3. Seams name the injected `Clock` (`src/lib/clock.ts`) as the time source; `Date.now()` is not proposed.
4. Collisions name `src/http/routes/me.ts:meHandler`, which serialises `SessionRecord` and would need a decision on exposing `lastSeenAt`.
5. No file bodies are pasted; locations are cited as `file:symbol`.
"""),
    },
)

# ----------------------------------------------------------------------------- 02 map rate-limit by user
map_case(
    "dugtrio-02-map-rate-limit-by-user", TREE, BRIEF_RATE_BY_USER,
    {
        "cites-rate-limit-middleware": regex(r"rate-limit-middleware\.ts:rateLimitMiddleware"),
        "prior-art-session-lookup": regex(r"session-middleware\.ts"),
        "collision-ordering": regex(r"order|before|after|chain", flags="i"),
        "map-is-right": llm("""
The answer maps a change that keys rate limiting on the authenticated user id instead of the client IP. All claims must hold to pass.

1. Insertion points name `src/http/rate-limit-middleware.ts:rateLimitMiddleware` (the `store.hit(req.ip ...)` key) and note that `RateLimitStore` itself keys on an opaque string and may not need to change.
2. Prior art names `src/http/session-middleware.ts:sessionMiddleware` as the place that resolves the session and sets `req.session`.
3. Collisions or seams name the middleware ordering constraint: the session must be resolved before the rate limiter runs, so the chain order (or the limiter reading `req.session`) is a side effect to handle, and the existing `src/cache/__tests__/rate-limit-store.test.ts` keys on an IP string.
4. No file bodies are pasted.
"""),
    },
)

# ----------------------------------------------------------------------------- 03 bare ticket reference
map_case(
    "dugtrio-03-bare-ticket-ref", TREE, "Ticket: TK-412. That is all the context available; there is no normalized requirement brief.",
    {
        "refuses-bare-ref": regex(r"missing normalized requirement", flags="i"),
        "no-mapping-attempted": regex(r"Insertion points", match="not_contains", flags="i"),
    },
)
# the four-sections grader does not apply to the refusal case
(SUITE / "dugtrio-03-bare-ticket-ref" / "graders" / "four-sections-in-order.md").unlink()

# ----------------------------------------------------------------------------- 04 diagnose touch-before-evict
DIAG_TREE_BUGGY = {**TREE, "src/cache/session-store.ts": STORE_AFTER, "src/http/session-middleware.ts": MW_BUGGY}
diag_case(
    "dugtrio-04-diagnose-touch-order", DIAG_TREE_BUGGY,
    f"""\
Failed scenario:

```text
V1 · surface: api · mutating: yes · criterion: AC1
  pre: server with SESSION_IDLE_TTL_MS=60000, NODE_ENV=test (X-Test-Now header honoured)
  steps: 1. POST /api/login user=alice at X-Test-Now=0, capture sid  2. GET /api/me with sid at X-Test-Now=61000
  expect: step 2 returns 401 and the log contains `session evicted: <sid>`
```

Evidence: step 2 returned 200 with `userId: "alice"`. The log contains no `session evicted` line. A direct `store.evictIdle(61000)` in a REPL against the same store instance DOES evict the session, so the store logic itself works.

Plan change map:

{CHANGE_MAP}
Execution-log deviations: none; S1 and S2 applied as specified.
""",
    {
        "names-s2": regex(r"\bS2\b"),
        "names-middleware": regex(r"session-middleware\.ts"),
        "names-order": regex(r"touch[\s\S]{0,120}(before|prior|precedes|first)[\s\S]{0,120}evict|evict[\s\S]{0,120}after[\s\S]{0,120}touch", flags="i"),
        "diagnosis-is-right": llm("""
The answer diagnoses a failed idle-eviction scenario. All claims must hold to pass.

1. It names S2 / `src/http/session-middleware.ts` as the suspect, not the store (the evidence says the store evicts correctly when called directly).
2. The cause hypothesis is that the middleware calls `store.touch(sessionId, now)` BEFORE `store.evictIdle(now)`, so the request refreshes `lastSeenAt` and the session can never be idle at sweep time.
3. It is at most about 100 words and does not paste file bodies or propose a full fix.
"""),
    },
)

# ----------------------------------------------------------------------------- 05 diagnose: cause outside the change map
DIAG_TREE_CORRECT = {**TREE, "src/cache/session-store.ts": STORE_AFTER, "src/http/session-middleware.ts": MW_CORRECT}
diag_case(
    "dugtrio-05-diagnose-outside-plan", DIAG_TREE_CORRECT,
    f"""\
Failed scenario:

```text
V2 · surface: api · mutating: yes · criterion: AC2
  pre: session s1 created at X-Test-Now=0
  steps: 1. GET /api/me with sid=s1 at X-Test-Now=5000  2. GET /api/me again at X-Test-Now=6000
  expect: the second response body has lastSeenAt = 5000
```

Evidence: both responses are 200 with body `{{ "sessionId": "s1", "userId": "u1" }}`; there is no `lastSeenAt` field in either body at all. A REPL read of the store after step 1 shows `lastSeenAt === 5000` on the record, so the store IS being refreshed.

Plan change map:

{CHANGE_MAP}
Execution-log deviations: none; S1, S2 and S3 applied as specified.
""",
    {
        "names-me-route": regex(r"routes/me\.ts"),
        "says-outside-plan": regex(r"outside|not (in|part of) the (plan|change map)|design gap|unchanged file|not (a|an) edit bug", flags="i"),
        "diagnosis-is-right": llm("""
The answer diagnoses a scenario in which `lastSeenAt` never appears in the `/api/me` response although the store holds the refreshed value. All claims must hold to pass.

1. It points at `src/http/routes/me.ts:meHandler`, which serialises only `sessionId` and `userId`, as the reason the field is absent.
2. It states explicitly that this file is outside the plan's change map (S1..S3 did not touch it), so this is a design/scope gap rather than an edit bug in S1..S3.
3. It does not blame S1 or S2, and it is compact (about 100 words or fewer).
"""),
    },
)

# ----------------------------------------------------------------------------- 06 negative: apply a contract (executor's job)
EXACT_CONTRACT = """\
### S9 — Log rate-limit rejections

- **Execution class:** exact
- **Files:** `src/http/rate-limit-middleware.ts`
- **Depends on:** none   **Enables:** none
- **Allowed context:** `src/http/rate-limit-middleware.ts:rateLimitMiddleware`
- **Pattern:** `src/cache/rate-limit-store.ts:RateLimitStore.sweep`

#### Preconditions

- The complete Before block occurs exactly once in `src/http/rate-limit-middleware.ts`.

#### Operations

1. **replace_exact** at `src/http/rate-limit-middleware.ts:rateLimitMiddleware`

**Before:**

```ts
    if (count > MAX_PER_WINDOW) return res.status(429).json({ error: "rate_limited" });
```

**After:**

```ts
    if (count > MAX_PER_WINDOW) {
      logger.warn(`rate limited: ${req.ip ?? "unknown"}`);
      return res.status(429).json({ error: "rate_limited" });
    }
```

2. **insert_after_exact** at `src/http/rate-limit-middleware.ts` imports

**Anchor:**

```ts
import type { RateLimitStore } from "../cache/rate-limit-store";
```

**Insert:**

```ts
import { logger } from "../lib/logger";
```

#### Invariants

- The 429 body is unchanged.

#### Verification

- Run/check: read `src/http/rate-limit-middleware.ts` and count the lines containing `logger`
- Expect: exactly `2` lines.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
"""


def neg_case(slug: str, prompt: str, files: dict[str, str], extra: dict[str, str]) -> None:
    case = case_dir(slug)
    (case / "prompt.md").write_text(FRONT + prompt)
    grader(case, "not-routed-to-dugtrio", NOT_ROUTED)
    grader(case, "no-mapping-sections", regex(r"Insertion points|Prior art to mirror", match="not_contains", flags="i"))
    for name, body in extra.items():
        grader(case, name, body)


neg_case(
    "dugtrio-06-neg-apply-contract",
    SETUP + fixture_block(TREE) + """\
Step 2 — apply the exact execution contract below with a sub-agent (no commits, current branch, touch only its Files, verify by reading). Relay the sub-agent's return verbatim: one line per operation and one verdict line.

---

""" + EXACT_CONTRACT,
    TREE,
    {
        "edit-applied": file_regex("src/http/rate-limit-middleware.ts", r"logger\.warn\(`rate limited: "),
        "import-added": file_regex("src/http/rate-limit-middleware.ts", r'import \{ logger \} from "\.\./lib/logger";'),
    },
)

neg_case(
    "dugtrio-07-neg-list-tree",
    SETUP + fixture_block(TREE) + """\
Step 2 — list every file under `src/` with a one-line description of what it exports, as a plain bullet list. Do not analyse a change, do not map insertion points, and do not delegate.
""",
    TREE,
    {
        "lists-all-files": regex(r"clock\.ts[\s\S]*logger\.ts[\s\S]*session-store\.ts|session-store\.ts[\s\S]*clock\.ts"),
        "mentions-every-file": llm("""
The answer lists the files of a small TypeScript tree with one-line descriptions. All claims must hold to pass.

1. All eight fixture files are listed: clock.ts, logger.ts, session-store.ts, rate-limit-store.ts, session-middleware.ts, rate-limit-middleware.ts, routes/me.ts, __tests__/rate-limit-store.test.ts.
2. It is a plain listing; it does not analyse a change or produce Insertion points / Prior art / Seams / Collisions sections.
"""),
        "tree-untouched": regex(r"^\S+$", match=f"count:{len(TREE)}", flags="m", target="files"),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("dugtrio-")))
