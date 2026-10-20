---
description: Investigate a request and write the ticket — why, what, acceptance criteria.
argument-hint: "<IE-123 | issue URL | pasted thread | idea>"
model: opus
effort: xhigh
---

Request: $ARGUMENTS — ask once if empty. Spend the effort here: the plan and the code inherit
every gap this phase leaves. Read-only — never edit code.

## 1. Intake

Fetch any ticket or thread with the `ticket-context` skill. Slug: the Jira key, `gh-<n>` for
an issue, else kebab-case of the first ~5 words. Work dir: `<work root>/<slug>/`; resume an
existing `ticket.md`. The work root is one folder per repo, shared by every worktree:

```bash
W=~/.agents/work/$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')")
```

## 2. Investigate

- **Why** — the problem, who it affects, and the evidence: current behaviour in the code,
  history (`git log`, blame, linked PRs), related tickets. Reproduce a bug when it is cheap.
- **What** — the behaviour that must change, in user-visible terms.
- **How to drive it** — constraints, sequencing, rollout or flags, teams to involve.
- **Dependencies** — tickets, services, migrations, config or secrets, API contracts. Raise
  blockers now.

Sweep wide areas with a read-only search sub-agent (Explore); keep only its conclusions.

## 3. Ticket — HARD STOP

Ask every question that changes the why, the what, or a criterion, in one bundle; repeat
until none remain. Write `ticket.md` — `Status: draft` and `Source: <key, URL, or none>`, then:

- **Why** and **What**
- **Acceptance criteria** — AC1…: observable, testable, one outcome each
- **Scope** — in and out
- **How to drive it**
- **Context** — key code as `file:symbol`, current behaviour
- **Dependencies and risks**
- **Open questions** — none, or each with an owner

Present it and wait for explicit approval, then set `Status: approved`. Offer to create or
update the tracker ticket from it with `ticket-context` — only on an explicit yes; put a new
key in `Source:`.

Next: `/plan <slug>` in a fresh session.
