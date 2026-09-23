#!/usr/bin/env python3
"""Regenerate the slowpoke-* cases AND the fake Jira mock (../../mocks/jira/_server.md).

The ticket texts live here once; the mock world and the grader nouns are derived from them,
so they cannot drift apart. Re-run after editing anything below.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parent
MOCKS = SUITE.parent / "mocks" / "jira"

# ----------------------------------------------------------------------------- the fake world
LONG_TICKET = """\
Since the vendor is discontinuing the legacy Node importer licence, we need a Python version of the Harbor Booking Gateway ETL. It should reuse the same technologies wherever possible and may use a different persistent store to replace the importer's object store.

This story is done when:

- There is a `python/` folder under the harbor-etl repository that holds all source and config files.
- It has `.env.*` files that mirror the legacy `config/*.properties` files one-to-one, the same way booking-sync's `.env.*` files mirror its properties.
- The ETL only uses HTTP REST calls, as the legacy importer does, to load the same nine collections into the harbor database.
- Cursors, watermarks and other items the legacy importer persisted are kept in SQLite, exactly as the booking-sync app does.
- The job starts from cron once a day instead of re-implementing the importer's in-process scheduler.
- Instead of INSERT statements, rows are published to Kafka topics named `harbor-<tableName>` (harbor-Activities, harbor-ActivityTypes, ...) through a single common publish function; no per-table writer functions and no pre-existence checks.
- The code takes a `--parquets` option. When present it writes with INSERT+FILES instead of Kafka: batches become parquet objects in the `harbornormal` S3 bucket, in table-DDL column order, driven by a `tables_config.json` with one `baseAttrs` entry per table.
- Writes run in a try/except: transient errors wait 10 seconds and retry for up to one day, then send an Apprise notification and halt; non-transient (filtered-row) errors move the object to the `harborerrors` bucket and notify via Apprise. On a filtered-row failure make ONE salvage attempt (write the good rows as their own object, quarantine only the filtered rows) before quarantining the whole batch.

Windowed collection walk (large collections)

Some collections cannot be walked end to end. The gateway pages at 25 records per page with no page-size control, and past roughly 60,000 pages a tenant returns HTTP 400 ErrorCode 6, undocumented behaviour. One tenant's Readings alone needs about 63,000 pages, so a cold-start backfill of that collection can never complete: it fails, correctly withholds its watermark, and restarts from the beginning on the next run, forever.

A collection may declare a windowing strategy. Collections that do not declare one behave exactly as they do today; this is strictly additive. Readings declares windowing on the Submitted field with a monthly span. EntryDateTime is not used because Modified is null on 99.99% of Readings rows, which would put essentially the whole collection into an unbounded remainder. When a collection's watermark is unset, the walk is split into windows from a configured floor up to the present. The upper bound of every window is clamped to the present: source data contains records dated as far ahead as 2045, and an unclamped walk would iterate for twenty years. Each window keeps its own sub-cursor, scoped per tenant, per collection, per window, so a completed window is not re-fetched when a later one fails. The collection's watermark advances only when every window completed cleanly. Windows are independent units of work on the existing thread pool; per-tenant concurrency is capped so one tenant's backfill cannot monopolise the pool.

Incremental cursor

ChangedSince is accepted by the gateway and, on most collections, ignored. Measured against a live tenant with an impossible cursor (year 2099), 11 of the 19 collections sending it returned a full first page. A collection whose cursor is ignored re-walks its entire history on every run; on Readings that is 1.6M rows and the run does not finish. The last nightly run was still going three days later, with three runs skipped behind its lock. A collection may declare a cursor_field; when set, the incremental request bounds on that field with $filter instead of sending ChangedSince. Readings declares cursor_field = Submitted, the arrival time rather than the business time, so backdated readings are still collected. Existing watermarks are NOT reset when a cursor_field is introduced. A test verifies against the LIVE API that each declared cursor_field is honoured: an impossible bound must return zero rows. It FAILS rather than skips when the API is unreachable; opting out requires HARBOR_SKIP_LIVE=1.

Out of scope in this story is anything related to the reporting module or the report UI tasks.
"""

# nouns a faithful brief must carry, one per "done when" criterion
LONG_CRITERIA_NOUNS = {
    "python-folder": r"python/? folder|`python/`|python directory",
    "env-files": r"\.env",
    "rest-only": r"\bREST\b|HTTP",
    "sqlite": r"SQLite",
    "cron": r"\bcron\b",
    "kafka": r"Kafka",
    "parquets-flag": r"--parquets|parquet",
    "retry-and-notify": r"Apprise|10 seconds|one day|retr(y|ies)",
}
LONG_OUT_OF_SCOPE_NOUN = r"report"
# sentences that only a dump would carry (design rationale, never a criterion)
LONG_DUMP_MARKERS = [r"iterate for twenty years", r"still going three days later", r"99\.99% of Readings rows"]

EPIC_TICKET = """\
Epic: Harbor ETL windowed walks.

Goal: large collections must be walkable end to end without hitting the gateway's page-depth limit.

Acceptance criteria:
- A collection may declare a windowing strategy (`window_field`, `window_span`); collections without one behave exactly as today.
- The upper bound of every window is clamped to the present.
- Each window keeps its own sub-cursor so completed windows are not re-fetched when a later window fails.
- The collection watermark advances only when every window in the walk completed cleanly.
- Per-tenant concurrency is capped on the shared thread pool.

Out of scope: changing the page size (the gateway does not support it) and partitioning by reading type.
"""
EPIC_CRITERIA_NOUNS = {"clamped-to-present": r"clamp", "sub-cursors": r"sub-?cursor"}

THIN_TICKET = "Config only: declare the windowing strategy for MeterReadings. See the parent epic for the acceptance criteria."

WORLD = {
    "HB-2041": {
        "summary": "Python version of the Harbor Booking Gateway ETL",
        "issuetype": "Story",
        "status": "In Progress",
        "assignee": "Dana Whitfield",
        "labels": ["etl", "harbor", "migration"],
        "parent": None,
        "description": LONG_TICKET,
    },
    "HB-2042": {
        "summary": "Harbor ETL: declare MeterReadings windowing config",
        "issuetype": "Task",
        "status": "To Do",
        "assignee": None,
        "labels": ["etl"],
        "parent": "HB-2000",
        "description": THIN_TICKET,
    },
    "HB-2000": {
        "summary": "Harbor ETL windowed walks",
        "issuetype": "Epic",
        "status": "In Progress",
        "assignee": "Dana Whitfield",
        "labels": ["etl", "harbor"],
        "parent": None,
        "description": EPIC_TICKET,
    },
}

DESCRIPTION_ONLY = """\
We need the nightly harbor ETL to send an Apprise notification whenever a run exceeds 6 hours, including the tenant name and the elapsed time, and to write a `run-summary.json` next to the log with per-collection row counts. It must work with the existing cron entry unchanged. Not part of this: changing the retry policy or the cron schedule itself.
"""
DESCRIPTION_OUT_OF_SCOPE_NOUN = r"retry|cron schedule"


# ----------------------------------------------------------------------------- mock files
def write_mock() -> None:
    MOCKS.mkdir(parents=True, exist_ok=True)
    tickets = "\n\n".join(
        f"### {key}\n"
        f"- summary: {t['summary']}\n- issuetype: {t['issuetype']}\n- status: {t['status']}\n"
        f"- assignee: {t['assignee'] or 'unassigned'}\n- labels: {', '.join(t['labels'])}\n"
        f"- parent: {t['parent'] or 'none'}\n- description (return EXACTLY this text, verbatim, as `fields.description`):\n\n"
        + "\n".join("    " + line for line in t["description"].splitlines())
        for key, t in WORLD.items()
    )
    body = f"""---
type: agent
tools: [getJiraIssue]
abort_when: |
  - getJiraIssue is called with an issue key that the user's request never mentioned and that is not the `parent` of a ticket already returned in this run (fetching the wrong ticket is the regression this suite exists to catch).
  - getJiraIssue is called three or more times in one run.
  - a tool other than getJiraIssue is requested from this server.
---
You are a fake Jira Cloud instance for the "Harbor" project (key prefix `HB`). You answer
`getJiraIssue` calls with a JSON object shaped like the Jira REST v3 issue resource:

```json
{{"id": "<numeric>", "key": "<KEY>", "fields": {{
  "summary": "...", "issuetype": {{"name": "..."}}, "status": {{"name": "..."}},
  "assignee": {{"displayName": "..."}} | null, "labels": [...],
  "parent": {{"key": "..."}} (omit when none),
  "description": "<the description text below, verbatim, as a plain string>"
}}}}
```

Return `fields.description` as the exact text written for the ticket below, character for
character; do not summarize, reformat, or convert it to Atlassian Document Format. Ignore the
`fields`/`expand` arguments except that the description must always be included.

For any key that is not listed below, return a tool ERROR with the Jira 404 body:
`{{"errorMessages": ["Issue does not exist or you do not have permission to see it."], "errors": {{}}}}`.

## Tickets

{tickets}
"""
    (MOCKS / "_server.md").write_text(body)
    (MOCKS / "_tools.json").write_text(json.dumps({
        "_note": "Hand-written approximation of the Atlassian MCP connector's getJiraIssue schema; the real tools/list was not obtainable without credentials in the authoring session.",
        "tools": [{
            "name": "getJiraIssue",
            "description": "Get the details of a Jira issue by its key or id. Returns the issue resource including summary, description, status, assignee, labels and parent.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cloudId": {"type": "string", "description": "Atlassian cloud id (optional when a single site is configured)"},
                    "issueIdOrKey": {"type": "string", "description": "Issue key such as HB-2041, or numeric id"},
                    "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to include; defaults to all navigable fields"},
                    "expand": {"type": "string", "description": "Comma-separated expansions such as renderedFields"},
                },
                "required": ["issueIdOrKey"],
            },
        }],
    }, indent=2) + "\n")


# ----------------------------------------------------------------------------- case plumbing
FRONT = """---
max_turns: 8
timeout_seconds: 180
allowed_tools: [Agent]
plugins: [../../..]
model: sonnet
runs: 5
---
"""

BRIEF_ASK = """Get me the requirement brief for the ticket below using a sub-agent; do not read the ticket yourself. Return the sub-agent's brief verbatim and nothing else. The brief has exactly these five sections, in this order, and stays under 200 words: **Goal**, **Acceptance criteria** (bulleted), **Scope**, **Out of scope**, **Constraints**. Empty sections say _None._

"""

TOOL = "mcp__jira__getJiraIssue"


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


def tool_used(tool: str, lo: int, hi: int | None, arm: str = "both", extra: str = "") -> str:
    fm = f"---\ntype: tool_used\ntool: {tool}\nmin: {lo}\n"
    if hi is not None:
        fm += f"max: {hi}\n"
    fm += f"arm: {arm}\n{extra}---\n"
    return fm


ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Slowpoke\nmin: 1\narm: with-only\nweight: 0.01\n---\n"
NOT_ROUTED = "---\ntype: tool_used\ntool: Agent\ninput_match: Slowpoke\nmin: 0\nmax: 0\narm: both\n---\n"

SECTIONS = r"\*\*Goal\*\*.*\*\*Acceptance criteria\*\*.*\*\*Scope\*\*.*\*\*Out of scope\*\*.*\*\*Constraints\*\*"
WORD_BUDGET = r"(?:\S+\s+){230}"
PREAMBLE = r"^\s*(I'll|I will|Let me|First,|Here is|Here's|Sure)"
RAW_JSON = r'"fields"\s*:|"issuetype"|"type"\s*:\s*"doc"'


def after_header(header: str, noun: str) -> str:
    """noun appears in the text following the given bold header (dotall)."""
    return rf"\*\*{header}\*\*[\s\S]*?({noun})"


def fire_case(slug: str, prompt: str, extra: dict[str, str], *, sections: bool = True) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt.strip() + "\n")
    if sections:
        grader(case, "five-sections-in-order", regex(SECTIONS, flags="s"))
        grader(case, "under-word-budget", regex(WORD_BUDGET, match="not_contains"))
    grader(case, "no-preamble", regex(PREAMBLE, match="not_contains"))
    grader(case, "no-raw-json", regex(RAW_JSON, match="not_contains"))
    grader(case, "routed-to-slowpoke", ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


def neg_case(slug: str, prompt: str, extra: dict[str, str]) -> None:
    case = SUITE / slug
    shutil.rmtree(case, ignore_errors=True)
    case.mkdir(parents=True)
    (case / "prompt.md").write_text(FRONT + prompt.strip() + "\n")
    grader(case, "not-routed-to-slowpoke", NOT_ROUTED)
    for name, body in extra.items():
        grader(case, name, body)


write_mock()

# ----------------------------------------------------------------------------- 01 long ticket
fire_case(
    "slowpoke-01-long-ticket",
    BRIEF_ASK + "Ticket: HB-2041",
    {
        "fetched-once": tool_used(TOOL, 1, 1),
        **{f"criterion-{k}": regex(after_header("Acceptance criteria", v), flags="i") for k, v in LONG_CRITERIA_NOUNS.items()},
        "out-of-scope-captured": regex(after_header("Out of scope", LONG_OUT_OF_SCOPE_NOUN), flags="i"),
        "no-dump": regex("|".join(LONG_DUMP_MARKERS), match="not_contains", flags="i"),
        "faithful-brief": llm("""
The answer is a requirement brief extracted from a long Jira story. The story has a two-sentence goal, eight "This story is done when" criteria (python folder, .env files mirroring properties, REST-only loading of nine collections, SQLite persistence, cron start, Kafka topics via one publish function, a --parquets INSERT+FILES mode with S3 buckets, and retry/notify/quarantine error handling), two long design-rationale sections (windowed collection walk, incremental cursor), and a final sentence excluding the reporting module and report UI tasks. All claims must hold to pass.

1. The Acceptance criteria bullets correspond to the eight "done when" items. Design-rationale details (page-depth limits, ChangedSince being ignored, sub-cursors, the live-API test) may appear under Constraints or Scope but are NOT presented as acceptance criteria, and nothing is invented.
2. The Out of scope section names the reporting module / report UI tasks. It is not merged into Scope and not omitted.
3. The brief is a summary, not a dump: no paragraph of the description is reproduced verbatim, and the whole answer is compact (about 200 words or fewer).
4. There is no preamble, no narration of what the agent did, and no trailing commentary.
"""),
    },
)

# ----------------------------------------------------------------------------- 02 description only
fire_case(
    "slowpoke-02-description-only",
    BRIEF_ASK + "There is no ticket yet; this is the description as the product owner wrote it:\n\n" + DESCRIPTION_ONLY,
    {
        "no-jira-call": tool_used(TOOL, 0, 0),
        "out-of-scope-captured": regex(after_header("Out of scope", DESCRIPTION_OUT_OF_SCOPE_NOUN), flags="i"),
        "criterion-notification": regex(after_header("Acceptance criteria", r"Apprise|notif"), flags="i"),
        "criterion-summary-file": regex(after_header("Acceptance criteria", r"run-summary\.json|summary"), flags="i"),
        "text-only-brief": llm("""
The answer is a requirement brief built from a free-text description with no ticket. All claims must hold to pass.

1. Acceptance criteria cover: an Apprise notification when a run exceeds 6 hours carrying tenant name and elapsed time, and a `run-summary.json` written next to the log with per-collection row counts.
2. Out of scope lists changing the retry policy and changing the cron schedule.
3. Constraints mention that the existing cron entry stays unchanged (or Constraints says _None._ and that fact appears under Scope). No ticket key or Jira reference is invented.
4. All five sections are present; the answer is compact and has no preamble.
"""),
    },
)

# ----------------------------------------------------------------------------- 03 thin ticket with parent
fire_case(
    "slowpoke-03-thin-ticket-parent",
    BRIEF_ASK + "Ticket: HB-2042",
    {
        "fetched-at-most-twice": tool_used(TOOL, 1, 2),
        **{f"epic-criterion-{k}": regex(after_header("Acceptance criteria", v), flags="i") for k, v in EPIC_CRITERIA_NOUNS.items()},
        "criteria-from-parent": llm("""
The answer is a requirement brief for a thin Jira task whose one-line description defers to its parent epic. All claims must hold to pass.

1. The Acceptance criteria are the epic's: declarable windowing strategy, window upper bound clamped to the present, per-window sub-cursors, watermark advancing only when all windows complete, per-tenant concurrency cap. At least four of these five appear.
2. The Scope reflects the task itself: declaring the windowing config for MeterReadings.
3. Out of scope carries the epic's exclusions (page size, partitioning by reading type) or says _None._; nothing is invented.
4. No raw ticket JSON or verbatim description dump; compact; no preamble.
"""),
    },
)

# ----------------------------------------------------------------------------- 04 not found
fire_case(
    "slowpoke-04-not-found",
    BRIEF_ASK + "Ticket: HB-9999",
    {
        "attempted-fetch": tool_used(TOOL, 1, None),
        "says-not-found": regex(r"not found|does ?n[o']t exist|doesn't exist|could ?n[o']t (be )?(find|found|fetch(ed)?|retriev(e|ed)|locat(e|ed))|no (such )?(ticket|issue)|unable to|not (accessible|available)|isn't accessible", flags="i"),
        "no-invented-criteria": regex(r"\*\*Acceptance criteria\*\*[^\n]*\n\s*[-*] (?!_?None|N/A|n/a|none)\S", match="not_contains", flags="m"),
        "honest-failure": llm("""
The answer concerns a Jira ticket (HB-9999) that the Jira tool reported as non-existent. All claims must hold to pass.

1. The answer states clearly that HB-9999 could not be found / does not exist.
2. It does not fabricate a goal, acceptance criteria, scope, or constraints for the ticket. Empty sections written as _None._ are acceptable; invented content is not.
3. It does not pretend the fetch succeeded, and it may suggest checking the key or pasting the ticket text.
"""),
    },
    sections=False,
)

# ----------------------------------------------------------------------------- 05 negative: status lookup
neg_case(
    "slowpoke-05-neg-status-lookup",
    "What is the current status and who is the assignee of Jira ticket HB-2041? Answer in one line; I do not need the requirements or a brief.",
    {
        "no-brief": regex(r"\*\*Acceptance criteria\*\*", match="not_contains"),
        "status-and-assignee": regex(r"In Progress[\s\S]*Whitfield|Whitfield[\s\S]*In Progress"),
        "one-line-answer": llm("""
The answer is a one-line status lookup for a Jira ticket. All claims must hold to pass.

1. It reports the status "In Progress" and the assignee "Dana Whitfield" for HB-2041.
2. It does not include a requirement brief, acceptance criteria, scope sections, or a summary of the ticket description.
"""),
    },
)

# ----------------------------------------------------------------------------- 06 negative: draft criteria
neg_case(
    "slowpoke-06-neg-draft-criteria",
    "Draft acceptance criteria for a feature we have not ticketed yet: a `--dry-run` flag for the harbor ETL that fetches and transforms every collection but writes nothing, printing per-collection row counts at the end. Five to seven bullets, testable wording. Do not look anything up.",
    {
        "no-jira-call": tool_used(TOOL, 0, 0),
        "no-brief-sections": regex(r"\*\*Out of scope\*\*", match="not_contains"),
        "mentions-dry-run": regex(r"--dry-run|dry.run", flags="i"),
        "drafted-not-extracted": llm("""
The answer drafts acceptance criteria for a described feature. All claims must hold to pass.

1. It contains five to seven bullet criteria in testable wording about a `--dry-run` flag, covering at least: no writes to any destination; every collection is still fetched and transformed; per-collection row counts are printed at the end. Extra criteria such as exit codes, totals or failure reporting are fine.
2. It does not claim to have read or fetched a Jira ticket, and it does not use the five-section brief layout (Goal / Acceptance criteria / Scope / Out of scope / Constraints).
"""),
    },
)

print("generated:", sorted(p.name for p in SUITE.iterdir() if p.name.startswith("slowpoke-")))
print("mock:", sorted(p.name for p in MOCKS.iterdir()))
