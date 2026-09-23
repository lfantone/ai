#!/usr/bin/env python3
"""Regenerate the growlithe-* cases.

Each prompt lays down a small repository with deliberate security-relevant features (HTTP entry
points, raw SQL, a token-bearing session record, safe-path helpers, a subprocess call, a secrets
loader) and asks a sub-agent for the security profile. Growlithe writes
`$CACHE/security-profile.md` ($CACHE = .agents/cache here) and returns a ranked threat
checklist, so graders read the written file and the brief. Re-run after editing.
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
CACHE = ".agents/cache"
PROFILE = f"{CACHE}/security-profile.md"

TS_TREE: dict[str, str] = {
    "README.md": """\
# harbor-sessions

Express + TypeScript service that owns login sessions and an admin export for the Harbor Booking Gateway.
Postgres via raw SQL (`src/lib/db.ts`), secrets from `.env.*` through `src/lib/secrets.ts`.
""",
    "src/lib/db.ts": """\
import { Pool } from "pg";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// The only database entry point. Always pass parameters; never interpolate values into `text`.
export const db = {
  query: async (text: string, params: unknown[] = []): Promise<Record<string, unknown>[]> =>
    (await pool.query(text, params)).rows,
};
""",
    "src/lib/secrets.ts": """\
import { readFileSync } from "node:fs";

// Loads `.env.<name>` and decrypts `*.secure` values with the KMS key. Never log the returned map.
export function loadSecrets(name: string): Record<string, string> {
  const raw = readFileSync(`.env.${name}`, "utf8");
  return Object.fromEntries(raw.split("\\n").filter(Boolean).map((l) => l.split("=", 2) as [string, string]));
}
""",
    "src/lib/safe-paths.ts": """\
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
""",
    "src/cache/session-store.ts": """\
export interface SessionRecord {
  id: string;
  userId: string;
  token: string; // bearer credential — never log, never serialise
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
}
""",
    "src/http/session-middleware.ts": """\
import type { NextFunction, Request, Response } from "express";
import type { SessionStore } from "../cache/session-store";

export function sessionMiddleware(store: SessionStore) {
  return (req: Request, res: Response, next: NextFunction) => {
    const session = store.get(req.cookies?.sid);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    req.user = { id: session.userId, role: session.userId.startsWith("u-adm") ? "admin" : "user" };
    next();
  };
}
""",
    "src/http/routes/index.ts": """\
import type { Express } from "express";
import { meHandler } from "./me";
import { loginHandler } from "./login";
import { exportSessionHandler } from "./admin/export-session";
import { rebuildIndexHandler } from "./admin/rebuild-index";
import { webhookHandler } from "./webhooks/harbor";

export function registerRoutes(app: Express): void {
  app.post("/api/login", loginHandler);
  app.get("/api/me", meHandler);
  app.get("/api/admin/sessions/:id/export", exportSessionHandler);
  app.post("/api/admin/rebuild-index", rebuildIndexHandler);
  app.post("/webhooks/harbor", webhookHandler);
}
""",
    "src/http/routes/me.ts": """\
import type { Request, Response } from "express";
import { redactSession } from "../../lib/safe-paths";

export function meHandler(req: Request, res: Response): void {
  res.json(redactSession(req.session!));
}
""",
    "src/http/routes/login.ts": """\
import type { Request, Response } from "express";
import { userIdSchema } from "../../lib/safe-paths";

export function loginHandler(req: Request, res: Response): void {
  const userId = userIdSchema.parse(req.body?.user);
  res.cookie("sid", `${userId}-${Date.now()}`, { httpOnly: true, secure: true, sameSite: "lax" });
  res.status(204).end();
}
""",
    "src/http/routes/admin/export-session.ts": """\
import type { Request, Response } from "express";
import { db } from "../../../lib/db";
import { redactSession, requireAdmin, sessionIdSchema } from "../../../lib/safe-paths";

export async function exportSessionHandler(req: Request, res: Response): Promise<void> {
  requireAdmin(req);
  const sessionId = sessionIdSchema.parse(req.params.id);
  const rows = await db.query("SELECT * FROM sessions WHERE id = $1", [sessionId]);
  res.json(rows[0] ? redactSession(rows[0] as { token?: string }) : { error: "not_found" });
}
""",
    "src/http/routes/admin/rebuild-index.ts": """\
import type { Request, Response } from "express";
import { execSync } from "node:child_process";
import { requireAdmin } from "../../../lib/safe-paths";

// Rebuilds the search index for one tenant by shelling out to the indexer CLI.
export function rebuildIndexHandler(req: Request, res: Response): void {
  requireAdmin(req);
  const tenant = String(req.body?.tenant ?? "");
  const out = execSync(`indexer rebuild --tenant ${tenant}`, { encoding: "utf8" });
  res.json({ ok: true, out });
}
""",
    "src/http/routes/webhooks/harbor.ts": """\
import type { Request, Response } from "express";
import { createHmac, timingSafeEqual } from "node:crypto";
import { loadSecrets } from "../../../lib/secrets";

const secrets = loadSecrets(process.env.APP_ENV ?? "dev");

// Harbor calls this on booking changes; the HMAC signature is verified before anything else.
export function webhookHandler(req: Request, res: Response): void {
  const expected = createHmac("sha256", secrets.HARBOR_WEBHOOK_SECRET).update(JSON.stringify(req.body)).digest("hex");
  const given = String(req.header("x-harbor-signature") ?? "");
  if (given.length !== expected.length || !timingSafeEqual(Buffer.from(given), Buffer.from(expected))) {
    res.status(401).end();
    return;
  }
  res.status(202).end();
}
""",
}

PY_TREE: dict[str, str] = {
    "README.md": """\
# harbor-etl

Flask admin API + nightly ETL. SQLite via raw `sqlite3`, Redis via `pipeline/redis_client.py`,
secrets from `.env.*` through `pipeline/config.py`.
""",
    "pipeline/config.py": """\
from pathlib import Path


def load_settings(env: str) -> dict[str, str]:
    \"\"\"The only place that reads `.env.<env>`; values include KAFKA_SASL_PASSWORD. Never log the dict.\"\"\"
    return dict(line.split("=", 1) for line in Path(f".env.{env}").read_text().splitlines() if "=" in line)
""",
    "pipeline/db.py": """\
import sqlite3


def query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[tuple]:
    \"\"\"The only SQL entry point. Callers must pass params; f-strings into `sql` are forbidden.\"\"\"
    return conn.execute(sql, params).fetchall()
""",
    "pipeline/auth.py": """\
from functools import wraps
from flask import abort, request


def require_operator(view):
    \"\"\"Safe path: every /admin/* view must be wrapped with this decorator.\"\"\"
    @wraps(view)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-Operator-Token") != current_token():
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def current_token() -> str:
    return "rotated-nightly"
""",
    "pipeline/api.py": """\
import subprocess
from flask import Flask, jsonify, request
from .auth import require_operator
from .db import query

app = Flask(__name__)


@app.post("/admin/replay")
@require_operator
def replay():
    stream = request.json.get("stream", "")
    subprocess.run(["python", "-m", "pipeline.replay", "--stream", stream], check=True)
    return jsonify(ok=True)


@app.get("/admin/runs/<run_id>")
@require_operator
def run_detail(run_id: str):
    rows = query(app.config["DB"], "SELECT * FROM runs WHERE id = ?", (run_id,))
    return jsonify(rows)


@app.post("/hooks/harbor")
def harbor_hook():
    # TODO: verify signature (HARBOR_WEBHOOK_SECRET) before accepting
    return ("", 202)
""",
}

FRESH_PROFILE = """\
generated: 2026-09-20, head: 4f1c9e2a7b3d5c6e8f0a1b2c3d4e5f6a7b8c9d0e
# Threat profile — harbor-sessions (ranked)
1. Entry points: Express routes in `src/http/routes/index.ts` (login, me, admin export, admin rebuild-index, harbor webhook).
2. Command execution: `execSync` with request-derived `tenant` in `src/http/routes/admin/rebuild-index.ts`.
3. Sensitive data: `SessionRecord.token`; responses must go through `redactSession`.
4. Data access: raw SQL via `src/lib/db.ts:db.query`, parameterised only.
5. Safe paths: `requireAdmin`, `redactSession`, `sessionIdSchema`, `userIdSchema` in `src/lib/safe-paths.ts`; `loadSecrets` never logged.
6. Footguns: role derived from user-id prefix in `sessionMiddleware`; `res.json(row)` serialises every column.
7. Deploy note: the indexer CLI invoked by rebuild-index is pinned to tools/indexer v3.4.1 for all tenants.
"""

STALE_PROFILE = """\
generated: 2026-05-01, head: 0000000000000000000000000000000000000000
# Threat profile — harbor-sessions
1. Entry points: `/api/login`, `/api/me` only.
2. Data access: ORM (Prisma).
3. Deploy note: the indexer CLI is pinned to tools/indexer v2.9.0.
"""

FRONT = """---
max_turns: 14
timeout_seconds: 600
allowed_tools: [Agent, Read, Write, Edit, Glob, Grep]
model: sonnet
runs: 5
---
"""


def fixture_block(files: dict[str, str]) -> str:
    parts = []
    for p, c in files.items():
        lang = "py" if p.endswith(".py") else "md" if p.endswith(".md") else "ts"
        parts.append(f"`{p}`:\n\n```{lang}\n{c.rstrip()}\n```\n")
    return "\n".join(parts)


SETUP = """\
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

"""

PROFILE_ASK = f"""\
Step 2 — with a sub-agent, produce the security profile (the ranked, repo-specific threat checklist) for this working tree. Do not produce it yourself. Context for the sub-agent: `$CACHE` is `{CACHE}` (relative to the working tree root); git is not available in this environment, so treat the current HEAD as `{{head}}` and the working tree as clean with no uncommitted changes. Relay the sub-agent's checklist verbatim and nothing else.

"""


def grader(case: Path, name: str, body: str) -> None:
    (case / "graders").mkdir(parents=True, exist_ok=True)
    (case / "graders" / f"{name}.md").write_text(body)


def regex(pattern: str, match: str = "contains", flags: str | None = None, target: str = "last_message") -> str:
    fm = f"---\ntype: regex\ntarget: {target}\nmatch: {match}\n"
    if flags:
        fm += f"flags: {flags}\n"
    return fm + f"---\n{pattern}\n"


def file_regex(pattern: str, match: str = "contains", flags: str | None = None, path: str = PROFILE) -> str:
    return regex(pattern, match, flags, target=f"{{source: file, path: {path}}}")


def llm(rubric: str) -> str:
    return f"---\ntype: llm\nfocus: last_message\n---\n{rubric.strip()}\n"


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Growlithe\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Growlithe\nmin: 0\nmax: 0\narm: both\n---\n"
PROFILE_EXISTS = f"---\ntype: file_exists\npath: {PROFILE}\nexists: true\n---\n"
PROFILE_ABSENT = f"---\ntype: file_exists\npath: {PROFILE}\nexists: false\n---\n"
DUMP = r"const pool = new Pool|export function requireAdmin\(req: \{ user\?|def require_operator\(view\):"


def case_dir(slug: str) -> Path:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    return case


def profile_case(slug: str, files: dict[str, str], head: str, extra: dict[str, str], *, expect_written: bool = True) -> None:
    case = case_dir(slug)
    (case / "prompt.md").write_text(FRONT + SETUP + fixture_block(files) + PROFILE_ASK.format(head=head))
    grader(case, "no-file-body-dump", regex(DUMP, match="not_contains"))
    grader(case, "brief-is-compact", regex(r"(?:\S+\s+){500}", match="not_contains"))
    grader(case, "ranked-list", regex(r"^\s*1[.)]\s+\S[\s\S]*^\s*2[.)]\s+\S", flags="m"))
    grader(case, "routed-to-growlithe", ROUTED)
    if expect_written:
        grader(case, "profile-written", PROFILE_EXISTS)
        grader(case, "profile-freshness-header", file_regex(rf"^generated: \d{{4}}-\d{{2}}-\d{{2}}, head: {head}", flags="m"))
    for name, body in extra.items():
        grader(case, name, body)


TS_HEAD = "4f1c9e2a7b3d5c6e8f0a1b2c3d4e5f6a7b8c9d0e"
PY_HEAD = "b7e2d9c4a1f0e3d6c5b8a7f2e1d0c9b8a7f6e5d4"

profile_case(
    "growlithe-01-ts-fresh-scan", TS_TREE, TS_HEAD,
    {
        "profile-command-exec": file_regex(r"execSync|child_process|command injection|rebuild-index", flags="i"),
        "profile-raw-sql": file_regex(r"db\.query|raw SQL|parameteri[sz]ed", flags="i"),
        "profile-token": file_regex(r"\btoken\b", flags="i"),
        "profile-safe-paths": file_regex(r"requireAdmin[\s\S]*redactSession|redactSession[\s\S]*requireAdmin"),
        "profile-schemas": file_regex(r"sessionIdSchema|userIdSchema"),
        "profile-webhook": file_regex(r"webhook|HMAC|signature", flags="i"),
        "profile-role-footgun": file_regex(r"u-adm|prefix|role", flags="i"),
        "brief-names-exec-risk": regex(r"execSync|child_process|command injection", flags="i"),
        "checklist-is-right": llm(f"""
The answer is a ranked, repo-specific threat checklist for a small Express service, and a profile file was written to `{PROFILE}`. Judge the checklist. All claims must hold to pass.

1. Entry points: it lists the HTTP routes (login, me, admin export, admin rebuild-index, harbor webhook) and identifies the admin routes and the webhook as trust boundaries.
2. It ranks the `execSync` call built from request input in `rebuild-index.ts` as a top item (command injection risk).
3. Data access: raw SQL via `src/lib/db.ts:db.query`, parameterised queries only; sensitive data: `SessionRecord.token` and the secrets map from `loadSecrets`, never to be logged or serialised.
4. Existing safe paths are named for new code to use: `requireAdmin`, `redactSession`, `sessionIdSchema`/`userIdSchema`, the webhook HMAC check with `timingSafeEqual`.
5. Footguns: the role is derived from a user-id prefix in `sessionMiddleware`; `res.json(row)` would serialise `token`. No file bodies are pasted.
"""),
    },
)

profile_case(
    "growlithe-02-fresh-cache-verbatim", {**TS_TREE, PROFILE: FRESH_PROFILE}, TS_HEAD,
    {
        "returns-cached-verbatim": regex(r"tools/indexer v3\.4\.1 for all tenants"),
        "no-rescan-artifacts": regex(r"^\S+$", match=f"count:{len(TS_TREE) + 1}", flags="m", target="files"),
        "cache-honoured": llm(f"""
The answer is the response to a request for a security profile when `{PROFILE}` already exists with `head:` equal to the current HEAD and a clean tree. All claims must hold to pass.

1. The cached checklist is returned verbatim (all seven numbered items, including the deploy note about tools/indexer v3.4.1), possibly with a one-line note that the cache was fresh.
2. No re-scanned checklist replaces it.
"""),
    },
)

profile_case(
    "growlithe-03-stale-cache-rescan", {**TS_TREE, PROFILE: STALE_PROFILE}, TS_HEAD,
    {
        "stale-lines-gone": file_regex(r"^2\. Data access: ORM \(Prisma\)\.$|tools/indexer v2\.9\.0", match="not_contains", flags="m"),
        "profile-has-new-routes": file_regex(r"rebuild-index|webhook", flags="i"),
        "brief-not-stale": regex(r"tools/indexer v2\.9\.0", match="not_contains"),
        "rescan-happened": llm(f"""
The answer is the response to a request for a security profile when `{PROFILE}` existed but was stale (all-zero head, only two routes listed, "ORM (Prisma)" while the tree uses raw SQL). All claims must hold to pass.

1. The stale checklist (two routes, "ORM (Prisma)", indexer v2.9.0) is not returned as the profile; a re-scanned checklist is. Mentioning the old text to explain what was corrected is fine.
2. The new checklist covers the admin export, rebuild-index (`execSync`) and webhook routes and raw SQL via `db.query`.
"""),
    },
)
p = SUITE / "growlithe-03-stale-cache-rescan" / "prompt.md"
p.write_text(p.read_text().rstrip("\n") + " Additional context for the sub-agent: HEAD has moved since the cached profile was written, and the diff between the cached head and HEAD adds the `src/http/routes/admin/` and `src/http/routes/webhooks/` directories.\n")

profile_case(
    "growlithe-04-py-fresh-scan", PY_TREE, PY_HEAD,
    {
        "profile-subprocess": file_regex(r"subprocess", flags="i"),
        "profile-raw-sql": file_regex(r"sqlite|raw SQL|parameteri[sz]ed|params", flags="i"),
        "profile-safe-path": file_regex(r"require_operator"),
        "profile-unverified-hook": file_regex(r"hook[\s\S]*(unverified|no signature|TODO|missing)", flags="i"),
        "profile-secrets": file_regex(r"KAFKA_SASL_PASSWORD|secrets|\.env", flags="i"),
        "checklist-is-right": llm(f"""
The answer is a ranked threat checklist for a small Flask admin API + ETL, and a profile file was written to `{PROFILE}`. Judge the checklist. All claims must hold to pass.

1. Entry points: `/admin/replay`, `/admin/runs/<run_id>`, `/hooks/harbor`; it flags that `/hooks/harbor` accepts payloads with NO signature verification (the TODO) as a top item.
2. External calls: `subprocess.run` with a request-derived `stream` argument in `/admin/replay` (list form, so no shell injection, but still an argument-injection surface).
3. Data access: raw sqlite via `pipeline/db.py:query`, parameterised only; sensitive data: the settings dict from `pipeline/config.py` (contains `KAFKA_SASL_PASSWORD`), never to be logged.
4. Safe path: the `require_operator` decorator every `/admin/*` view must use; footgun: `current_token()` is a hard-coded placeholder.
5. No file bodies pasted.
"""),
    },
)


def neg_case(slug: str, prompt: str, files: dict[str, str], extra: dict[str, str]) -> None:
    case = case_dir(slug)
    (case / "prompt.md").write_text(FRONT + prompt)
    grader(case, "not-routed-to-growlithe", NOT_ROUTED)
    grader(case, "no-profile-written", PROFILE_ABSENT)
    grader(case, "fixtures-only-created", regex(r"^\S+$", match=f"count:{len(files)}", flags="m", target="files"))
    for name, body in extra.items():
        grader(case, name, body)


neg_case(
    "growlithe-05-neg-list-routes",
    SETUP + fixture_block(TS_TREE) + "Step 2 — list the HTTP routes registered in `src/http/routes/index.ts` as `METHOD path -> handler`, one per line. Do not assess security and do not delegate.\n",
    TS_TREE,
    {"lists-routes": regex(r"POST /api/login[\s\S]*GET /api/admin/sessions/:id/export[\s\S]*POST /webhooks/harbor")},
)

neg_case(
    "growlithe-06-neg-repo-profile",
    SETUP + fixture_block(TS_TREE) + f"""\
Step 2 — with a sub-agent, produce the REPOSITORY profile (stack, architecture patterns, naming and code conventions, testing expectations) for this working tree, not a security assessment. `$CACHE` is `{CACHE}`; treat HEAD as `{TS_HEAD}`. Relay the brief verbatim.
""",
    TS_TREE,
    {"repo-profile-produced": regex(r"Express[\s\S]*(TypeScript|convention)|(TypeScript|convention)[\s\S]*Express", flags="i")},
)
# the repo-profile negative legitimately writes .agents/cache/repo-profile.md, so the
# "fixtures only" file-count guard does not apply there (the security-profile guard does)
(SUITE / "growlithe-06-neg-repo-profile" / "graders" / "fixtures-only-created.md").unlink()

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("growlithe-")))
