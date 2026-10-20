---
description: Verify the change in a running app — browser or Bruno scenarios, PASS/FAIL per criterion.
argument-hint: "[local | env URL] [slug]"
---

Target: $ARGUMENTS. Work root, one folder per repo shared by every worktree:

```bash
W=~/.agents/work/$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')")
```

Work dir: `<work root>/<slug>/`. Slug: given, else the one in the branch name, else the newest
folder in the work root. Criteria come from `ticket.md`, surfaces from the plan's test plan;
with neither, ask what behaviour proves the change.

## 1. Environment — HARD STOP

Ask once. Local: is the dev server running (URL), or should you start it (from AGENTS.md
or the package scripts)? Other environment: base URL, and may mutating scenarios
run? Never assume a shared environment is disposable; start or stop nothing outside local.
If `AGENTS.md` declares a sign-in for the target, open BASE_URL with the browser tools, let
the user sign in, and continue on their word; `Ditto` reuses that browser session. API
scenarios don't share it: they need a credential the user hands over (`bruno-cli`'s signed-in
requests), or are `BLOCKED`.

## 2. Scenarios

Keep them in `verify.md`, reusing existing ones: at least one per AC, plus the obvious edge
case:

```text
V1 · web|api|cli · mutating: yes|no · AC1
  pre: <setup, or none>
  steps: <numbered, concrete>
  expect: <one observable result>
```

- Literal values only — no placeholders, no "or equivalent".
- One outcome per expect; split either/or cases.
- No conditional steps: a missing mechanism becomes `pre:` or "not verifiable here".
- One surface per scenario.

Show counts per surface and mutating, then wait for yes / adjust.

## 3. Run

- A server you start: run it in the background, poll health ~60 s, stop it after.
- api: the `bruno-cli` skill; keep the collection in `bruno/` in the work dir so a rerun is
  one `bru run`. Signed-in runs start with the preflight; a sign-in failure is `BLOCKED`,
  not FAIL. cli: compare the command's output with the expect line.
- web: spawn `Ditto` with BASE_URL, the web scenarios, and whether mutating is allowed. On
  `blocked`, check routes over HTTP and flag degraded coverage.
- Run api and web in parallel; retry a flaky failure once and say so.

## 4. Report

Append a dated run to `verify.md`: environment, the tested working tree's id (below), one line
per scenario (`V<n>: PASS | FAIL | BLOCKED — <evidence or reason>`), then PASS / FAIL /
NOT VERIFIED per AC (a BLOCKED scenario leaves its AC not verified), plus warnings even when
green.

```bash
I=$(mktemp) && cp "$(git rev-parse --git-path index)" "$I" && GIT_INDEX_FILE=$I git add -A && GIT_INDEX_FILE=$I git write-tree; rm -f "$I"
```

Fix nothing here: failures go to `/implement <slug>`; all green → `/ship <slug>`. Offer to
post the verdict to the ticket — only on an explicit yes.
