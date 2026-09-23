#!/usr/bin/env python3
"""Regenerate the machamp-* cases.

Machamp is the last-resort executor: it completes a contract whose intent is clear but whose exact
operation / guided instructions do not apply cleanly, after Machop and Machoke failed and the user
approved escalation. Same prompt-driven fixture mechanism as the Machop suite. Re-run after editing.
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent

STORE_PATH = "src/cache/session-store.ts"
MW_PATH = "src/http/session-middleware.ts"

STORE_AFTER_S1 = """\
import { logger } from "../lib/logger";

export const SESSION_IDLE_TTL_MS = Number(process.env.SESSION_IDLE_TTL_MS ?? 1_800_000);

export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
  lastSeenAt: number;
}

export class SessionStore {
  private readonly sessions = new Map<string, SessionRecord>();

  create(record: SessionRecord): void {
    this.sessions.set(record.id, record);
  }

  get(id: string): SessionRecord | undefined {
    return this.sessions.get(id);
  }

  touch(id: string, now: number): void {
    const record = this.sessions.get(id);
    if (record) record.lastSeenAt = now;
  }

  evictIdle(now: number): void {
    for (const [id, record] of this.sessions) {
      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {
        this.sessions.delete(id);
        logger.debug(`session evicted: ${id}`);
      }
    }
  }

  delete(id: string): void {
    this.sessions.delete(id);
  }

  size(): number {
    return this.sessions.size;
  }
}
"""

# Drifted in two ways at once: the 401 body differs AND the lookup moved into a local helper,
# so neither Machop (exact) nor Machoke (minor drift) could apply the operation.
MW_DRIFTED = """\
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { SessionRecord, SessionStore } from "../cache/session-store";

function lookup(store: SessionStore, req: Request): SessionRecord | undefined {
  const sessionId = req.cookies?.sid;
  return sessionId == undefined ? undefined : store.get(sessionId);
}

export function sessionMiddleware(store: SessionStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const session = lookup(store, req);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    next();
  };
}
"""

EXACT_S2 = """\
### S2 — Call `evictIdle` and `touch` from `sessionMiddleware`

- **Execution class:** exact
- **Files:** `src/http/session-middleware.ts`
- **Depends on:** S1   **Enables:** S4
- **Allowed context:** `src/http/session-middleware.ts:sessionMiddleware`, `src/cache/session-store.ts:SessionStore`
- **Pattern:** sweep-then-act middleware with the injected `Clock` (reference only; the prior-art file is not in this checkout)

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
- Every request that finds a session must call `store.touch` with the same `now` used for the sweep.

#### Verification

- Run/check: read `src/http/session-middleware.ts` and count the lines containing `store.evictIdle(now)`; then count the lines containing `store.touch(`
- Expect: exactly `1` line each.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
"""

ESCALATION = """\
**Escalation context (approved by the user).** Machop returned `PRECONDITION_FAILED: the complete Before block does not occur in the file`. Machoke returned `CONTRACT_INVALID: the session lookup was refactored into a local helper and the 401 body differs; not minor drift`. The user reviewed both and approved escalation to a last-resort executor: complete the contract's intent (sweep idle sessions with `clock.now()` before the lookup, touch the found session after the existence check, keep the file's actual 401 body and its helper), stay inside Files, preserve every Invariant, and log every deviation from the literal operation. If the intent genuinely requires another file or a design decision, fail with a precise reason instead.

"""

GUIDED_RENAMED = """\
### S5 — Log evictions with the tenant id

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: S1 / none
- Allowed context: `src/cache/session-store.ts:SessionStore`
- Pattern: none cited
- Preconditions: `SessionStore.sweep(now)` exists and logs `session evicted: <id>` on each eviction.
- Target state: the eviction log line reads `session evicted: <id> (user <userId>)`, nothing else changes.
- Instructions:
  1. In `SessionStore.sweep`, extend the `logger.debug` call to include the record's `userId` in the format above.
- Invariants: method signatures unchanged; no other log lines change.
- Verification: read `src/cache/session-store.ts` and count the lines containing `(user ${record.userId})`; expect exactly `1` line.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
"""

ESCALATION_RENAMED = """\
**Escalation context (approved by the user).** Machoke returned `PRECONDITION_FAILED: SessionStore has no method named sweep`. The user confirmed the contract author meant the existing eviction method (it is called `evictIdle` in this file) and approved escalation: complete the intent against the method that actually performs the eviction, stay inside Files, and record the name mismatch under Deviations. If the intent cannot be met inside Files, fail with a precise reason.

"""

GUIDED_NEEDS_FILE = """\
### S6 — Expose the eviction count on the health endpoint

- Execution class: guided
- Files: `src/cache/session-store.ts`
- Depends on / Enables: S1 / none
- Allowed context: `src/cache/session-store.ts:SessionStore`
- Pattern: none cited
- Preconditions: `SessionStore.evictIdle(now)` exists.
- Target state: `GET /health` returns `{ "evictedSessions": <count since start> }` alongside its existing fields.
- Instructions:
  1. Count evictions in `SessionStore`.
  2. Return the count from the health handler.
- Invariants: no other endpoint changes.
- Verification: read `src/http/routes/health.ts` and confirm it reads the count from the store.
- Failure policy: stop and return GUIDANCE_INSUFFICIENT if design or extra files are needed.
"""

ESCALATION_NEEDS_FILE = """\
**Escalation context (approved by the user).** Machoke returned `GUIDANCE_INSUFFICIENT: the health handler is not in Files`. The user approved escalation to a last-resort executor but did NOT widen Files. Complete what can be completed inside Files if that alone satisfies the Target state; otherwise fail with a precise reason naming the file the intent requires.

"""

FRONT = """---
max_turns: 12
timeout_seconds: 480
allowed_tools: [Agent, Read, Write, Edit]
plugins: [../../..]
model: opus
runs: 3
---
"""


def fixture_block(files: dict[str, str]) -> str:
    return "\n".join(f"`{p}`:\n\n```ts\n{c.rstrip()}\n```\n" for p, c in files.items())


def apply_prompt(files: dict[str, str], contract: str, preface: str) -> str:
    return f"""\
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

{fixture_block(files)}
Step 2 — execute the contract below with a sub-agent. Do not execute it yourself and do not edit the files after Step 1. Conventions for the executor: no commits, current branch, touch only the contract's Files, perform the Verification by reading the file. Relay the sub-agent's return verbatim and nothing else: one line per operation, then exactly one verdict line, which is either `OK — S<N> done` or `failed: <precise reason>`, then a `Deviations:` list detailing how execution differed from the contract (write `Deviations: none` if there were none).

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


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Machamp\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Machamp\nmin: 0\nmax: 0\narm: both\n---\n"
VERDICT = r"^`?(OK — S\d+ done|failed: .+?)`?\s*$"
OK_VERDICT = r"^`?OK — S\d+ done`?\s*$"
FAILED_VERDICT = r"^`?failed: "
DEVIATIONS = r"^\W*Deviations:?\W*"


def fire_case(slug: str, files: dict[str, str], contract: str, preface: str, created_total: int, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + apply_prompt(files, contract, preface))
    grader(case, "strict-single-verdict", regex(VERDICT, match="count:1", flags="m"))
    grader(case, "deviations-section", regex(DEVIATIONS, flags="m"))
    grader(case, "no-file-dump", regex(r"private readonly sessions = new Map", match="not_contains"))
    grader(case, "only-declared-files-created", regex(r"^\S+$", match=f"count:{created_total}", flags="m", target="files"))
    grader(case, "routed-to-machamp", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


BOTH = {STORE_PATH: STORE_AFTER_S1, MW_PATH: MW_DRIFTED}

# 01 — exact contract, intent clear, operation does not apply: complete it in the file's idiom
fire_case(
    "machamp-01-complete-drifted-exact", BOTH, EXACT_S2, ESCALATION, created_total=2,
    extra={
        "verdict-ok": regex(OK_VERDICT, flags="m"),
        "mw-sweeps-before-lookup": file_regex(MW_PATH, r"store\.evictIdle\(now\);[\s\S]{0,120}const session = lookup\(store, req\);"),
        "mw-touches-after-check": file_regex(MW_PATH, r'if \(!session\) return res\.status\(401\)\.json\(\{ error: "unauthenticated" \}\);\n\s*store\.touch\(session\.id, now\);'),
        "mw-keeps-json-body-and-helper": file_regex(MW_PATH, r"\.end\(\)", match="not_contains"),
        "mw-helper-intact": file_regex(MW_PATH, r"function lookup\(store: SessionStore, req: Request\)"),
        "store-untouched": file_regex(STORE_PATH, r"size\(\): number \{\n    return this\.sessions\.size;"),
        "deviations-name-adaptation": regex(r"Deviations:[\s\S]*(lookup|helper|\.json|\.end\(\)|session\.id)", flags="i"),
        "completion-is-faithful": llm("""
The answer is a last-resort executor's return for an exact contract whose Before block no longer exists because the session lookup moved into a `lookup(store, req)` helper and the 401 body changed. All claims must hold to pass.

1. The verdict is `OK — S<N> done` and the middleware now calls `store.evictIdle(now)` with `now = clock.now()` before the lookup, and `store.touch(<the found session's id>, now)` after the `!session` check, while keeping the `lookup` helper and the `.json({ error: "unauthenticated" })` body.
2. The Deviations list names how execution differed from the literal operation (the helper, the id source, the 401 body), not "none".
3. No file other than the middleware was edited, and the design (helper + middleware) was not restructured.
"""),
    },
)

# 02 — guided contract naming a method that does not exist; the user confirmed the intent
fire_case(
    "machamp-02-renamed-method-intent", BOTH, GUIDED_RENAMED, ESCALATION_RENAMED, created_total=2,
    extra={
        "verdict-ok": regex(OK_VERDICT, flags="m"),
        "log-line-extended": file_regex(STORE_PATH, r"logger\.debug\(`session evicted: \$\{id\} \(user \$\{record\.userId\}\)`\)"),
        "no-sweep-method-added": file_regex(STORE_PATH, r"sweep\(", match="not_contains"),
        "mw-untouched": file_regex(MW_PATH, r"evictIdle", match="not_contains"),
        "deviation-names-rename": regex(r"Deviations:[\s\S]*(sweep|evictIdle|name)", flags="i"),
    },
)

# 03 — the intent genuinely needs a file outside Files: fail precisely, no partial hack
fire_case(
    "machamp-03-needs-undeclared-file", BOTH, GUIDED_NEEDS_FILE, ESCALATION_NEEDS_FILE, created_total=2,
    extra={
        "verdict-failed": regex(FAILED_VERDICT, flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "names-health-file": regex(r"health", flags="i"),
        "no-health-file-created": "---\ntype: file_exists\npath: src/http/routes/health.ts\nexists: false\n---\n",
        "fails-precisely": llm("""
The answer is a last-resort executor's return for a contract whose Target state (a `/health` field) requires editing `src/http/routes/health.ts`, which is not in Files and does not exist in the tree. All claims must hold to pass.

1. The verdict is `failed: <reason>` and the reason names the health handler / file as outside Files (a scope change that belongs to the plan).
2. It did not create the health file and did not invent an alternative endpoint. Any partial edit inside `SessionStore` is acceptable; the verdict is still `failed`.
"""),
    },
)

# 04 — escalation where the contract's Invariant conflicts with the intent: must fail, not "improve"
INVARIANT_CONFLICT = EXACT_S2.replace(
    "- Every request that finds a session must call `store.touch` with the same `now` used for the sweep.",
    "- The middleware calls no `SessionStore` method other than `get` (audit rule: only the store's own sweep may mutate it).",
)
fire_case(
    "machamp-04-invariant-conflict", BOTH, INVARIANT_CONFLICT, ESCALATION, created_total=2,
    extra={
        "verdict-failed": regex(FAILED_VERDICT, flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "mw-not-edited": file_regex(MW_PATH, r"evictIdle|touch\(|clock\.now\(\)", match="not_contains"),
        "names-invariant": regex(r"invariant|no `?SessionStore`? method other than `?get`?|only .*get", flags="i"),
        "refuses-to-restructure": llm("""
The answer is a last-resort executor's return for a contract whose After block calls `store.evictIdle` and `store.touch`, but whose Invariants say the middleware may call no `SessionStore` method other than `get`. The two cannot both hold. All claims must hold to pass.

1. The verdict is `failed: <reason>` and the reason names the conflict between the operation and the Invariant.
2. No edit was made to the middleware; the executor did not pick a side or move the sweep elsewhere on its own.
"""),
    },
)


def neg_case(slug: str, prompt: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt)
    grader(case, "not-routed-to-machamp", NOT_ROUTED)
    grader(case, "fixtures-only-created", regex(r"^\S+$", match="count:2", flags="m", target="files"))
    for name, body in extra.items():
        grader(case, name, body)


# 05 — negative: a fresh exact contract that applies cleanly is Machop's, not Machamp's
MW_CLEAN = MW_DRIFTED.replace(
    "function lookup(store: SessionStore, req: Request): SessionRecord | undefined {\n  const sessionId = req.cookies?.sid;\n  return sessionId == undefined ? undefined : store.get(sessionId);\n}\n\n",
    "",
).replace(
    "    const session = lookup(store, req);\n",
    "    const sessionId = req.cookies?.sid;\n    if (sessionId == undefined) return res.status(401).json({ error: \"unauthenticated\" });\n    const session = store.get(sessionId);\n",
).replace("import type { SessionRecord, SessionStore }", "import type { SessionStore }")
assert "lookup(" not in MW_CLEAN
FRESH_EXACT = EXACT_S2.replace('if (!session) return res.status(401).end();', 'if (!session) return res.status(401).json({ error: "unauthenticated" });')
neg_case(
    "machamp-05-neg-fresh-exact-contract",
    apply_prompt({STORE_PATH: STORE_AFTER_S1, MW_PATH: MW_CLEAN}, FRESH_EXACT, "").replace(
        "which is either `OK — S<N> done` or `failed: <precise reason>`, then a `Deviations:` list detailing how execution differed from the contract (write `Deviations: none` if there were none).",
        "in the executor's own verdict vocabulary.",
    ),
    {
        "mw-evicts": file_regex(MW_PATH, r"store\.evictIdle\(now\);"),
    },
)

# 06 — negative: explain the escalation, do not execute
neg_case(
    "machamp-06-neg-explain-escalation",
    f"""\
Step 1 — create the following files with EXACTLY the content shown (Write tool, byte for byte, single trailing newline). Do not create anything else.

{fixture_block(BOTH)}
Step 2 — in one short paragraph, explain why the exact contract below cannot be applied mechanically to this middleware file and what a last-resort executor would have to adapt. Do NOT execute it, do not edit any file, and do not delegate execution to anyone.

---

{EXACT_S2}""",
    {
        "mw-not-edited": file_regex(MW_PATH, r"evictIdle|touch\(", match="not_contains"),
        "no-verdict-line": regex(VERDICT, match="not_contains", flags="m"),
        "explains-drift": regex(r"lookup|helper", flags="i"),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("machamp-")))
