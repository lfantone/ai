#!/usr/bin/env python3
"""Regenerate the alakazam-* cases.

A synthetic TypeScript PR adds a "session export" admin endpoint and a login handler to the
TK-412 world. Each fire case is a variant of the new files with planted security defects; the
diff is produced with difflib and every grader line number is derived from the new-file text.
The threat profile (Growlithe's output) is inline. Re-run after editing.
"""
from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent

# ----------------------------------------------------------------------------- base files (before the PR)
SAFE_PATHS_OLD = """\
import { z } from "zod";

// Existing safe paths — new code is expected to use these, never re-implement them.
export const sessionIdSchema = z.string().regex(/^[A-Za-z0-9_-]{16,64}$/);
export const userIdSchema = z.string().regex(/^u-[a-z0-9]{6,12}$/);

export function requireAdmin(req: { user?: { role?: string } }): void {
  if (req.user?.role !== "admin") throw Object.assign(new Error("forbidden"), { status: 403 });
}

export function redactSession<T extends { token?: string }>(record: T): Omit<T, "token"> {
  const { token: _token, ...rest } = record;
  return rest;
}

// Verifies a password against the stored hash; throws a 401 error on mismatch. The only credential check.
export async function verifyPassword(userId: string, password: unknown): Promise<void> {
  if (!(await passwordMatches(userId, String(password ?? "")))) throw Object.assign(new Error("unauthenticated"), { status: 401 });
}
"""

ROUTES_INDEX_OLD = """\
import type { Express } from "express";
import { meHandler } from "./me";

// server.ts mounts sessionMiddleware on /api/* (populating req.user) before calling registerRoutes.
export function registerRoutes(app: Express): void {
  app.get("/api/me", meHandler);
}
"""

# ----------------------------------------------------------------------------- new files (variants)
def export_route(*, authz: str, id_check: str, redact: str, query: str) -> str:
    return f"""\
import type {{ Request, Response }} from "express";
import {{ db }} from "../../lib/db";
import {{ logger }} from "../../lib/logger";
import {{ redactSession, requireAdmin, sessionIdSchema }} from "../../lib/safe-paths";

// GET /api/admin/sessions/:id/export — admin export of one session with its audit trail.
export async function exportSessionHandler(req: Request, res: Response): Promise<void> {{
{authz}
{id_check}
  const rows = await db.query({query});
  const session = rows[0];
  if (!session) {{
    res.status(404).json({{ error: "not_found" }});
    return;
  }}
  logger.info(`session export by ${{req.user?.id}} for ${{sessionId}}`);
  res.json({redact});
}}
"""


AUTHZ_OK = "  requireAdmin(req);"
AUTHZ_MISSING = "  // admin-only: enforced by the /api/admin router prefix (see routes/index.ts)"
ID_OK = "  const sessionId = sessionIdSchema.parse(req.params.id);"
ID_UNCHECKED = "  const sessionId = req.params.id;"
QUERY_PARAM = '"SELECT * FROM sessions WHERE id = $1", [sessionId]'
QUERY_CONCAT = '`SELECT * FROM sessions WHERE id = \'${sessionId}\'`'
REDACT_OK = "redactSession(session)"
REDACT_RAW = "session"

ROUTES_INDEX_NEW = """\
import type { Express } from "express";
import { meHandler } from "./me";
import { exportSessionHandler } from "./admin/export-session";

// server.ts mounts sessionMiddleware on /api/* (populating req.user) before calling registerRoutes.
export function registerRoutes(app: Express): void {
  app.get("/api/me", meHandler);
  app.get("/api/admin/sessions/:id/export", exportSessionHandler);
}
"""

LOGIN_OK = """\
import type { Request, Response } from "express";
import { logger } from "../lib/logger";
import { userIdSchema, verifyPassword } from "../lib/safe-paths";
import { sessionStore } from "../cache/session-store";
import { issueToken } from "../lib/tokens";

export async function loginHandler(req: Request, res: Response): Promise<void> {
  const userId = userIdSchema.parse(req.body?.user);
  await verifyPassword(userId, req.body?.password);
  const token = issueToken(userId);
  sessionStore.create({ id: token.sessionId, userId, token: token.value, createdAt: Date.now() });
  logger.info(`login ok for ${userId}`);
  res.cookie("sid", token.value, { httpOnly: true, secure: true, sameSite: "lax" });
  res.status(204).end();
}
"""
LOGIN_LOGS_TOKEN = LOGIN_OK.replace(
    "  logger.info(`login ok for ${userId}`);",
    "  logger.info(`login ok for ${userId} token=${token.value}`);",
)
LOGIN_INSECURE_COOKIE = LOGIN_OK.replace(
    '  res.cookie("sid", token.value, { httpOnly: true, secure: true, sameSite: "lax" });',
    '  res.cookie("sid", token.value, { httpOnly: false, secure: false, sameSite: "none" });',
)

EXPORT_PATH = "src/http/routes/admin/export-session.ts"
ROUTES_PATH = "src/http/routes/index.ts"
LOGIN_PATH = "src/http/routes/login.ts"
SAFE_PATH = "src/lib/safe-paths.ts"


# ----------------------------------------------------------------------------- diff helpers
def udiff(path: str, old: str, new: str) -> str:
    body = "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile=f"a/{path}" if old else "/dev/null", tofile=f"b/{path}", n=3))
    return f"diff --git a/{path} b/{path}\n{body}"


def new_line_no(new: str, needle: str) -> int:
    hits = [i + 1 for i, line in enumerate(new.splitlines()) if needle in line]
    assert len(hits) == 1, f"{needle!r} must appear exactly once, found {hits}"
    return hits[0]


def accept_line(n: int) -> str:
    lo = "|".join(str(x) for x in range(max(1, n - 3), n + 1))
    hi = "|".join(str(x) for x in range(n, n + 4))
    return rf":(?:{n}|(?:{lo})-(?:{hi}))\b"


def context_line_anchor_regex(diff: str) -> str:
    added = {l[1:].strip() for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")}
    ctx = []
    for line in diff.splitlines():
        if line.startswith(("+", "-", "@@", "diff --git", "---", "+++")):
            continue
        body = (line[1:] if line.startswith(" ") else line).strip()
        if len(body) < 12 or body in added:
            continue
        ctx.append(re.escape(body))
    if not ctx:  # all-new-file diffs have no context lines to guard against
        return None
    return r"^\*\*Anchor:\*\*\s*`+\s*(?:" + "|".join(sorted(set(ctx))) + r")\s*`+"


# ----------------------------------------------------------------------------- briefs
THREAT_PROFILE = """\
## Threat profile (Growlithe, ranked)
generated: 2026-09-18, head: 7d3f1a2c
1. **Entry points:** Express HTTP. Every `/api/admin/*` handler must call `requireAdmin(req)` itself — there is NO router-level guard; the prefix is a naming convention only.
2. **Data access:** raw SQL through `db.query(text, params)`. Only parameterised queries; string interpolation into SQL is forbidden.
3. **Sensitive data:** session tokens (`sessions.token`, also the `sid` cookie value) are credentials. Never log them; API responses go through `redactSession()` before serialisation. Session ids and user ids are not secrets and may be logged.
4. **Input validation:** path and body parameters are validated with the zod schemas in `src/lib/safe-paths.ts` (`sessionIdSchema`, `userIdSchema`) before use.
5. **Cookies:** the `sid` cookie is set with `httpOnly: true, secure: true, sameSite: "lax"`; weakening any attribute is a must-fix.
7. **Credentials:** login verifies the password through `verifyPassword()` in `src/lib/safe-paths.ts` (throws 401); issuing a session without it is a must-fix.
6. **Footguns:** `req.user` is only populated after `sessionMiddleware`; `res.json(record)` serialises every column including `token`.
"""

COORDS = "## COORDS\nforge: github · owner/repo: acme/app · PR index: 91 · head_sha: 9c1e4b7d2a5f8e3061728394a5b6c7d8e9f0a1b2\n"


def impl_brief(files: list[str]) -> str:
    return "## Implementation brief\nPR #91 \"Admin session export + login handler\" — files changed:\n" + "\n".join(f"- `{p}`" for p in files) + "\n"


REVIEW = """Review this pull request delta for security with a sub-agent, through the repository's threat profile. Do not review it yourself. There is no checkout and no DIFF_PATH in this environment; the full diff is inline in the brief and is the only source. Return the sub-agent's findings verbatim and nothing else. Findings only (no general code-quality review), each as its own block:

````text
### [<must-fix|recommended|cosmetic>] <short title> — <file>:<new-file line(s)>
**Anchor:** `<verbatim line copied from the + side of the diff>`
**What's wrong:** <1–2 sentences>

```suggestion
<replacement lines only>
```
````

Empty severity buckets are written as `_None._`. Findings must anchor to lines the diff adds or modifies; a missing control the change demands is reported with location `(not in diff — missing)` and a `(not inline — sketch)` suggestion.

---

"""


def brief(files: list[str], diff: str) -> str:
    context = f"## Repository context (unchanged files, for reference only — not part of the PR)\n\n`{SAFE_PATH}`:\n\n```ts\n{SAFE_PATHS_OLD.rstrip()}\n```\n\n`src/lib/tokens.ts` exports `issueToken(userId): {{ sessionId: string; value: string }}` where `value` is the opaque bearer credential and `sessionId` is a non-secret identifier. `src/lib/db.ts` exports `db.query(text, params)`. `server.ts` mounts `sessionMiddleware` on `/api/*` before `registerRoutes`.\n"
    return f"{impl_brief(files)}\n{THREAT_PROFILE}\n{COORDS}\n{context}\n## Diff (inline; the only source)\n\n```diff\n{diff.rstrip()}\n```\n"


# ----------------------------------------------------------------------------- plumbing
FRONT = """---
max_turns: 8
timeout_seconds: 600
allowed_tools: [Agent]
model: opus
runs: 3
---
"""


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


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Alakazam\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Alakazam\nmin: 0\nmax: 0\narm: both\n---\n"
SEV = r"(must-fix|recommended|cosmetic)"
MISSING_SUGGESTION = r"^### \[(must-fix|recommended|cosmetic)\] [^\n]*\n(?:(?!### |## |```suggestion)[^\n]*\n)*(?:(?=### |## )|(?!### |## |```suggestion)[^\n]*(?![\s\S]))"
EMPTY_SUGGESTION = r"```suggestion\s*\n\s*```"


def fire_case(slug: str, files: list[str], diff: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + REVIEW + brief(files, diff))
    # any ### header must be a finding header (severity + title + location) or a bare bucket label
    grader(case, "strict-finding-headers", regex(rf"^### (?!\[{SEV}\] [^\n]+ — [^\n]+$)(?!\[?{SEV}\]?\s*$)", match="not_contains", flags="mi"))
    grader(case, "strict-anchor-follows-header", regex(rf"^### \[{SEV}\] (?![^\n]*\(not in diff)[^\n]*\n\n?(?!\*\*Anchor:\*\*)", match="not_contains", flags="m"))
    grader(case, "no-collapsed-findings", regex(rf"^- \[{SEV}\]", match="not_contains", flags="m"))
    grader(case, "suggestion-fence-per-finding", regex(MISSING_SUGGESTION, match="not_contains", flags="m"))
    grader(case, "no-empty-suggestion", regex(EMPTY_SUGGESTION, match="not_contains"))
    ctx_guard = context_line_anchor_regex(diff)
    if ctx_guard:
        grader(case, "no-anchor-on-context-line", regex(ctx_guard, match="not_contains", flags="m"))
    grader(case, "routed-to-alakazam", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def neg_case(slug: str, prompt: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt.strip() + "\n")
    grader(case, "no-review-findings", regex(rf"^### \[{SEV}\]", match="not_contains", flags="m"))
    grader(case, "not-routed-to-alakazam", NOT_ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


# ----------------------------------------------------------------------------- 01 SQL injection + missing authz (bypasses the safe path)
export01 = export_route(authz=AUTHZ_MISSING, id_check=ID_OK, redact=REDACT_OK, query=QUERY_CONCAT)
diff01 = udiff(EXPORT_PATH, "", export01) + udiff(ROUTES_PATH, ROUTES_INDEX_OLD, ROUTES_INDEX_NEW)
l_sql = new_line_no(export01, "SELECT * FROM sessions WHERE id = '")
l_authz = new_line_no(export01, "enforced by the /api/admin router prefix")
fire_case(
    "alakazam-01-sqli-and-missing-authz", [EXPORT_PATH, ROUTES_PATH], diff01,
    {
        "finds-sqli": regex(rf"^### \[must-fix\][^\n]*— {re.escape(EXPORT_PATH)}{accept_line(l_sql)}", flags="m"),
        "sqli-suggestion-parameterised": regex(r"\$1[\s\S]{0,80}\[sessionId\]|\[sessionId\][\s\S]{0,80}\$1"),
        "finds-missing-authz": regex(rf"^### \[must-fix\][^\n]*(requireAdmin|authz|authori[sz]ation|admin)[^\n]*— ({re.escape(EXPORT_PATH)}{accept_line(l_authz)}|\(not in diff — missing\))", flags="mi"),
        "authz-suggestion": regex(r"requireAdmin\(req\)"),
        "both-defects": llm("""
The answer is a security review of a diff that adds an admin session-export endpoint. The diff contains exactly two planted defects. All claims must hold to pass.

1. A must-fix reports SQL injection: `sessionId` is interpolated into the SQL string instead of passed as a parameter. The suggestion uses the parameterised form (`"... WHERE id = $1", [sessionId]`).
2. A must-fix reports the missing authorisation check: the handler relies on the `/api/admin` prefix comment, but the threat profile says every admin handler must call `requireAdmin(req)` itself. The suggestion adds `requireAdmin(req);` (either anchored on the comment line or reported as `(not in diff — missing)` with a sketch).
3. It does not report the zod validation or `redactSession` usage as problems (they are correct here), and it does not report general code-quality issues.
"""),
    },
)

# ----------------------------------------------------------------------------- 02 token leak in log + unredacted response
export02 = export_route(authz=AUTHZ_OK, id_check=ID_OK, redact=REDACT_RAW, query=QUERY_PARAM)
diff02 = udiff(EXPORT_PATH, "", export02) + udiff(LOGIN_PATH, "", LOGIN_LOGS_TOKEN)
l_redact = new_line_no(export02, "res.json(session);")
l_log = new_line_no(LOGIN_LOGS_TOKEN, "token=${token.value}")
fire_case(
    "alakazam-02-token-leaks", [EXPORT_PATH, LOGIN_PATH], diff02,
    {
        "finds-unredacted-response": regex(rf"^### \[must-fix\][^\n]*— {re.escape(EXPORT_PATH)}{accept_line(l_redact)}", flags="m"),
        "redact-suggestion": regex(r"redactSession\(session\)"),
        "finds-token-in-log": regex(rf"^### \[must-fix\][^\n]*— {re.escape(LOGIN_PATH)}{accept_line(l_log)}", flags="m"),
        "log-suggestion-drops-token": regex(r"```suggestion\n[^\n]*logger\.info\(`login ok for \$\{userId\}(?![^\n]*token\.value)[^\n]*`\)"),
        "both-leaks": llm("""
The answer is a security review of a diff with exactly two planted credential leaks. All claims must hold to pass.

1. A must-fix reports that the export handler serialises the raw session row (`res.json(session)`) so the `token` column is exposed; the suggestion wraps it in `redactSession(session)`.
2. A must-fix reports that the login handler logs the session token (`token=${token.value}`); the suggestion removes `token.value` from the log line (logging the user id and/or the non-secret `token.sessionId` instead is fine).
3. The correctly parameterised query, the `requireAdmin` call, and the login handler's `verifyPassword` credential check are not flagged as defects.
"""),
    },
)

# ----------------------------------------------------------------------------- 03 clean PR
export03 = export_route(authz=AUTHZ_OK, id_check=ID_OK, redact=REDACT_OK, query=QUERY_PARAM)
diff03 = udiff(EXPORT_PATH, "", export03) + udiff(ROUTES_PATH, ROUTES_INDEX_OLD, ROUTES_INDEX_NEW) + udiff(LOGIN_PATH, "", LOGIN_OK)
fire_case(
    "alakazam-03-clean-pr", [EXPORT_PATH, ROUTES_PATH, LOGIN_PATH], diff03,
    {
        "no-must-fix": regex(r"^### \[must-fix\]", match="not_contains", flags="m"),
        "empty-bucket-marker": regex(r"_None\._"),
        "nothing-invented": llm("""
The answer is a security review of a diff that follows every rule of the threat profile: `requireAdmin` is called, the id is zod-validated, the query is parameterised, the response is redacted, the token is not logged, login verifies the password via `verifyPassword`, and the cookie keeps `httpOnly/secure/sameSite`. All claims must hold to pass.

1. There are no must-fix findings and the must-fix bucket is written as `_None._`. A review whose three buckets are all `_None._` is the ideal answer and PASSES.
2. If any recommended or cosmetic finding is present, it is a defensible hardening suggestion anchored to an added line (for example rate-limiting the export, or `sameSite: "strict"`), not an invented vulnerability.
3. `createdAt: Date.now()` in the login handler is not reported as a security issue (it is a code-convention matter for the general reviewer, if anything).
"""),
    },
)

# ----------------------------------------------------------------------------- 04 unvalidated id + weakened cookie (one finding is on a route file too)
export04 = export_route(authz=AUTHZ_OK, id_check=ID_UNCHECKED, redact=REDACT_OK, query=QUERY_PARAM)
diff04 = udiff(EXPORT_PATH, "", export04) + udiff(LOGIN_PATH, "", LOGIN_INSECURE_COOKIE)
l_id = new_line_no(export04, "const sessionId = req.params.id;")
l_cookie = new_line_no(LOGIN_INSECURE_COOKIE, 'httpOnly: false')
fire_case(
    "alakazam-04-validation-and-cookie", [EXPORT_PATH, LOGIN_PATH], diff04,
    {
        "finds-weak-cookie": regex(rf"^### \[must-fix\][^\n]*— {re.escape(LOGIN_PATH)}{accept_line(l_cookie)}", flags="m"),
        "cookie-suggestion": regex(r"httpOnly: true[^\n]*secure: true"),
        "finds-unvalidated-id": regex(rf"^### \[{SEV}\][^\n]*— {re.escape(EXPORT_PATH)}{accept_line(l_id)}", flags="m"),
        "id-suggestion-uses-schema": regex(r"sessionIdSchema\.parse\(req\.params\.id\)"),
        "severities": llm("""
The answer is a security review of a diff with two planted defects. All claims must hold to pass.

1. The `sid` cookie set with `httpOnly: false, secure: false, sameSite: "none"` is reported as must-fix (the threat profile says weakening any attribute is a must-fix); the suggestion restores `httpOnly: true, secure: true` and a `lax` or `strict` sameSite.
2. The unvalidated `req.params.id` is reported (must-fix or recommended) as bypassing the `sessionIdSchema` safe path; the suggestion uses `sessionIdSchema.parse(req.params.id)`. The query itself is parameterised, so the answer does not claim SQL injection here.
3. No other must-fix is invented (the login handler verifies the password via `verifyPassword`, so "no credential check" would be an invented finding).
"""),
    },
)

# ----------------------------------------------------------------------------- 05 negative: general code review request (Mewtwo's job)
neg_case(
    "alakazam-05-neg-general-review-ask",
    f"""\
Summarize in five bullets what this diff changes, for the PR description. Do not review it for security or quality, and do not produce findings.

```diff
{diff03.rstrip()}
```
""",
    {
        "mentions-export": regex(r"export", flags="i"),
        "summary-only": llm("""
The answer is a five-bullet PR-description summary of a diff that adds an admin session-export endpoint, registers its route, and adds a login handler. All claims must hold to pass.

1. It has four to six bullets describing those changes in plain language.
2. It contains no severity labels, no `**Anchor:**` lines, no suggestion blocks, and no vulnerability findings.
"""),
    },
)

# ----------------------------------------------------------------------------- 06 negative: explain the threat profile
neg_case(
    "alakazam-06-neg-explain-profile",
    f"""\
Explain, in one short paragraph each, what the six items of this threat profile mean for a developer adding a new HTTP handler. Do not review any code and do not produce findings.

{THREAT_PROFILE}
""",
    {
        "covers-six-items": regex(r"requireAdmin[\s\S]*param[\s\S]*redact|redact[\s\S]*requireAdmin", flags="i"),
        "explanation-only": llm("""
The answer explains a six-item threat profile for developers. All claims must hold to pass.

1. It addresses all six items: admin handlers calling requireAdmin, parameterised SQL only, never logging tokens and redacting responses, zod validation of inputs, cookie attributes, and the two footguns (`req.user` population, `res.json` serialising every column).
2. It contains no code-review findings, severity labels, anchors, or suggestion blocks.
"""),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("alakazam-")))
print(f"lines: sqli={l_sql} authz={l_authz} redact={l_redact} log={l_log} id={l_id} cookie={l_cookie}")
