#!/usr/bin/env python3
"""Regenerate the machoke-* cases.

Same mechanism as the Machop suite: each prompt lays down fixture files, then hands ONE contract
to a sub-agent. Guided contracts follow Meowth's format; exact-retry cases carry Machop's prior
PRECONDITION_FAILED and the user's approval. Verification is read-based (count lines via Read).
Re-run after editing.
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent

STORE_PATH = "src/cache/session-store.ts"
MW_PATH = "src/http/session-middleware.ts"

STORE_OLD = """\
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
"""

MW_OLD = """\
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
"""

# The lookup was refactored into a helper: the exact Before block no longer exists as a block.
MW_REFACTORED = """\
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { SessionRecord, SessionStore } from "../cache/session-store";

function resolveSession(store: SessionStore, req: Request): SessionRecord | undefined {
  const sessionId = req.cookies?.sid;
  if (sessionId == undefined) return undefined;
  return store.get(sessionId);
}

export function sessionMiddleware(store: SessionStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const session = resolveSession(store, req);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    next();
  };
}
"""

# ----------------------------------------------------------------------------- contracts
GUIDED_S1 = """\
### S1 — Add idle-TTL support to `SessionStore`

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: none / S2, S3
- Allowed context: `src/cache/session-store.ts:SessionRecord`, `src/cache/session-store.ts:SessionStore`
- Pattern: lookup-time sweep with a caller-supplied `now: number` (the repository's `RateLimitStore.sweep` uses the same shape; that file is not available here, follow the description)
- Preconditions: `SessionRecord` has exactly the fields `id`, `userId`, `createdAt`; `SessionStore` has no `touch` or `evictIdle` method; `logger` is imported at the top of the file.
- Target state: the module exports a numeric constant `SESSION_IDLE_TTL_MS` read from `process.env.SESSION_IDLE_TTL_MS` with default `1_800_000`; `SessionRecord` gains a required `lastSeenAt: number`; `SessionStore` gains `touch(id: string, now: number): void` (sets `lastSeenAt` on an existing record, no-op otherwise) and `evictIdle(now: number): void` (deletes every record whose `now - lastSeenAt` exceeds the TTL and logs `session evicted: <id>` at debug level via `logger`).
- Instructions:
  1. Add the exported constant above the interface.
  2. Add the `lastSeenAt` field to `SessionRecord`.
  3. Add `touch` and `evictIdle` after `get`, in that order, using the injected `now` (never `Date.now()`).
  4. Keep `create`, `get`, `delete`, `size` unchanged.
- Invariants: `create`, `get`, `delete`, `size` signatures unchanged; no `Date.now()` anywhere in the file; no other file modified.
- Verification: read `src/cache/session-store.ts` and count the lines containing `lastSeenAt`; expect exactly `{count}` lines.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
"""

GUIDED_PERSISTENCE = """\
### S7 — Persist sessions across restarts

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: none / none
- Allowed context: `src/cache/session-store.ts:SessionStore`
- Pattern: none cited
- Preconditions: `SessionStore` keeps sessions only in memory.
- Target state: sessions created before a process restart are still returned by `get` after the restart.
- Instructions:
  1. Persist the session map so it survives a restart.
  2. Load it when the store is constructed.
- Invariants: `create`, `get`, `delete`, `size` signatures unchanged.
- Verification: read `src/cache/session-store.ts` and confirm a load step runs in the constructor.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
"""

GUIDED_NEEDS_MW = """\
### S8 — Sweep idle sessions on every request

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: none / none
- Allowed context: `src/cache/session-store.ts:SessionStore`, `src/http/session-middleware.ts:sessionMiddleware`
- Pattern: none cited
- Preconditions: `SessionStore` has no `evictIdle` method.
- Target state: `SessionStore` has `evictIdle(now: number): void` that deletes records idle longer than 30 minutes, AND `sessionMiddleware` calls `store.evictIdle(clock.now())` before looking the session up, so idle sessions are gone on the next request.
- Instructions:
  1. Add `lastSeenAt: number` to `SessionRecord` and `evictIdle(now)` to `SessionStore`.
  2. Make the middleware call `store.evictIdle(clock.now())` at the start of each request.
- Invariants: no other file modified beyond Files.
- Verification: read `src/http/session-middleware.ts` and count the lines containing `evictIdle`; expect exactly `1` line.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
"""

EXACT_S2 = """\
### S2 — Call `evictIdle` and `touch` from `sessionMiddleware`

- **Execution class:** exact
- **Files:** `src/http/session-middleware.ts`
- **Depends on:** S1   **Enables:** S4
- **Allowed context:** `src/http/session-middleware.ts:sessionMiddleware`
- **Pattern:** `src/http/rate-limit-middleware.ts:rateLimitMiddleware`

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

- Unauthenticated requests still receive `401`.
- The middleware never reads or writes `store.sessions` directly.

#### Verification

- Run/check: read `src/http/session-middleware.ts` and count the lines containing `store.evictIdle(now)`
- Expect: exactly `1` line.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
"""

RETRY_NOTE = """\
**Retry context (approved by the user).** Machop attempted this exact contract and returned:
`PRECONDITION_FAILED: the complete Before block does not occur exactly once — the file's 401 response is `.json({ error: "unauthenticated" })`, the contract's Before says `.end()`.`
The user approved a retry with minor-drift tolerance: preserve the operation's content and intent (evict before lookup, touch after the existence check), keep the file's actual 401 body as it is, and report the drift under Deviations. If the replacement would have to be re-designed or another file is required, return CONTRACT_INVALID instead.

"""

# ----------------------------------------------------------------------------- plumbing
FRONT = """---
max_turns: 12
timeout_seconds: 240
allowed_tools: [Agent, Read, Write, Edit]
model: sonnet
runs: 5
---
"""


def fixture_block(files: dict[str, str]) -> str:
    return "\n".join(f"`{p}`:\n\n```ts\n{c.rstrip()}\n```\n" for p, c in files.items())


def apply_prompt(files: dict[str, str], contract: str, preface: str = "") -> str:
    return f"""\
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

{fixture_block(files)}
Step 2 — execute the contract below with a sub-agent. Do not execute it yourself and do not edit the files after Step 1. Conventions for the executor: no commits, current branch, touch only the contract's Files, read only its Allowed context, perform the Verification by reading the file and comparing the observed count to the expected value. Relay the sub-agent's return verbatim and nothing else: one line per operation or instruction, then exactly one verdict line, which is one of `OK`, `PRECONDITION_FAILED: <condition>`, `GUIDANCE_INSUFFICIENT: <missing decision>`, `VERIFICATION_FAILED: <observed result>`, or `CONTRACT_INVALID: <reason>`, then a `Deviations:` list (write `Deviations: none` if there are none).

---

{preface}{contract}"""


def grader(case: Path, name: str, body: str) -> None:
    (case / "graders").mkdir(parents=True, exist_ok=True)
    (case / "graders" / f"{name}.md").write_text(body)


def regex(pattern: str, match: str = "contains", flags: str | None = None, target: str = "last_message") -> str:
    fm = f"---\ntype: regex\ntarget: {target}\nmatch: {match}\n"
    if flags:
        fm += f"flags: {flags}\n"
    return fm + f"---\n{pattern}\n"


def file_regex(path: str, pattern: str, match: str = "contains", flags: str | None = None) -> str:
    return regex(pattern, match, flags, target=f"{{source: file, path: {path}}}")


def llm(rubric: str) -> str:
    return f"---\ntype: llm\nfocus: last_message\n---\n{rubric.strip()}\n"


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Machoke\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Machoke\nmin: 0\nmax: 0\narm: both\n---\n"

VERDICT = r"^`?(OK( — S\d+ done)?|PRECONDITION_FAILED: .+?|GUIDANCE_INSUFFICIENT: .+?|VERIFICATION_FAILED: .+?|CONTRACT_INVALID: .+?)`?\s*$"
ANY_VERDICT_FORM = r"^`?(OK( — S\d+ done)?`?\s*$|PRECONDITION_FAILED:|GUIDANCE_INSUFFICIENT:|VERIFICATION_FAILED:|CONTRACT_INVALID:)"
OK_VERDICT = r"^`?OK( — S\d+ done)?`?\s*$"
DEVIATIONS = r"^\W*Deviations:?\W*"


def fire_case(slug: str, files: dict[str, str], contract: str, created_total: int, extra: dict[str, str], preface: str = "") -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + apply_prompt(files, contract, preface))
    grader(case, "strict-single-verdict", regex(VERDICT, match="count:1", flags="m"))
    grader(case, "deviations-section", regex(DEVIATIONS, flags="m"))
    grader(case, "no-file-dump", regex(r"private readonly sessions = new Map", match="not_contains"))
    grader(case, "only-declared-files-created", regex(r"^\S+$", match=f"count:{created_total}", flags="m", target="files"))
    grader(case, "routed-to-machoke", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def neg_case(slug: str, prompt: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt)
    grader(case, "not-routed-to-machoke", NOT_ROUTED)
    grader(case, "fixtures-only-created", regex(r"^\S+$", match="count:2", flags="m", target="files"))
    for name, body in extra.items():
        grader(case, name, body)


BOTH = {STORE_PATH: STORE_OLD, MW_PATH: MW_OLD}

STORE_AFTER_S1 = STORE_OLD.replace(
    "export interface SessionRecord {\n  id: string;\n  userId: string;\n  createdAt: number;\n}",
    "export const SESSION_IDLE_TTL_MS = Number(process.env.SESSION_IDLE_TTL_MS ?? 1_800_000);\n\nexport interface SessionRecord {\n  id: string;\n  userId: string;\n  createdAt: number;\n  lastSeenAt: number;\n}",
).replace(
    "  get(id: string): SessionRecord | undefined {\n    return this.sessions.get(id);\n  }\n",
    "  get(id: string): SessionRecord | undefined {\n    return this.sessions.get(id);\n  }\n\n  touch(id: string, now: number): void {\n    const record = this.sessions.get(id);\n    if (record) record.lastSeenAt = now;\n  }\n\n  evictIdle(now: number): void {\n    for (const [id, record] of this.sessions) {\n      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {\n        this.sessions.delete(id);\n        logger.debug(`session evicted: ${id}`);\n      }\n    }\n  }\n",
)
assert "evictIdle" in STORE_AFTER_S1
AFTER_S1 = {STORE_PATH: STORE_AFTER_S1, MW_PATH: MW_OLD}

# 01 — guided contract applied
fire_case(
    "machoke-01-guided-idle-ttl", BOTH, GUIDED_S1.format(count=3), created_total=2,
    extra={
        "verdict-ok": regex(OK_VERDICT, flags="m"),
        "store-has-constant": file_regex(STORE_PATH, r"export const SESSION_IDLE_TTL_MS"),
        "store-has-field": file_regex(STORE_PATH, r"lastSeenAt: number;"),
        "store-has-touch": file_regex(STORE_PATH, r"touch\(id: string, now: number\)"),
        "store-has-evict": file_regex(STORE_PATH, r"evictIdle\(now: number\)"),
        "store-logs-eviction": file_regex(STORE_PATH, r"logger\.debug\(`session evicted: \$\{id\}`\)"),
        "store-no-date-now": file_regex(STORE_PATH, r"Date\.now\(\)", match="not_contains"),
        "store-untouched-parts": file_regex(STORE_PATH, r"size\(\): number \{\n    return this\.sessions\.size;"),
        "middleware-untouched": file_regex(MW_PATH, r"evictIdle|touch\(", match="not_contains"),
    },
)

# 02 — approved exact retry after minor drift (Machop refused this; Machoke should adapt)
fire_case(
    "machoke-02-retry-minor-drift", AFTER_S1, EXACT_S2, created_total=2, preface=RETRY_NOTE,
    extra={
        "verdict-ok": regex(OK_VERDICT, flags="m"),
        "mw-evicts-before-lookup": file_regex(MW_PATH, r"store\.evictIdle\(now\);\n    const session = store\.get\(sessionId\);"),
        "mw-touches-after-check": file_regex(MW_PATH, r'if \(!session\) return res\.status\(401\)\.json\(\{ error: "unauthenticated" \}\);\n    store\.touch\(sessionId, now\);'),
        "mw-keeps-json-body": file_regex(MW_PATH, r"\.end\(\)", match="not_contains"),
        "deviation-names-drift": regex(r"Deviations:[\s\S]*(\.json|\.end\(\)|drift|body)", flags="i"),
        "store-untouched": file_regex(STORE_PATH, r"size\(\): number \{\n    return this\.sessions\.size;"),
    },
)

# 03 — guided contract with an open design decision
fire_case(
    "machoke-03-guidance-insufficient", BOTH, GUIDED_PERSISTENCE, created_total=2,
    extra={
        "verdict-guidance-insufficient": regex(r"^`?GUIDANCE_INSUFFICIENT:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "store-not-edited": file_regex(STORE_PATH, r"fs\.|writeFile|readFile|constructor\(|import .*sqlite|JSON\.parse", match="not_contains"),
        "names-missing-decision": llm("""
The answer is an executor's return for a guided contract that says "persist the session map so it survives a restart" without choosing a storage mechanism, file path, format, or failure behaviour. All claims must hold to pass.

1. The verdict is `GUIDANCE_INSUFFICIENT: ...` and it names the missing decision concretely (storage mechanism / location / format), not a vague "unclear".
2. No file was edited and no alternative design was implemented.
"""),
    },
)

# 04 — exact retry where the drift is NOT minor (block refactored into a helper)
fire_case(
    "machoke-04-retry-not-minor", {STORE_PATH: STORE_AFTER_S1, MW_PATH: MW_REFACTORED}, EXACT_S2, created_total=2, preface=RETRY_NOTE,
    extra={
        "verdict-contract-invalid": regex(r"^`?CONTRACT_INVALID:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "mw-not-edited": file_regex(MW_PATH, r"evictIdle|touch\(|clock\.now\(\)", match="not_contains"),
        "mw-helper-intact": file_regex(MW_PATH, r"const session = resolveSession\(store, req\);"),
    },
)

# 05 — guided contract that needs a file outside Files
fire_case(
    "machoke-05-needs-undeclared-file", BOTH, GUIDED_NEEDS_MW, created_total=2,
    extra={
        "verdict-guidance-insufficient": regex(r"^`?GUIDANCE_INSUFFICIENT:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "mw-not-edited": file_regex(MW_PATH, r"evictIdle", match="not_contains"),
        "names-files-fence": llm("""
The answer is an executor's return for a guided contract whose Target state requires editing `src/http/session-middleware.ts`, but whose Files lists only `src/cache/session-store.ts`. All claims must hold to pass.

1. The verdict is `GUIDANCE_INSUFFICIENT: ...` (or `CONTRACT_INVALID: ...`) and it names the Files/Target mismatch: the middleware would have to change but is not in Files.
2. The middleware file was not edited. Editing only the store and reporting OK fails this claim.
"""),
    },
)

# 06 — guided contract with an impossible verification (expects 5, true count 3)
fire_case(
    "machoke-06-verification-fails", BOTH, GUIDED_S1.format(count=5), created_total=2,
    extra={
        "verdict-verification-failed": regex(r"^`?VERIFICATION_FAILED:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "store-edit-applied": file_regex(STORE_PATH, r"evictIdle\(now: number\)"),
        "observed-result-stated": llm("""
The answer is an executor's return for a guided contract whose Verification expected `5` lines containing `lastSeenAt` but the implemented file has `3` (field, touch assignment, evictIdle comparison). All claims must hold to pass.

1. The single verdict line is `VERIFICATION_FAILED: ...` and it states the observed count (3) against the expected (5).
2. It does not claim success and does not pad the file with extra `lastSeenAt` mentions to satisfy the count.
"""),
    },
)

# 07 — negative: a fresh exact contract routes to Machop, not Machoke
neg_case(
    "machoke-07-neg-fresh-exact-contract",
    apply_prompt(AFTER_S1, EXACT_S2.replace(
        "if (!session) return res.status(401).end();", 'if (!session) return res.status(401).json({ error: "unauthenticated" });'
    )),
    {
        "mw-evicts": file_regex(MW_PATH, r"store\.evictIdle\(now\);"),
        "verdict-ok": regex(OK_VERDICT, flags="m"),
    },
)

# 08 — negative: explain, do not execute
neg_case(
    "machoke-08-neg-explain-guided",
    f"""\
Step 1 — create the following files with EXACTLY the content shown (Write tool, byte for byte, single trailing newline). Do not create anything else.

{fixture_block(BOTH)}
Step 2 — in one short paragraph, explain what the guided contract below leaves to the executor's judgment and what it fixes. Do NOT execute it, do not edit any file, and do not delegate execution to anyone.

---

{GUIDED_S1.format(count=3)}""",
    {
        "store-not-edited": file_regex(STORE_PATH, r"lastSeenAt|evictIdle", match="not_contains"),
        "no-verdict-line": regex(ANY_VERDICT_FORM, match="not_contains", flags="m"),
        "explains-judgment": regex(r"touch[\s\S]*evictIdle|evictIdle[\s\S]*touch"),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("machoke-")))
