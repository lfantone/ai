---
description: Implement the approved plan, or fix what verify and review found. Never commits.
argument-hint: "[slug]"
model: sonnet
effort: medium
---

Work root, one folder per repo shared by every worktree:

```bash
W=~/.agents/work/$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')")
```

Work dir: `<work root>/<slug>/`. Slug: $ARGUMENTS, else the one in the branch name, else the
newest folder in the work root — say which. Needs `plan.md` with `Status: approved`, or
`open` findings in `review.md`; otherwise stop and suggest `/plan`.

## 1. Work list

In order: the plan's unchecked units, the FAIL lines of the latest run in `verify.md` not
marked `fixed`, then the `open` findings in `review.md`. Criteria come from `ticket.md`.

## 2. Build

- Follow the plan and the touched paths' guidance (nearest `AGENTS.md`, matching
  `.github/instructions/*.instructions.md`): keep its decisions, mirror the cited
  prior art, make the smallest change.
- Unit tests for every behaviour change; integration tests where the project has them.
- Ready units whose executor is `Machop`: spawn them in one message, at most five, files
  disjoint, each briefed with goal, owned files, prior art, the decisions and signatures to
  keep, and test command. Do `main` units yourself.
- Reality differs from the plan: a local detail → do it and log it under `## Deviations` in
  `plan.md` with the reason; anything that changes a decision or a criterion → stop and ask.

## 3. Gates

Run the project's test, lint, typecheck, and build. Fix the failures this change caused;
report any others verbatim. Tick done units in `plan.md`; mark fixed FAIL lines and
findings `fixed`. Never commit.

If the work, or a review finding it fixed, revealed a reusable rule for a path that its
guidance lacks, offer to add it as one line to that guidance (the file `AGENTS.md` names for
the path, else the nearest `AGENTS.md`) — only on a yes.

Next: `/verify local <slug>`, then `/ship <slug>`.
