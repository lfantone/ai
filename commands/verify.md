---
description: Check a change in a running environment — scenarios from the plan's acceptance criteria, run in browser and API, PASS/FAIL per criterion.
argument-hint: "[local | env URL] [ticket]"
---

Target: $ARGUMENTS. Criteria come from `.agents/work/<slug>/plan.md` (slug from the ticket or
branch); with no plan, ask what behaviour proves the change.

## 1. Environment — HARD STOP

Ask once. Local: is the dev server running (URL), or should you start it (command from
AGENTS.md or the package scripts)? Other environment: base URL, and may mutating scenarios
run? Never assume a shared environment is disposable; start or stop nothing outside local.

## 2. Scenarios

At least one per AC, plus the obvious edge case:

```text
V1 · web|api|cli · mutating: yes|no · AC1
  pre: <setup, or none>
  steps: <numbered, concrete>
  expect: <one observable result>
```

- Literal values only — no placeholders, no "or equivalent".
- One outcome per expect (status, field, visible text); split either/or cases.
- No conditional steps: a missing mechanism becomes `pre:` or "not verifiable here".
- One surface per scenario; setup belongs in `pre:`.

Show counts per surface and mutating, then wait for yes / adjust.

## 3. Run

- A server you start: run it in the background, poll health for ~60 s, stop it at the end.
- api / cli: the `bruno-cli` skill; keep the collection in `.agents/work/<slug>/bruno/` so a
  rerun is one `bru run`.
- web: spawn `Ditto` with BASE_URL, the web scenarios, and whether mutating is allowed. On
  `blocked`, check routes over HTTP and flag degraded coverage.
- Run api and web in parallel; retry a flaky failure once and say so.

## 4. Report

Per AC: PASS / FAIL with one line of evidence (failing assert, screenshot path), plus warnings
(console errors, failed requests) even when green. Append a dated `## Verification` section
to the plan.

Local failure: diagnose and fix in this session, rerun the failed scenarios, then the project
tests and the full set. Remote failure: report it; fix locally and redeploy first.

Offer to post the verdict to the ticket (Jira `addCommentToJiraIssue` or a forge comment) —
only on an explicit yes.
