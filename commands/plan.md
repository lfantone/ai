---
description: Turn an approved ticket.md or a tracker ticket into a stored plan — design, decisions, units.
argument-hint: "[slug | Jira key]"
model: opus
effort: high
---

Work root, one folder per repo shared by every worktree:

```bash
W=~/.agents/work/$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')")
```

Work dir: `<work root>/<slug>/`. Slug: $ARGUMENTS, else the one in the branch name, else the
newest folder in the work root — say which. Read-only — never edit code. Resume an existing
`plan.md`.

Plan from `ticket.md` with `Status: approved`. With no `ticket.md`, the tracker ticket the slug
names (a Jira key or `gh-<n>`) is the source of truth: fetch it with the `ticket-context` skill,
or ask for its text if that fails, and save it as `ticket.md` — `Status: approved`,
`Source: <key>`, why, what, criteria (AC1…). Otherwise stop and suggest `/investigate`.

## 1. Study

- Read the guidance for each path the change touches — the nearest `AGENTS.md`, plus any
  `.github/instructions/*.instructions.md` whose `applyTo` matches — then the ticket and the
  code; sweep wide areas with Explore, keeping only its conclusions.
- Find the prior art to mirror and the tests covering it.
- Map the security surface: entry points and their authz checks, sensitive data, and the safe
  paths new code must use (validation, parameterised queries, redaction).

## 2. Decide

Settle every real decision (architecture, data model, contracts, error handling, migrations,
flags) with its reason. When contested, give 2–3 options with trade-offs and a recommendation.

Never assume. Anything the ticket or the repo leaves unclear, contradicts, or may mislead (a
missing or ambiguous criterion, role, value, or contract) is a question. Rate your confidence:
**high** when every decision rests on the ticket, the code, or the user's word; **low** when
any rests on a guess. When low, ask one round of questions in one bundle (only those whose
answers change the plan, each with your default) and wait. Record each answer as a decision,
and a settled criterion in `ticket.md`. Still low after it: say why and offer `/investigate`.

## 3. Plan — HARD STOP

Write `plan.md` — `Status: draft`, then:

- **Approach** — 2–4 sentences
- **Decisions** — D1…: the choice, why, and each rejected option in one line
- **Design** — components, data flow, signatures, data model, config
- **Units** — U1…: goal · owned files · prior art (`file:symbol`) · tests · executor ·
  depends on
- **Test plan** — each AC → unit, integration, or verify (web, api, cli)
- **Security surface** — or `none` with the reason
- **Risks and rollout**

Size each unit so a mid-tier model finishes it without a design choice. Executor: `Machop`
(cheaper) for mechanical sweeps that mirror a pattern, `main` for the rest; parallel `Machop`
units own disjoint files.

Present the plan with its confidence; on explicit approval, set `Status: approved`.

Next: `/implement <slug>` in a fresh session.
