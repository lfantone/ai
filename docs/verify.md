# Verification / QA (`/verify-orchestrator`)

End-to-end QA of an implemented change — against the **running software**, not the code.
Scenarios are derived from the plan's acceptance criteria, then executed for real: a
browser drives the web UI (via the Chrome DevTools MCP) and HTTP/CLI probes hit the API.
You get a PASS/FAIL verdict per acceptance criterion, with evidence.

This is **step 3 of the Plan → Implement → Verify flow**.

## Usage

```
/verify-orchestrator IE-1234
```

It reads the plan from `<cache>/plan-<ticket>.md`. No plan? It asks what was
implemented and what behavior proves it works, and verifies against that.

## What it does

1. **Loads the contract** — the plan's acceptance criteria, change map, and execution log
   (including any deviations from implementation).
2. **Asks where to test** — one bundled question: local dev (reusing your already-running
   server, or starting one itself — and stopping only what it started) or another
   environment (you give the base URL). On shared environments, mutating scenarios are
   skipped unless you explicitly allow them.
3. **Designs scenarios** — every acceptance criterion gets at least one concrete,
   observable check; collision areas get regression checks. You approve the list before
   anything runs.
4. **Runs them** — web scenarios in a real browser (navigate, click, fill, assert what's
   visible; screenshots + console/network errors on failure), API/CLI scenarios as exact
   requests with status/body assertions. Both surfaces run in parallel.
5. **Reports** — PASS/FAIL per criterion with evidence, warnings even when green, and a
   final `verified` / `verification-failed` status written into the plan artifact.

## The stops

- **Environment** — local dev vs another environment (and whether mutating scenarios may
  run there).
- **Scenario approval** — the checklist before any execution: `yes / adjust / no`.
- **Posting the verdict** to the ticket — only on explicit yes.

## On failure — you choose the route

A `verified` status requires **your acceptance, not just green scenarios** — a PASS you
contest is not a pass. Per failed (or contested) criterion, the command recommends one
route and asks:

| Route                   | When                                                                                                                     |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Fix now                 | The failure traces to an edit — diagnose → re-spec → execute → re-run only the failed scenarios                          |
| Implement fix mode      | Skipped steps / deviations are the likely cause — [`/implement-orchestrator`](./implement.md) reads the Verification log |
| Plan revision           | The design can't meet the criterion — [`/plan-orchestrator`](./plan.md)                                                  |
| Strengthen the scenario | A contested PASS: the check was a weak proxy; it's re-derived and re-run                                                 |
| Criterion is wrong      | A requirements gap — plan revision, never routed to an executor                                                          |

Fix rounds are user-gated and **local-only** (fixes edit the local tree — on a remote
environment, fix and redeploy first). After a fix, the failed scenarios re-run first;
once green, the repo's own gates and the **full scenario set** re-run to guard against
regressions — a fix that breaks something else is a FAIL. After two failed rounds it
stops and recommends a deeper route. If coverage was impossible rather than failing
(e.g. the Chrome MCP is missing), the run reports `verification-blocked` and leaves the
plan status untouched. The `## Verification log` appended to the plan keeps the whole
ticket's Plan → Implement → Verify record — including fix rounds — in one artifact.

## What's under the hood

| Agent       | Model  | Job                                                                                               |
| ----------- | ------ | ------------------------------------------------------------------------------------------------- |
| `Abra`      | Sonnet | Turns acceptance criteria into executable scenarios                                               |
| `Ditto`     | Sonnet | Web E2E — drives a real browser via Chrome DevTools MCP                                           |
| `Magnemite` | Sonnet | API E2E — authors and runs a [Bruno](https://usebruno.com) collection (curl fallback); CLI probes |

API scenarios are written as a **Bruno collection** at `<cache>/bruno/<ticket>/`
(via the [`bruno-cli`](../skills/bruno-cli) skill) — a persistent, git-friendly artifact
with declarative assertions. Re-running verification is then one `bru run` instead of a
re-authoring, and the collection can be promoted into the repo for CI.

Environment gotchas and fix-round root causes are distilled into
`<cache>/learnings.md` (the `repo-learnings` skill) — cross-ticket memory every
flow reads, so the next verification doesn't rediscover them.

## Requirements

- The implemented change (usually via [`/implement-orchestrator`](./implement.md)) and
  its plan in the cache dir (auto-detected: `.opencode/cache/`, `.claude/cache/`, or `.agents/cache/`).
- For web verification: the **Chrome DevTools MCP** server available to your harness.
- For API verification: the [`bru` CLI](../skills/bruno-cli) (`@usebruno/cli`, used via
  `npx` if not installed) — falls back to curl without it.
- A runnable dev server (local mode) or a reachable environment URL.
