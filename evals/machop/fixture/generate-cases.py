#!/usr/bin/env python3
"""Regenerate the machop-* cases.

Each prompt first lays down fixture files (the runner's prompt.md format has no scaffold
hook), then hands ONE exact execution contract to a sub-agent. Contracts follow the TK-412
plan (../../magneton/fixture/plan-TK-412.md) but use read-based Verification (count lines via Read) because the
sandbox has no toolchain. Re-run after editing.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent

STORE_PATH = "src/cache/session-store.ts"
MW_PATH = "src/http/session-middleware.ts"
TEST_PATH = "src/cache/__tests__/session-store.test.ts"

# Same "before" files as the Mewtwo suite (kept in sync by hand; they are tiny).
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

# Variant for the ambiguous-anchor case: `revoke` duplicates `delete`'s body exactly.
STORE_DUP = STORE_OLD.replace(
    """  delete(id: string): void {
    this.sessions.delete(id);
  }
""",
    """  delete(id: string): void {
    this.sessions.delete(id);
  }

  revoke(id: string): void {
    this.sessions.delete(id);
  }
""",
)
assert STORE_DUP.count("    this.sessions.delete(id);\n  }\n") == 2

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

# ----------------------------------------------------------------------------- contracts
S1_OPS = """\
#### Operations

1. **replace_exact** at `src/cache/session-store.ts:SessionRecord`

**Before:**

```ts
export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
}
```

**After:**

```ts
export const SESSION_IDLE_TTL_MS = Number(process.env.SESSION_IDLE_TTL_MS ?? 1_800_000);

export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
  lastSeenAt: number;
}
```

2. **insert_after_exact** at `src/cache/session-store.ts:SessionStore.get`

**Anchor:**

```ts
  get(id: string): SessionRecord | undefined {
    return this.sessions.get(id);
  }
```

**Insert:**

```ts

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
```
"""


def s1_contract(expected_count: int) -> str:
    return f"""\
### S1 — Add `lastSeenAt`, `touch`, `evictIdle` and the TTL constant to `SessionStore`

- **Execution class:** exact
- **Files:** `src/cache/session-store.ts`
- **Depends on:** none   **Enables:** S2, S3
- **Allowed context:** `src/cache/session-store.ts:SessionRecord`, `src/cache/session-store.ts:SessionStore`
- **Pattern:** `src/cache/rate-limit-store.ts:RateLimitStore.sweep`

#### Preconditions

- The complete Before block of operation 1 occurs exactly once in `src/cache/session-store.ts`.
- The complete anchor of operation 2 occurs exactly once in `src/cache/session-store.ts`.
- `logger` is already imported at the top of `src/cache/session-store.ts`.

{S1_OPS}
#### Invariants

- `SessionStore.create` and `SessionStore.delete` signatures are unchanged.
- No other file is modified.

#### Verification

- Run/check: read `src/cache/session-store.ts` and count the lines containing `lastSeenAt`
- Expect: exactly `{expected_count}` lines.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
"""


S3_CONTRACT = """\
### S3 — Store tests: eviction, touch refresh, default TTL

- **Execution class:** exact
- **Files:** `src/cache/__tests__/session-store.test.ts`
- **Depends on:** S1   **Enables:** none
- **Allowed context:** `src/cache/session-store.ts:SessionStore`
- **Pattern:** `src/cache/__tests__/rate-limit-store.test.ts`

#### Preconditions

- The path `src/cache/__tests__/session-store.test.ts` does not exist.

#### Operations

1. **create_file** at `src/cache/__tests__/session-store.test.ts`

**Content:**

```ts
import { describe, expect, it, vi } from "vitest";
import { SESSION_IDLE_TTL_MS, SessionStore } from "../session-store";
import { logger } from "../../lib/logger";

const record = (id: string, lastSeenAt: number) => ({
  id,
  userId: `u-${id}`,
  createdAt: lastSeenAt,
  lastSeenAt,
});

describe("SessionStore idle eviction", () => {
  it("evicts a session idle longer than the TTL and logs its id", () => {
    const store = new SessionStore();
    const debug = vi.spyOn(logger, "debug");
    store.create(record("a", 0));
    store.evictIdle(SESSION_IDLE_TTL_MS + 1);
    expect(store.get("a")).toBeUndefined();
    expect(debug).toHaveBeenCalledWith("session evicted: a");
  });

  it("keeps a session touched within the TTL", () => {
    const store = new SessionStore();
    store.create(record("b", 0));
    store.touch("b", 1000);
    store.evictIdle(SESSION_IDLE_TTL_MS + 500);
    expect(store.get("b")?.lastSeenAt).toBe(1000);
  });

  it("defaults the TTL to 30 minutes", () => {
    expect(SESSION_IDLE_TTL_MS).toBe(1_800_000);
  });
});
```

#### Invariants

- No production file is modified.

#### Verification

- Run/check: read `src/cache/__tests__/session-store.test.ts` and count the lines containing `it(`
- Expect: exactly `3` lines.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
"""

S2_CONTRACT = """\
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

S5_DUP_CONTRACT = """\
### S5 — Log every session deletion

- **Execution class:** exact
- **Files:** `src/cache/session-store.ts`
- **Depends on:** none   **Enables:** none
- **Allowed context:** `src/cache/session-store.ts:SessionStore.delete`
- **Pattern:** `src/cache/rate-limit-store.ts:RateLimitStore.clear`

#### Preconditions

- The complete Before block occurs exactly once in `src/cache/session-store.ts`.
- `logger` is already imported at the top of `src/cache/session-store.ts`.

#### Operations

1. **replace_exact** at `src/cache/session-store.ts:SessionStore.delete`

**Before:**

```ts
    this.sessions.delete(id);
  }
```

**After:**

```ts
    this.sessions.delete(id);
    logger.debug(`session deleted: ${id}`);
  }
```

#### Invariants

- No method signature changes.

#### Verification

- Run/check: read `src/cache/session-store.ts` and count the lines containing `session deleted`
- Expect: exactly `1` line.

#### Failure policy

Stop without editing and return `PRECONDITION_FAILED: <condition>`.
"""

# Files lists only the store, but operation 2 edits the middleware -> CONTRACT_INVALID.
S6_INVALID_CONTRACT = s1_contract(3).replace(
    "### S1 — Add `lastSeenAt`, `touch`, `evictIdle` and the TTL constant to `SessionStore`",
    "### S6 — Add idle eviction to the store and wire it into the middleware",
).replace(
    "#### Invariants",
    """3. **replace_exact** at `src/http/session-middleware.ts:sessionMiddleware`

**Before:**

```ts
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
```

**After:**

```ts
    const now = clock.now();
    store.evictIdle(now);
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    store.touch(sessionId, now);
```

#### Invariants""",
)
assert "S6" in S6_INVALID_CONTRACT and "3. **replace_exact**" in S6_INVALID_CONTRACT


# ----------------------------------------------------------------------------- plumbing
FRONT = """---
max_turns: 12
timeout_seconds: 240
allowed_tools: [Agent, Read, Write, Edit]
plugins: [../../..]
model: sonnet
runs: 5
---
"""


def fixture_block(files: dict[str, str]) -> str:
    parts = []
    for path, content in files.items():
        parts.append(f"`{path}`:\n\n```ts\n{content.rstrip()}\n```\n")
    return "\n".join(parts)


def apply_prompt(files: dict[str, str], contract: str) -> str:
    return f"""\
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

{fixture_block(files)}
Step 2 — apply the execution contract below with a sub-agent. Do not apply it yourself and do not edit the files after Step 1. Conventions for the executor: no commits, current branch, touch only the contract's Files, perform the contract's Verification by reading the file and compare the observed count to the expected value. Relay the sub-agent's return verbatim and nothing else: one line per operation, then exactly one verdict line, which is one of `OK — S<N> done`, `PRECONDITION_FAILED: <condition>`, `VERIFICATION_FAILED: <observed result>`, or `CONTRACT_INVALID: <reason>`.

---

{contract}"""


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


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Machop\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Machop\nmin: 0\nmax: 0\narm: both\n---\n"

VERDICT = r"^`?(OK — S\d+ done|PRECONDITION_FAILED: .+?|VERIFICATION_FAILED: .+?|CONTRACT_INVALID: .+?)`?\s*$"
ANY_VERDICT_FORM = r"^`?(OK — S\d+ done|PRECONDITION_FAILED:|VERIFICATION_FAILED:|CONTRACT_INVALID:)"
OK_VERDICT = r"^`?OK — S\d+ done`?\s*$"
OLD_INTERFACE = r"export interface SessionRecord \{\n  id: string;\n  userId: string;\n  createdAt: number;\n\}"


def fire_case(slug: str, files: dict[str, str], contract: str, created_total: int, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + apply_prompt(files, contract))
    grader(case, "strict-single-verdict", regex(VERDICT, match="count:1", flags="m"))
    grader(case, "no-file-dump", regex(r"private readonly sessions = new Map", match="not_contains"))
    grader(case, "only-declared-files-created", regex(r"^\S+$", match=f"count:{created_total}", flags="m", target="files"))
    grader(case, "routed-to-machop", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def neg_case(slug: str, prompt: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt)
    grader(case, "not-routed-to-machop", NOT_ROUTED)
    grader(case, "no-verdict-line", regex(ANY_VERDICT_FORM, match="not_contains", flags="m"))
    grader(case, "fixtures-only-created", regex(r"^\S+$", match="count:2", flags="m", target="files"))
    grader(case, "store-not-edited", file_regex(STORE_PATH, r"lastSeenAt|evictIdle", match="not_contains"))
    for name, body in extra.items():
        grader(case, name, body)


BOTH = {STORE_PATH: STORE_OLD, MW_PATH: MW_OLD}

# 01 — S1 applies cleanly
fire_case(
    "machop-01-replace-and-insert", BOTH, s1_contract(3), created_total=2,
    extra={
        "verdict-ok": regex(r"^`?OK — S1 done", flags="m"),
        "store-has-field": file_regex(STORE_PATH, r"lastSeenAt: number;"),
        "store-has-constant": file_regex(STORE_PATH, r"export const SESSION_IDLE_TTL_MS"),
        "store-has-evict": file_regex(STORE_PATH, r"evictIdle\(now: number\): void \{"),
        "store-old-block-gone": file_regex(STORE_PATH, OLD_INTERFACE, match="not_contains"),
        "store-untouched-parts": file_regex(STORE_PATH, r"size\(\): number \{\n    return this\.sessions\.size;"),
        "middleware-untouched": file_regex(MW_PATH, r"evictIdle|touch\(", match="not_contains"),
    },
)

# 02 — S3 create_file
STORE_AFTER_S1 = STORE_OLD.replace(
    "export interface SessionRecord {\n  id: string;\n  userId: string;\n  createdAt: number;\n}",
    "export const SESSION_IDLE_TTL_MS = Number(process.env.SESSION_IDLE_TTL_MS ?? 1_800_000);\n\nexport interface SessionRecord {\n  id: string;\n  userId: string;\n  createdAt: number;\n  lastSeenAt: number;\n}",
).replace(
    "  get(id: string): SessionRecord | undefined {\n    return this.sessions.get(id);\n  }\n",
    "  get(id: string): SessionRecord | undefined {\n    return this.sessions.get(id);\n  }\n\n  touch(id: string, now: number): void {\n    const record = this.sessions.get(id);\n    if (record) record.lastSeenAt = now;\n  }\n\n  evictIdle(now: number): void {\n    for (const [id, record] of this.sessions) {\n      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {\n        this.sessions.delete(id);\n        logger.debug(`session evicted: ${id}`);\n      }\n    }\n  }\n",
)
assert STORE_AFTER_S1.count("lastSeenAt") == 3 and "evictIdle" in STORE_AFTER_S1

fire_case(
    "machop-02-create-file", {STORE_PATH: STORE_AFTER_S1, MW_PATH: MW_OLD}, S3_CONTRACT, created_total=3,
    extra={
        "verdict-ok": regex(r"^`?OK — S3 done", flags="m"),
        "test-file-exists": f"---\ntype: file_exists\npath: {TEST_PATH}\nexists: true\n---\n",
        "test-has-describe": file_regex(TEST_PATH, r'describe\("SessionStore idle eviction"'),
        "test-has-ttl-case": file_regex(TEST_PATH, r"SESSION_IDLE_TTL_MS \+ 1\)"),
        "store-untouched": file_regex(STORE_PATH, r"session deleted|touch\(id: string, now: number, ", match="not_contains"),
    },
)

# 03 — S2 against a drifted middleware (Before block does not match)
fire_case(
    "machop-03-precondition-drift", BOTH, S2_CONTRACT, created_total=2,
    extra={
        "verdict-precondition-failed": regex(r"^`?PRECONDITION_FAILED:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "middleware-not-edited": file_regex(MW_PATH, r"evictIdle|clock\.now\(\)|touch\(", match="not_contains"),
        "middleware-drift-intact": file_regex(MW_PATH, r'if \(!session\) return res\.status\(401\)\.json\(\{ error: "unauthenticated" \}\);'),
    },
)

# 04 — Before block occurs twice
fire_case(
    "machop-04-ambiguous-anchor", {STORE_PATH: STORE_DUP, MW_PATH: MW_OLD}, S5_DUP_CONTRACT, created_total=2,
    extra={
        "verdict-precondition-failed": regex(r"^`?PRECONDITION_FAILED:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "store-not-edited": file_regex(STORE_PATH, r"session deleted", match="not_contains"),
        "both-copies-intact": file_regex(STORE_PATH, r"    this\.sessions\.delete\(id\);\n  \}", match="count:2"),
    },
)

# 05 — S1 applies, Verification cannot hold (expects 4, true count is 3)
fire_case(
    "machop-05-verification-fails", BOTH, s1_contract(4), created_total=2,
    extra={
        "verdict-verification-failed": regex(r"^`?VERIFICATION_FAILED:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "store-edit-applied": file_regex(STORE_PATH, r"evictIdle\(now: number\): void \{"),
        "observed-result-stated": llm("""
The answer is an executor's return for an exact contract whose Verification expected `4` lines containing `lastSeenAt` but the file actually has `3`. All claims must hold to pass.

1. The single verdict line is `VERIFICATION_FAILED: ...` and it states the observed result (the count 3) against the expected 4.
2. It does not claim success, does not silently adjust the expectation, and does not invent a fix.
"""),
    },
)

# 06 — operation on a file not listed under Files
fire_case(
    "machop-06-contract-invalid", BOTH, S6_INVALID_CONTRACT, created_total=2,
    extra={
        "verdict-contract-invalid": regex(r"^`?CONTRACT_INVALID:", flags="m"),
        "not-ok": regex(OK_VERDICT, match="not_contains", flags="m"),
        "middleware-not-edited": file_regex(MW_PATH, r"evictIdle|clock\.now\(\)|touch\(", match="not_contains"),
        "store-not-edited": file_regex(STORE_PATH, r"lastSeenAt|evictIdle", match="not_contains"),
    },
)

# 07 — negative: explain, do not apply
neg_case(
    "machop-07-neg-explain-contract",
    f"""\
Step 1 — create the following files with EXACTLY the content shown (Write tool, byte for byte, single trailing newline). Do not create anything else.

{fixture_block(BOTH)}
Step 2 — explain in plain prose, in one short paragraph, what the execution contract below would change in the working tree and why the plan needs it. Do NOT apply it, do not edit any file, and do not delegate the application to anyone.

---

{s1_contract(3)}""",
    {"explains-change": regex(r"lastSeenAt[\s\S]*evictIdle|evictIdle[\s\S]*lastSeenAt")},
)

# 08 — negative: author a contract
neg_case(
    "machop-08-neg-author-contract",
    f"""\
Step 1 — create the following files with EXACTLY the content shown (Write tool, byte for byte, single trailing newline). Do not create anything else.

{fixture_block(BOTH)}
Step 2 — draft, as text only, an exact execution contract (Execution class: exact; Files; Preconditions; one `replace_exact` operation with complete Before/After blocks; Invariants; Verification; Failure policy) that makes `SessionStore.size()` return `0` when the map is empty without touching the `Map` type. Do not apply anything and do not edit any file.

---
""",
    {"drafted-contract": regex(r"Execution class:\*?\*? ?exact[\s\S]*Preconditions[\s\S]*Before")},
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("machop-")))
