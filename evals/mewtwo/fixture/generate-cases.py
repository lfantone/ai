#!/usr/bin/env python3
"""Regenerate the mewtwo-* cases.

A synthetic TypeScript PR implements the shared TK-412 plan
(../../magneton/fixture/plan-TK-412.md). Each fire case is a variant of the PR's new-file
contents; the unified diff is produced with difflib so hunk headers are real, and every
grader line number is derived from the new-file text (asserted unique). Re-run after edits.
"""
from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
PLAN = (SUITE.parent / "magneton" / "fixture" / "plan-TK-412.md").read_text()


def section(md: str, number: int) -> str:
    m = re.search(rf"^## {number}\. .*?(?=^## \d+\. |\Z)", md, re.S | re.M)
    assert m, f"section {number} not found"
    return m.group(0).strip()


# ----------------------------------------------------------------------------- base files
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

  // TODO(TK-412): evict idle sessions here
  // see docs/sessions.md for the intended TTL semantics

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


TTL_ROBUST = """\
const parsedIdleTtlMs = Number(process.env.SESSION_IDLE_TTL_MS);
export const SESSION_IDLE_TTL_MS =
  Number.isFinite(parsedIdleTtlMs) && parsedIdleTtlMs > 0
    ? parsedIdleTtlMs
    : 1_800_000;
"""


def store_new(*, evict_body: str, ttl: str = TTL_ROBUST) -> str:
    return f"""\
import {{ logger }} from "../lib/logger";

{ttl}
export interface SessionRecord {{
  id: string;
  userId: string;
  createdAt: number;
  lastSeenAt: number;
}}

export class SessionStore {{
  private readonly sessions = new Map<string, SessionRecord>();

  create(record: Omit<SessionRecord, "lastSeenAt">): void {{
    this.sessions.set(record.id, {{ ...record, lastSeenAt: record.createdAt }});
  }}

  get(id: string): SessionRecord | undefined {{
    return this.sessions.get(id);
  }}

  touch(id: string, now: number): void {{
    const record = this.sessions.get(id);
    if (record) record.lastSeenAt = now;
  }}

{evict_body}
  delete(id: string): void {{
    this.sessions.delete(id);
  }}

  size(): number {{
    return this.sessions.size;
  }}
}}
"""


EVICT_CLEAN = """\
  evictIdle(now: number): void {
    for (const [id, record] of this.sessions) {
      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {
        this.sessions.delete(id);
        logger.debug(`session evicted: ${id}`);
      }
    }
  }
"""

EVICT_CREATED_AT = EVICT_CLEAN.replace("now - record.lastSeenAt >", "now - record.createdAt >")
EVICT_INVERTED = EVICT_CLEAN.replace("now - record.lastSeenAt >", "now - record.lastSeenAt <")
EVICT_NO_LOG = EVICT_CLEAN.replace("        logger.debug(`session evicted: ${id}`);\n", "")
EVICT_DATE_NOW = """\
  evictIdle(): void {
    const now = Date.now();
    for (const [id, record] of this.sessions) {
      if (now - record.lastSeenAt > SESSION_IDLE_TTL_MS) {
        this.sessions.delete(id);
        console.log(`session evicted: ${id}`);
      }
    }
  }
"""


def mw_new(*, order: str = "clean", evict_call: str = "store.evictIdle(now);") -> str:
    if order == "clean":
        body = f"""\
    const now = clock.now();
    {evict_call}
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({{ error: "unauthenticated" }});
    store.touch(sessionId, now);
"""
    else:  # touch-before-evict bug
        body = f"""\
    const now = clock.now();
    store.touch(sessionId, now);
    {evict_call}
    const session = store.get(sessionId);
    if (!session) return res.status(401).json({{ error: "unauthenticated" }});
"""
    return f"""\
import type {{ NextFunction, Request, Response }} from "express";
import type {{ Clock }} from "../lib/clock";
import type {{ SessionStore }} from "../cache/session-store";

export function sessionMiddleware(store: SessionStore, clock: Clock) {{
  return (req: Request, res: Response, next: NextFunction) => {{
    const sessionId = req.cookies?.sid;
    if (sessionId == undefined) return res.status(401).json({{ error: "unauthenticated" }});
{body}    req.session = session;
    next();
  }};
}}
"""


STORE_TEST = """\
import { afterEach, describe, expect, it, vi } from "vitest";
import { SESSION_IDLE_TTL_MS, SessionStore } from "../session-store";
import { logger } from "../../lib/logger";

const record = (id: string, createdAt: number) => ({
  id,
  userId: `u-${id}`,
  createdAt,
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
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

  it("falls back to the default when the env var is empty", async () => {
    vi.stubEnv("SESSION_IDLE_TTL_MS", "");
    vi.resetModules();
    const fresh = await import("../session-store");
    expect(fresh.SESSION_IDLE_TTL_MS).toBe(1_800_000);
  });
});
"""

MW_TEST = """\
import { describe, expect, it, vi } from "vitest";
import { SessionStore } from "../../cache/session-store";
import { sessionMiddleware } from "../session-middleware";

describe("sessionMiddleware", () => {
  it("refreshes lastSeenAt on every authenticated request", () => {
    const store = new SessionStore();
    store.create({ id: "s1", userId: "u1", createdAt: 0 });
    const clock = { now: () => 5000 };
    const mw = sessionMiddleware(store, clock);
    const req = { cookies: { sid: "s1" } } as any;
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;
    const next = vi.fn();

    mw(req, res, next);

    expect(store.get("s1")?.lastSeenAt).toBe(5000);
    expect(next).toHaveBeenCalledOnce();
  });

  it("returns 401 for a session evicted by the sweep", () => {
    const store = new SessionStore();
    store.create({ id: "old", userId: "u2", createdAt: 0 });
    const clock = { now: () => 10_000_000 };
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;
    const next = vi.fn();

    const mw = sessionMiddleware(store, clock);
    mw({ cookies: { sid: "old" } } as any, res, next);

    expect(res.status).toHaveBeenCalledWith(401);
    expect(next).not.toHaveBeenCalled();
    expect(store.get("old")).toBeUndefined();
  });
});
"""

STORE_PATH = "src/cache/session-store.ts"
MW_PATH = "src/http/session-middleware.ts"
TEST_PATH = "src/cache/__tests__/session-store.test.ts"
MW_TEST_PATH = "src/http/__tests__/session-middleware.test.ts"


# ----------------------------------------------------------------------------- diff helpers
def udiff(path: str, old: str, new: str) -> str:
    lines = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}" if old else "/dev/null",
        tofile=f"b/{path}",
        n=3,
    )
    body = "".join(lines)
    return f"diff --git a/{path} b/{path}\n{body}"


def new_line_no(new: str, needle: str) -> int:
    hits = [i + 1 for i, line in enumerate(new.splitlines()) if needle in line]
    assert len(hits) == 1, f"{needle!r} must appear exactly once, found {hits}"
    return hits[0]


def naive_line_no(diff: str, path: str, needle: str) -> int:
    """The number a reviewer gets by counting removed lines too (the classic mistake)."""
    file_diff = diff.split(f"diff --git a/{path} b/{path}")[1].split("diff --git")[0]
    start = None
    count = 0
    for line in file_diff.splitlines():
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
        if m:
            start = int(m.group(1))
            count = 0
            continue
        if start is None:
            continue
        if needle in line and line.startswith("+"):
            return start + count
        count += 1  # counts '-' lines as well: the mistake we want to detect
    raise AssertionError("needle not found in diff")


def accept_line(n: int) -> str:
    """Regex for `:<n>` or a short range that includes n."""
    lo = "|".join(str(x) for x in range(max(1, n - 3), n + 1))
    hi = "|".join(str(x) for x in range(n, n + 4))
    return rf":(?:{n}|(?:{lo})-(?:{hi}))\b"


# ----------------------------------------------------------------------------- case plumbing
FRONT = """---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Agent]
plugins: [../../..]
model: opus
runs: 3
---
"""

REVIEW = """Review this pull request delta with a sub-agent: correctness, ticket coverage, and repository conventions. Do not review it yourself. There is no checkout and no DIFF_PATH in this environment; the full diff is inline in the brief and is the only source. Return the sub-agent's output verbatim and nothing else. It must start with a `## Ticket coverage` section (one line per acceptance criterion: covered / partial / MISSING) and then give findings, each as its own block:

````text
### [<must-fix|recommended|cosmetic>] <short title> — <file>:<new-file line(s)>
**Anchor:** `<verbatim line copied from the + side of the diff>`
**What's wrong:** <1–2 sentences>

```suggestion
<replacement lines only>
```
````

Empty severity buckets are written as `_None._`. Findings must anchor to lines the diff adds or modifies; an omitted acceptance criterion is reported with location `(not in diff — missing)` and a `(not inline — sketch)` suggestion.

---

"""

REPO_BRIEF = """\
## Repository brief (excerpt)
- TypeScript strict mode, Express, vitest. Prettier formatting enforced in CI.
- **Hard rule:** `Date.now()` is forbidden outside `src/lib/clock.ts`. Library code gets the current time either from an injected `Clock` (`src/lib/clock.ts:Clock`, `clock.now(): number`) or as a `now: number` argument supplied by a caller that holds the clock; both forms are compliant.
- The TTL constant is resolved once at module load on purpose (the process is restarted on config change); do not flag that as an issue.
- Logging goes through `src/lib/logger.ts:logger` (`debug`/`info`/`warn`); `console.*` is not used in `src/`.
- Safe path: `SessionStore` is the only owner of the session map; middleware must go through its methods.
- Tests live next to the code under `__tests__/`, one `describe` per unit.
"""

COORDS = """\
## COORDS
owner/repo: acme/app · PR index: 88 · head_sha: 7d3f1a2c9b8e4f5061728394a5b6c7d8e9f0a1b2 · base_ref: main
"""


def impl_brief(files: list[tuple[str, str]]) -> str:
    rows = "\n".join(f"- `{p}` — {what}" for p, what in files)
    return f"## Implementation brief\nPR #88 \"TK-412: expire idle sessions\" — {len(files)} file(s) changed.\n{rows}\n"


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


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Mewtwo\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Mewtwo\nmin: 0\nmax: 0\narm: both\n---\n"

SEV = r"(must-fix|recommended|cosmetic)"
SCOPE_BUCKETS = """
The answer is a code review of a pull request diff. Judge only the two claims below; both must hold to pass.

1. Scope: every finding block whose header ends in `<file>:<line(s)>` has an `**Anchor:**` whose text is a line the diff ADDS (a `+` line in the diff). A finding anchored to an unchanged context line (no leading `+`), or to code that is not in the diff at all, fails this claim. Findings whose header location is `(not in diff — missing)` are exempt: they report an omission and need no anchor.
2. Buckets: the review lists findings under severity headings. If a severity (must-fix, recommended, or cosmetic) has no findings, that heading is present with the literal text `_None._` under it. A severity with one or more findings does not need `_None._`.

Do not judge finding quality, severity choice, or verbosity here; other graders do that.
"""

# A finding header followed, before the next header/section, by no ```suggestion fence.
# Each repetition consumes exactly one full line, so the scan is linear (no backtracking).
MISSING_SUGGESTION = r"^### \[(must-fix|recommended|cosmetic)\][^\n]*\n(?:(?!### \[|## |```suggestion)[^\n]*\n)*(?:(?=### \[|## )|(?!### \[|## |```suggestion)[^\n]*(?![\s\S]))"
EMPTY_SUGGESTION = r"```suggestion\s*\n\s*```"


def context_line_anchor_regex(diff: str) -> str:
    """not_contains pattern: an **Anchor:** equal to an unchanged context line of the diff.

    Encodes Mewtwo's scope rule deterministically: findings may anchor only on `+` lines.
    Context lines too short to be distinctive (braces, blanks) are skipped.
    """
    added = {
        line[1:].strip()
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    }
    ctx = []
    for line in diff.splitlines():
        if line.startswith(("+", "-", "@@", "diff --git", "---", "+++")):
            continue
        body = (line[1:] if line.startswith(" ") else line).strip()
        # skip short lines and any text that is ALSO an added line (an anchor on the added
        # copy is legitimate and the regex cannot tell the two apart)
        if len(body) < 12 or body in added:
            continue
        ctx.append(re.escape(body))
    assert ctx, "diff has no distinctive context lines"
    return r"^\*\*Anchor:\*\*\s*`+\s*(?:" + "|".join(sorted(set(ctx))) + r")\s*`+"


def fire_case(slug: str, brief: str, extra: dict[str, str], diff: str) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + REVIEW + brief.strip() + "\n")
    grader(case, "no-anchor-on-context-line", regex(context_line_anchor_regex(diff), match="not_contains", flags="m"))
    grader(case, "coverage-section-first", regex(r"^## Ticket coverage", flags="m"))
    for i in range(1, 5):
        grader(case, f"covers-ac{i}", regex(rf"^- [^\n]*\bAC{i}\b[^\n]*\b(covered|partial|MISSING|descoped)\b", flags="m"))
    grader(case, "strict-finding-headers", regex(rf"^### (?!\[{SEV}\] [^\n]+ — [^\n]+$)", match="not_contains", flags="m"))
    # Every anchored finding has its **Anchor:** line right under the header; omissions
    # located "(not in diff — missing)" are exempt (Mewtwo must not invent an anchor).
    grader(case, "strict-anchor-follows-header", regex(rf"^### \[{SEV}\](?![^\n]*\(not in diff)[^\n]*\n(?!\*\*Anchor:\*\*)", match="not_contains", flags="m"))
    grader(case, "no-collapsed-findings", regex(rf"^- \[{SEV}\]", match="not_contains", flags="m"))
    grader(case, "suggestion-fence-per-finding", regex(MISSING_SUGGESTION, match="not_contains", flags="m"))
    grader(case, "no-empty-suggestion", regex(EMPTY_SUGGESTION, match="not_contains"))
    grader(case, "routed-to-mewtwo", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def neg_case(slug: str, prompt: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt.strip() + "\n")
    grader(case, "no-review-findings", regex(rf"^### \[{SEV}\]", match="not_contains", flags="m"))
    grader(case, "not-routed-to-mewtwo", NOT_ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def brief(files: list[tuple[str, str]], diff: str) -> str:
    return f"""
## Ticket brief
{section(PLAN, 1)}

{impl_brief(files)}
{REPO_BRIEF}
{COORDS}
## Diff (inline; the only source)

```diff
{diff.rstrip()}
```
"""


CONTEXT_BUG_ANCHOR = regex(r"^\*\*Anchor:\*\*[^\n]*sessionId == undefined", match="not_contains", flags="m")

# ----------------------------------------------------------------------------- 01 two planted bugs
store01 = store_new(evict_body=EVICT_CREATED_AT)
mw01 = mw_new(order="touch-first")
diff01 = udiff(STORE_PATH, STORE_OLD, store01) + udiff(MW_PATH, MW_OLD, mw01)
l_created = new_line_no(store01, "now - record.createdAt >")
l_touch = new_line_no(mw01, "store.touch(sessionId, now);")
fire_case(
    "mewtwo-01-two-planted-bugs",
    brief([(STORE_PATH, "TTL constant, `lastSeenAt`, `touch`, `evictIdle`"), (MW_PATH, "call `evictIdle` and `touch` per request")], diff01),
    diff=diff01,
    extra={
        "finds-createdat-bug": regex(rf"^### \[must-fix\][^\n]*— {re.escape(STORE_PATH)}{accept_line(l_created)}", flags="m"),
        "anchors-createdat-line": regex(r"^\*\*Anchor:\*\*[^\n]*record\.createdAt", flags="m"),
        "finds-touch-order-bug": regex(rf"^### \[must-fix\][^\n]*— {re.escape(MW_PATH)}{accept_line(l_touch)}", flags="m"),
        "no-context-line-finding": CONTEXT_BUG_ANCHOR,
        "diagnoses-both-bugs": llm(f"""
The answer reviews a diff that contains exactly two planted correctness bugs. All claims must hold to pass.

1. It reports as must-fix that `evictIdle` compares `now - record.createdAt` (session age) instead of `now - record.lastSeenAt` (idle time), so an active session is evicted after the TTL regardless of activity, breaking AC3. The suggestion replaces `createdAt` with `lastSeenAt` on that line.
2. It reports as must-fix that the middleware calls `store.touch(sessionId, now)` before `store.evictIdle(now)`, which refreshes an idle session so it is never evicted, breaking AC1. The suggestion reorders the calls (evict, get, then touch) or equivalent.
3. It does not report the pre-existing `sessionId == undefined` check (an unchanged context line) as a finding block; a one-line `Beyond the diff` mention is acceptable.
4. Any additional must-fix finding corresponds to a real defect in the diff. Missing tests may be reported, but at recommended severity (Mewtwo's own severity table), not must-fix.
"""),
    },
)

# ----------------------------------------------------------------------------- 02 missing criterion (no debug log)
store02 = store_new(evict_body=EVICT_NO_LOG)
mw02 = mw_new()
test02 = (
    STORE_TEST.replace('    const debug = vi.spyOn(logger, "debug");\n', "")
    .replace('    expect(debug).toHaveBeenCalledWith("session evicted: a");\n', "")
    .replace('import { logger } from "../../lib/logger";\n', "")
    .replace("afterEach(() => {\n  vi.restoreAllMocks();\n  vi.unstubAllEnvs();\n});\n\n", "")
    .replace(
        """  it("falls back to the default when the env var is empty", async () => {
    vi.stubEnv("SESSION_IDLE_TTL_MS", "");
    vi.resetModules();
    const fresh = await import("../session-store");
    expect(fresh.SESSION_IDLE_TTL_MS).toBe(1_800_000);
  });
""",
        """  it("defaults the TTL to 30 minutes", () => {
    expect(SESSION_IDLE_TTL_MS).toBe(1_800_000);
  });
""",
    )
    .replace("import { afterEach, describe, expect, it, vi }", "import { describe, expect, it }")
)
assert "vi." not in test02 and "logger" not in test02, "case 02 test must not reference vi or logger"
diff02 = udiff(STORE_PATH, STORE_OLD, store02) + udiff(MW_PATH, MW_OLD, mw02) + udiff(TEST_PATH, "", test02)
fire_case(
    "mewtwo-02-missing-criterion",
    brief([(STORE_PATH, "TTL constant, `lastSeenAt`, `touch`, `evictIdle`"), (MW_PATH, "call `evictIdle` and `touch` per request"), (TEST_PATH, "store tests")], diff02),
    diff=diff02,
    extra={
        "ac1-not-covered": regex(r"^- [^\n]*\bAC1\b[^\n]*\b(partial|MISSING)\b", flags="m"),
        "must-fix-names-log": regex(r"^### \[must-fix\][^\n]*(log|debug)", flags="mi"),
        "suggestion-adds-debug-log": regex(r"logger\.debug\(`session evicted: \$\{id\}`\)"),
        "exactly-one-must-fix": regex(r"^### \[must-fix\]", match="count:1", flags="m"),
        "log-omission-fixed": llm("""
The answer reviews a diff whose only defect is an omission: AC1 requires a `debug` log line `session evicted: <id>` when a session is evicted, and the diff never logs anything. All claims must hold to pass.

1. The ticket coverage marks AC1 as partial or MISSING and explains that the eviction log line is absent.
2. There is exactly one must-fix finding, for that omission. Either shape is correct: an inline finding anchored to the eviction block inside `evictIdle` (which the diff adds) whose suggestion inserts `logger.debug(`session evicted: ${id}`)` after the delete, or a finding located `(not in diff — missing)` with a `(not inline — sketch)` suggestion sketching the same call.
3. No other must-fix finding is reported; the rest of the diff is correct. Recommended or cosmetic findings, if any, describe something real (for example the now-unused `logger` import, the test title promising a log assertion it does not make, or missing middleware tests reported as `(not in diff — missing)`).
"""),
    },
)

# ----------------------------------------------------------------------------- 03 clean PR
store03 = store_new(evict_body=EVICT_CLEAN)
mw03 = mw_new()
diff03 = (
    udiff(STORE_PATH, STORE_OLD, store03)
    + udiff(MW_PATH, MW_OLD, mw03)
    + udiff(TEST_PATH, "", STORE_TEST)
    + udiff(MW_TEST_PATH, "", MW_TEST)
)
fire_case(
    "mewtwo-03-clean-pr",
    brief([(STORE_PATH, "TTL constant, `lastSeenAt`, `touch`, `evictIdle`"), (MW_PATH, "call `evictIdle` and `touch` per request"), (TEST_PATH, "store tests"), (MW_TEST_PATH, "middleware tests")], diff03),
    diff=diff03,
    extra={
        **{f"ac{i}-covered": regex(rf"^- [^\n]*\bAC{i}\b[^\n]*\bcovered\b", flags="m") for i in range(1, 5)},
        "no-must-fix": regex(r"^### \[must-fix\]", match="not_contains", flags="m"),
        "empty-bucket-marker": regex(r"_None\._"),
        "no-context-line-finding": CONTEXT_BUG_ANCHOR,
        "no-invented-bugs": llm("""
The answer reviews a diff that correctly implements every acceptance criterion. All claims must hold to pass.

1. The ticket coverage marks all four criteria as covered, each with a file:line pointer into the diff.
2. There are no must-fix findings, and the must-fix bucket is written as `_None._`.
3. Any recommended or cosmetic finding points at a real, defensible improvement on a line the diff adds (for example test coverage for the middleware, or the O(n) sweep cost), not an invented bug, and not the pre-existing `sessionId == undefined` context line.
"""),
    },
)

# ----------------------------------------------------------------------------- 04 line-shift hunks
store04 = store_new(evict_body=EVICT_INVERTED)
diff04 = udiff(STORE_PATH, STORE_OLD, store04)
l_inv = new_line_no(store04, "now - record.lastSeenAt <")
naive = naive_line_no(diff04, STORE_PATH, "now - record.lastSeenAt <")
assert naive != l_inv, "the removed TODO lines must shift the naive count"
extra04 = {
    "finds-inverted-comparison": regex(rf"^### \[must-fix\][^\n]*— {re.escape(STORE_PATH)}{accept_line(l_inv)}", flags="m"),
    "anchors-verbatim-plus-line": regex(r"^\*\*Anchor:\*\* `\s*if \(now - record\.lastSeenAt < SESSION_IDLE_TTL_MS\) \{`", flags="m"),
    "not-old-side-count": regex(rf"— {re.escape(STORE_PATH)}:{naive}\b", match="not_contains"),
    "explains-inversion": llm("""
The answer reviews a diff with exactly one planted bug: `evictIdle` uses `<` instead of `>`, so it evicts every session that is still fresh and keeps the idle ones. All claims must hold to pass.

1. A must-fix finding identifies the inverted comparison on the `if (now - record.lastSeenAt < SESSION_IDLE_TTL_MS)` line and its suggestion changes only that comparison, to `>` or `>=`.
2. The finding's `**Anchor:**` is that line copied verbatim from the `+` side of the diff (not the removed TODO comment lines, not an old-side line).
3. No other must-fix is reported. The middleware wiring is descoped per the implementation brief, so its absence is reported as descoped or at most recommended, not must-fix; the middleware file is not reviewed.
"""),
}
fire_case(
    "mewtwo-04-line-shift-hunks",
    brief([(STORE_PATH, "TTL constant, `lastSeenAt`, `touch`, `evictIdle`; middleware wiring lands in a follow-up PR (descoped here, see PR description)")], diff04),
    diff=diff04,
    extra=extra04,
)

# ----------------------------------------------------------------------------- 05 hard-rule violation
store05 = store_new(evict_body=EVICT_DATE_NOW)
mw05 = mw_new(evict_call="store.evictIdle();")
diff05 = udiff(STORE_PATH, STORE_OLD, store05) + udiff(MW_PATH, MW_OLD, mw05)
l_date = new_line_no(store05, "const now = Date.now();")
l_console = new_line_no(store05, "console.log(`session evicted")
fire_case(
    "mewtwo-05-hard-rule-violation",
    brief([(STORE_PATH, "TTL constant, `lastSeenAt`, `touch`, `evictIdle`"), (MW_PATH, "call `evictIdle` and `touch` per request")], diff05),
    diff=diff05,
    extra={
        "date-now-is-must-fix": regex(rf"^### \[must-fix\][^\n]*— {re.escape(STORE_PATH)}{accept_line(l_date)}", flags="m"),
        "console-log-flagged": regex(rf"^### \[{SEV}\][^\n]*— {re.escape(STORE_PATH)}{accept_line(l_console)}", flags="m"),
        "no-context-line-finding": CONTEXT_BUG_ANCHOR,
        "severities-and-fix": llm("""
The answer reviews a diff whose logic is correct but which breaks two repository conventions from the brief. All claims must hold to pass.

1. `const now = Date.now();` inside `evictIdle` is reported as must-fix, citing the repository's hard rule that library code uses the injected `Clock` and never `Date.now()`. The suggestion removes `Date.now()`, for example by giving `evictIdle` a `now: number` parameter that the middleware passes from `clock.now()` (the middleware call `store.evictIdle();` then needs `now`; a sketch or a second finding for it is acceptable).
2. `console.log(...)` instead of `logger.debug(...)` is reported with a suggestion using `logger.debug`. Recommended severity (convention drift) or must-fix (because AC1 names a `debug` log line) are both acceptable.
3. No must-fix is reported for anything else; the eviction comparison itself is correct and is not flagged as a bug.
"""),
    },
)

# ----------------------------------------------------------------------------- 06 negative: changelog summary
neg_case(
    "mewtwo-06-neg-changelog-summary",
    f"""
Summarize what this diff changes in five bullets for the changelog. Describe the behavior change in plain language; do not review it, do not assess correctness, and do not produce findings.

```diff
{diff03.rstrip()}
```
""",
    {
        "mentions-ttl": regex(r"SESSION_IDLE_TTL_MS|idle|TTL", flags="i"),
        "changelog-only": llm("""
The answer is a changelog summary of a diff. All claims must hold to pass.

1. It contains about five bullets (four to six) describing the changes: a configurable idle TTL constant, a `lastSeenAt` field on sessions, `touch` and `evictIdle` on the store, the middleware evicting idle sessions and refreshing `lastSeenAt` on each request, and new store tests.
2. It contains no review findings, no severity labels, no `**Anchor:**` lines, and no suggestion blocks.
"""),
    },
)

# ----------------------------------------------------------------------------- 07 negative: hunk header arithmetic
neg_case(
    "mewtwo-07-neg-hunk-header",
    """
In a unified diff, which new-file line numbers does the hunk header `@@ -12,7 +12,9 @@` cover, and how do you count them? Answer in two or three sentences; this is not a code review.
""",
    {
        "names-range": regex(r"\b12\b[^\n]*\b20\b"),
        "arithmetic": llm("""
The answer explains a unified-diff hunk header. All claims must hold to pass.

1. It states that the new-file side starts at line 12 and spans 9 lines, so the hunk covers new-file lines 12 through 20.
2. It explains that new-file lines are counted from `+` and context lines only, and that `-` (removed) lines do not count toward new-file numbering.
3. It does not produce any review findings.
"""),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("mewtwo-")))
print(f"lines: createdAt={l_created} touch={l_touch} inverted={l_inv} (naive {naive}) dateNow={l_date} console={l_console}")
