#!/usr/bin/env python3
"""Regenerate the eevee-* cases.

Each prompt lays down a small repository (README, contributing rules, lint/test config, a few
source files) and asks a sub-agent for the repository profile. Eevee writes
`$CACHE/repo-profile.md` ($CACHE = .agents/cache here) and returns a compact brief, so graders
read the written file with `{source: file}` and the brief from the last message. Re-run after
editing.
"""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
CACHE = ".agents/cache"
PROFILE = f"{CACHE}/repo-profile.md"

# ----------------------------------------------------------------------------- TypeScript repo
TS_TREE: dict[str, str] = {
    "README.md": """\
# harbor-sessions

Express + TypeScript service that owns login sessions for the Harbor Booking Gateway.

- Runtime: Node 22, pnpm. `pnpm dev` starts the server on :3000, `pnpm test` runs vitest.
- Layout: `src/http` (Express handlers and middleware), `src/cache` (in-memory stores),
  `src/lib` (shared helpers: clock, logger, safe paths).
- All time comes from the injected `Clock` (`src/lib/clock.ts`); `Date.now()` is banned outside it.
""",
    "CONTRIBUTING.md": """\
# Contributing

Rules a reviewer must enforce:

1. Library code takes an injected `Clock`; `Date.now()` only inside `src/lib/clock.ts`.
2. Logging goes through `src/lib/logger.ts` (`debug`/`info`/`warn`); no `console.*` in `src/`.
3. `SessionStore` is the only owner of the session map; middleware goes through its methods.
4. Tests live next to the code under `__tests__/`, one `describe` per unit, vitest only.
5. Exported functions are named `verbNoun` (`createSession`, `evictIdle`); no default exports.
6. Commits follow Conventional Commits (`feat(scope): ...`).
""",
    "package.json": """\
{
  "name": "harbor-sessions",
  "private": true,
  "packageManager": "pnpm@9",
  "scripts": { "dev": "tsx watch src/server.ts", "test": "vitest run", "lint": "eslint src --max-warnings 0", "format": "prettier --check ." },
  "dependencies": { "express": "^4.19.0" },
  "devDependencies": { "typescript": "^5.6.0", "vitest": "^2.1.0", "eslint": "^9.10.0", "prettier": "^3.3.0", "tsx": "^4.19.0" }
}
""",
    ".prettierrc.json": '{ "printWidth": 100, "singleQuote": false, "semi": true }\n',
    "eslint.config.js": """\
export default [
  { files: ["src/**/*.ts"], rules: { "no-console": "error", "no-restricted-syntax": ["error", { selector: "CallExpression[callee.object.name='Date'][callee.property.name='now']", message: "use the injected Clock" }] } },
];
""",
    "src/lib/clock.ts": "export interface Clock {\n  now(): number;\n}\n\nexport const systemClock: Clock = { now: () => Date.now() };\n",
    "src/lib/logger.ts": "export const logger = {\n  debug: (msg: string): void => console.debug(msg),\n  info: (msg: string): void => console.info(msg),\n  warn: (msg: string): void => console.warn(msg),\n};\n",
    "src/cache/session-store.ts": """\
import { logger } from "../lib/logger";

export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: number;
}

export class SessionStore {
  private readonly sessions = new Map<string, SessionRecord>();

  createSession(record: SessionRecord): void {
    this.sessions.set(record.id, record);
  }

  getSession(id: string): SessionRecord | undefined {
    return this.sessions.get(id);
  }
}
""",
    "src/http/session-middleware.ts": """\
import type { NextFunction, Request, Response } from "express";
import type { Clock } from "../lib/clock";
import type { SessionStore } from "../cache/session-store";

export function requireSession(store: SessionStore, clock: Clock) {
  return (req: Request, res: Response, next: NextFunction) => {
    const session = store.getSession(req.cookies?.sid);
    if (!session) return res.status(401).json({ error: "unauthenticated" });
    req.session = session;
    next();
  };
}
""",
    "src/cache/__tests__/session-store.test.ts": """\
import { describe, expect, it } from "vitest";
import { SessionStore } from "../session-store";

describe("SessionStore", () => {
  it("returns a created session", () => {
    const store = new SessionStore();
    store.createSession({ id: "a", userId: "u-1", createdAt: 0 });
    expect(store.getSession("a")?.userId).toBe("u-1");
  });
});
""",
}

# ----------------------------------------------------------------------------- Python repo (second stack)
PY_TREE: dict[str, str] = {
    "README.md": """\
# harbor-etl

Nightly Python ETL that pulls collections from the Harbor gateway and publishes them to Kafka.

- Python 3.12, managed with `uv`. `uv run pytest` runs the tests, `uv run ruff check .` lints.
- Layout: `pipeline/` (collection walkers, cursors, writers), `pipeline/redis_client.py`
  (all Redis access), `tests/`.
- Configuration comes only from `.env.*` files loaded by `pipeline/config.py`; never read
  `os.environ` directly elsewhere.
""",
    "AGENTS.md": """\
# Working in this repo

- Every collection walker is a subclass of `pipeline.walkers.BaseWalker` and is registered in
  `pipeline/walkers/__init__.py`; do not special-case collections in `main.py`.
- Redis is only touched through `pipeline/redis_client.py` (connection timeout 2s, raises
  `RedisUnavailable`); no bare `redis.Redis()` anywhere else.
- Tests use `pytest` with the `fake_redis` fixture from `tests/conftest.py`; no live Redis in
  unit tests. Live-API tests are marked `@pytest.mark.live` and FAIL (not skip) when the API is
  unreachable unless `HARBOR_SKIP_LIVE=1`.
- Type hints everywhere; `ruff` and `mypy --strict` must pass.
- Commit messages: Conventional Commits.
""",
    "pyproject.toml": """\
[project]
name = "harbor-etl"
version = "0.4.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "redis>=5.0", "confluent-kafka>=2.5", "pydantic>=2.8"]

[tool.uv]
dev-dependencies = ["pytest>=8.3", "ruff>=0.6", "mypy>=1.11"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "B"]

[tool.pytest.ini_options]
markers = ["live: hits the real Harbor API"]
""",
    "pipeline/config.py": """\
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    kafka_bootstrap: str
    redis_url: str
    harbor_base_url: str


def load_settings(env: str) -> Settings:
    \"\"\"Load `.env.<env>`; the only place that reads environment files.\"\"\"
    values = dict(line.split("=", 1) for line in Path(f".env.{env}").read_text().splitlines() if "=" in line)
    return Settings(**{k.lower(): v for k, v in values.items()})
""",
    "pipeline/redis_client.py": """\
import redis


class RedisUnavailable(RuntimeError):
    pass


def connect(url: str) -> redis.Redis:
    \"\"\"The only Redis entry point in the codebase.\"\"\"
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=2)
        client.ping()
        return client
    except redis.exceptions.ConnectionError as exc:
        raise RedisUnavailable(str(exc)) from exc
""",
    "pipeline/walkers/__init__.py": "from .base import BaseWalker\nfrom .readings import ReadingsWalker\n\nREGISTRY: dict[str, type[BaseWalker]] = {\"Readings\": ReadingsWalker}\n",
    "pipeline/walkers/base.py": """\
from abc import ABC, abstractmethod


class BaseWalker(ABC):
    collection: str

    @abstractmethod
    def walk(self, since: str | None) -> list[dict]:
        ...
""",
    "pipeline/walkers/readings.py": """\
from .base import BaseWalker


class ReadingsWalker(BaseWalker):
    collection = "Readings"
    cursor_field = "Submitted"

    def walk(self, since: str | None) -> list[dict]:
        return []
""",
    "tests/conftest.py": """\
import pytest


@pytest.fixture
def fake_redis():
    class Fake:
        store: dict[str, str] = {}
    return Fake()
""",
}

FRESH_PROFILE_TS = """\
generated: 2026-09-20, head: 4f1c9e2a7b3d5c6e8f0a1b2c3d4e5f6a7b8c9d0e
# Repository profile — harbor-sessions
- Stack: Node 22, TypeScript, Express 4, vitest, pnpm, eslint 9, prettier (printWidth 100).
- Architecture: `src/http` handlers/middleware, `src/cache` in-memory stores, `src/lib` shared helpers; injected `Clock` for all time.
- Conventions: `verbNoun` exports, no default exports, logging via `src/lib/logger.ts`, no `console.*` in `src/`, tests under `__tests__/` one `describe` per unit.
- Rules to enforce: `Date.now()` only in `src/lib/clock.ts`; `SessionStore` sole owner of the session map; Conventional Commits.
- Key modules: `src/lib/clock.ts:Clock`, `src/lib/logger.ts:logger`, `src/cache/session-store.ts:SessionStore`, `src/http/session-middleware.ts:requireSession`.
- Deploy note: the service image is pinned to node:22.6-alpine; bump it together with `packageManager`.
"""

STALE_PROFILE_TS = """\
generated: 2026-06-01, head: 0000000000000000000000000000000000000000
# Repository profile — harbor-sessions
- Stack: Node 18, TypeScript, Express 4, **jest**, npm.
- Architecture: single `src/` folder.
- Conventions: none recorded.
- Deploy note: the service image is pinned to node:18.20-alpine.
"""

# ----------------------------------------------------------------------------- plumbing
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
        lang = "json" if p.endswith(".json") else "toml" if p.endswith(".toml") else "py" if p.endswith(".py") else "md" if p.endswith(".md") else "ts"
        parts.append(f"`{p}`:\n\n```{lang}\n{c.rstrip()}\n```\n")
    return "\n".join(parts)


SETUP = """\
Step 1 — set up the working tree. Create the following files with EXACTLY the content shown (use the Write tool; copy byte for byte; each file ends with a single trailing newline). Do not create anything else.

"""

PROFILE_ASK = f"""\
Step 2 — with a sub-agent, produce the repository profile for this working tree. Do not profile it yourself. Context for the sub-agent: `$CACHE` is `{CACHE}` (relative to the working tree root); git is not available in this environment, so treat the current HEAD as `{{head}}` and the working tree as clean with no uncommitted changes. Relay the sub-agent's brief verbatim and nothing else.

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


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Eevee\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Eevee\nmin: 0\nmax: 0\narm: both\n---\n"
PROFILE_EXISTS = f"---\ntype: file_exists\npath: {PROFILE}\nexists: true\n---\n"
PROFILE_ABSENT = f"---\ntype: file_exists\npath: {PROFILE}\nexists: false\n---\n"
DUMP = r"private readonly sessions = new Map|return \(req: Request, res: Response, next: NextFunction\) =>|def connect\(url: str\)"


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
    grader(case, "routed-to-eevee", ROUTED)
    if expect_written:
        grader(case, "profile-written", PROFILE_EXISTS)
        grader(case, "profile-freshness-header", file_regex(rf"^generated: \d{{4}}-\d{{2}}-\d{{2}}, head: {head}", flags="m"))
    for name, body in extra.items():
        grader(case, name, body)


TS_HEAD = "4f1c9e2a7b3d5c6e8f0a1b2c3d4e5f6a7b8c9d0e"
PY_HEAD = "b7e2d9c4a1f0e3d6c5b8a7f2e1d0c9b8a7f6e5d4"

# 01 — TypeScript repo, no cache
profile_case(
    "eevee-01-ts-fresh-scout", TS_TREE, TS_HEAD,
    {
        "profile-stack": file_regex(r"vitest[\s\S]*Express|Express[\s\S]*vitest", flags="i"),
        "profile-clock-rule": file_regex(r"Date\.now\(\)[^\n]*(clock|banned|only)", flags="i"),
        "profile-logger-rule": file_regex(r"logger", flags="i"),
        "profile-test-convention": file_regex(r"__tests__"),
        "profile-naming-rule": file_regex(r"verbNoun|default export", flags="i"),
        "profile-commits": file_regex(r"Conventional Commits", flags="i"),
        "brief-mentions-rules": regex(r"Clock[\s\S]*(logger|__tests__)|(logger|__tests__)[\s\S]*Clock"),
        "profile-is-curated": llm(f"""
The answer is a repository profile brief for a small Express/TypeScript service, and a profile file was written to `{PROFILE}`. Judge the brief in the answer. All claims must hold to pass.

1. It names the stack (Node, TypeScript, Express, vitest, pnpm, eslint/prettier) and the layout (`src/http`, `src/cache`, `src/lib`).
2. It lists the reviewer-enforced rules from CONTRIBUTING.md: injected `Clock` / no `Date.now()`, logging via `logger` / no `console.*`, `SessionStore` sole owner of the map, tests under `__tests__/` with vitest, `verbNoun` exports and no default exports, Conventional Commits.
3. It names the key modules/helpers by path (for example `src/lib/clock.ts`, `src/cache/session-store.ts`), optionally with symbols, and it does not paste file bodies.
"""),
    },
)

# 02 — fresh cache present: return it verbatim, do not re-scout or rewrite
profile_case(
    "eevee-02-fresh-cache-verbatim", {**TS_TREE, PROFILE: FRESH_PROFILE_TS}, TS_HEAD,
    {
        "returns-cached-verbatim": regex(r"node:22\.6-alpine; bump it together with"),
        "no-rescout-artifacts": regex(r"^\S+$", match=f"count:{len(TS_TREE) + 1}", flags="m", target="files"),
        "cache-honoured": llm(f"""
The answer is the response to a request for a repository profile when `{PROFILE}` already exists with `head:` equal to the current HEAD and a clean tree. All claims must hold to pass.

1. The cached profile is returned verbatim (all bullets, including the deploy note about node:22.6-alpine), possibly with a one-line note that the cache was fresh.
2. No new scouting summary is produced in place of the cached text; the answer does not add newly derived sections.
"""),
    },
)

# 03 — stale cache: head differs and package.json changed materially -> re-scout
profile_case(
    "eevee-03-stale-cache-rescout", {**TS_TREE, PROFILE: STALE_PROFILE_TS}, TS_HEAD,
    {
        "stale-lines-gone": file_regex(r"^- Stack: Node 18, TypeScript, Express 4, \*\*jest\*\*, npm\.$|node:18\.20-alpine", match="not_contains", flags="m"),
        "profile-updated-stack": file_regex(r"vitest", flags="i"),
        "brief-not-stale": regex(r"node:18\.20-alpine", match="not_contains"),
        "rescout-happened": llm(f"""
The answer is the response to a request for a repository profile when `{PROFILE}` existed but was stale: its `head:` was all zeros (HEAD has moved) and it described jest/npm while the tree now uses vitest/pnpm. All claims must hold to pass.

1. The stale text ("jest", "Node 18", node:18.20-alpine) is NOT returned as the profile; a re-scouted brief is returned instead. Mentioning the old text to explain what was corrected is fine.
2. The new brief reflects the current tree: vitest, pnpm, the injected Clock rule, tests under `__tests__/`.
"""),
    },
)
# case 03's prompt must say HEAD moved materially; append that to the ask
p = SUITE / "eevee-03-stale-cache-rescout" / "prompt.md"
p.write_text(p.read_text().rstrip("\n") + f" Additional context for the sub-agent: HEAD has moved since the cached profile was written, and the diff between the cached head and HEAD touches `package.json` and `eslint.config.js`.\n")

# 04 — Python repo, no cache (second stack)
profile_case(
    "eevee-04-py-fresh-scout", PY_TREE, PY_HEAD,
    {
        "profile-stack": file_regex(r"pytest[\s\S]*ruff|ruff[\s\S]*pytest", flags="i"),
        "profile-uv": file_regex(r"\buv\b"),
        "profile-redis-rule": file_regex(r"redis_client", flags="i"),
        "profile-walker-pattern": file_regex(r"BaseWalker"),
        "profile-live-tests": file_regex(r"HARBOR_SKIP_LIVE|live", flags="i"),
        "profile-config-rule": file_regex(r"\.env|os\.environ|config\.py", flags="i"),
        "profile-is-curated": llm(f"""
The answer is a repository profile brief for a small Python ETL, and a profile file was written to `{PROFILE}`. Judge the brief. All claims must hold to pass.

1. It names the stack: Python 3.12, uv, pytest, ruff, mypy --strict, httpx/redis/confluent-kafka/pydantic.
2. It lists the AGENTS.md rules: walkers subclass `BaseWalker` and register in `pipeline/walkers/__init__.py`; Redis only via `pipeline/redis_client.py`; config only via `pipeline/config.py` and `.env.*` files; `fake_redis` fixture in unit tests; live tests marked `live` fail rather than skip unless `HARBOR_SKIP_LIVE=1`; Conventional Commits.
3. Key modules are cited as `file:symbol`; no file bodies pasted.
"""),
    },
)


# ----------------------------------------------------------------------------- negatives
def neg_case(slug: str, prompt: str, files: dict[str, str], extra: dict[str, str]) -> None:
    case = case_dir(slug)
    (case / "prompt.md").write_text(FRONT + prompt)
    grader(case, "not-routed-to-eevee", NOT_ROUTED)
    grader(case, "no-profile-written", PROFILE_ABSENT)
    grader(case, "fixtures-only-created", regex(r"^\S+$", match=f"count:{len(files)}", flags="m", target="files"))
    for name, body in extra.items():
        grader(case, name, body)


neg_case(
    "eevee-05-neg-list-scripts",
    SETUP + fixture_block(TS_TREE) + "Step 2 — list the npm scripts defined in `package.json` with a one-line description each. Do not profile the repository and do not delegate.\n",
    TS_TREE,
    {"lists-scripts": regex(r"\bdev\b[\s\S]*\btest\b[\s\S]*\blint\b[\s\S]*\bformat\b")},
)

neg_case(
    "eevee-06-neg-map-change",
    SETUP + fixture_block(TS_TREE) + """\
Step 2 — with a sub-agent, map where the following change lands in this codebase: "add an idle TTL to `SessionStore` so sessions untouched for 30 minutes are evicted on the next request through `requireSession`". Return insertion points as `file:symbol`, prior art to mirror, seams, and collisions. This is a change-mapping task, not a repository profile.
""",
    TS_TREE,
    {"maps-insertion-points": regex(r"session-store\.ts:SessionStore|session-middleware\.ts:requireSession")},
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("eevee-")))
