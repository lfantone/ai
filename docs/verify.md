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

It reads the plan from `.agents/cache/plan-<ticket>.md`. No plan? It asks what was
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

## On failure

The report tells you where to go next: execution-level issues route back to
[`/implement-orchestrator`](./implement.md) (hot-fix path, resumes from the failing
step); design-level gaps route to a [`/plan-orchestrator`](./plan.md) revision. The
`## Verification log` appended to the plan keeps the whole ticket's Plan → Implement →
Verify record in one artifact.

## What's under the hood

| Agent       | Model  | Job                                                     |
| ----------- | ------ | ------------------------------------------------------- |
| `Abra`      | Sonnet | Turns acceptance criteria into executable scenarios     |
| `Ditto`     | Sonnet | Web E2E — drives a real browser via Chrome DevTools MCP |
| `Magnemite` | Sonnet | API/CLI runtime probes — curl + jq assertions           |

## Requirements

- The implemented change (usually via [`/implement-orchestrator`](./implement.md)) and
  its plan in `.agents/cache/`.
- For web verification: the **Chrome DevTools MCP** server available to your harness.
- A runnable dev server (local mode) or a reachable environment URL.
