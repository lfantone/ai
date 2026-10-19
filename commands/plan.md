---
description: Turn the approved ticket into a stored technical plan — design, decisions, units.
argument-hint: "[slug]"
model: opus
effort: high
---

Work root, one folder per repo shared by every worktree:

```bash
W=~/.agents/work$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')
```

Work dir: `<work root>/<slug>/`. Slug: $ARGUMENTS, else the one in the branch name, else the
newest folder in the work root — say which. Needs `ticket.md` with `Status: approved`;
otherwise stop and suggest `/investigate`. Read-only — never edit code. Resume an existing
`plan.md`.

## 1. Study

- Read the guidance for each path the change touches — the nearest `AGENTS.md` or
  `CLAUDE.md`, plus any `.github/instructions/*.instructions.md` whose `applyTo` matches —
  then the ticket's Context and the code; sweep wide areas with Explore and keep only its
  conclusions.
- Find the prior art to mirror and the tests that cover the area.
- Map the security surface: entry points and their authz checks, sensitive data (PII, tokens,
  secrets), and the safe paths new code must use (validation, parameterised queries,
  redaction).

## 2. Decide

Settle every real decision — architecture, data model, contracts, error handling,
migrations, flags — with its reason. When one is contested, give 2–3 options with
trade-offs and a recommendation. Ask blocking questions in one bundle.

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

Size each unit so a mid-tier model finishes it without making a design choice. Executor:
`Machop` (a cheaper model) for mechanical sweeps that mirror a pattern, `main` for the rest;
`Machop` units that may run in parallel own disjoint files.

Present the plan and wait for explicit approval, then set `Status: approved`.

Next: `/implement <slug>` in a fresh session.
