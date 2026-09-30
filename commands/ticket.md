---
description: Take a ticket from intake to tested code — gather context, raise dependencies, agree a plan, implement with unit tests. Never commits.
argument-hint: "<IE-123 | issue URL | pasted thread>"
---

Ticket: $ARGUMENTS — ask once if empty.

## 1. Intake

Build the brief with the `ticket-context` skill. Slug: the Jira key, `gh-<n>` for an issue,
else kebab-case of the first ~6 words. State lives in `.agents/work/<slug>/`; add
`.agents/work/` to `.git/info/exclude` unless it is already ignored. If `plan.md` exists
there, resume from it.

## 2. Investigate — read-only

- Read the project's AGENTS.md / CLAUDE.md, then the code the ticket touches. Use a read-only
  search sub-agent (Explore) for wide sweeps and keep only its conclusions.
- Find the prior art to mirror and the tests covering the area.
- Map the security surface: entry points and their authz checks, sensitive data (PII, tokens,
  secrets), and the safe paths new code must use (validation, parameterised queries, redaction).
- List dependencies: other tickets or PRs, services and teams, migrations, feature flags,
  per-environment config and secrets, API contracts. Raise blockers now.

## 3. Plan — HARD STOP

Ask blocking questions in one bundle. When the design is contested, give 2–3 options with
trade-offs and a recommendation, and iterate until one meets every criterion. Write
`.agents/work/<slug>/plan.md`:

- Goal and acceptance criteria (AC1…, from the brief)
- Approach, plus one line per rejected option
- Files to change — path and responsibility
- Test plan: each AC → unit / integration / manual check
- Security surface — from the investigation, or `none` with the reason
- Dependencies, risks, out of scope

Present it and wait for explicit approval. No edits before that.

## 4. Implement

- Mirror prior art; make the smallest change that meets the criteria; project conventions
  beat your defaults.
- Unit tests for every behaviour change, always; integration tests where the project has them.
- **Parallel, optional:** if the plan splits into 3+ chunks with disjoint files, offer to fan
  out — one spawn per chunk in a single message, at most five: `Machop` for mechanical sweeps,
  `Machoke` for feature slices. Brief each with goal, owned files, prior art, and test
  command. Then integrate and fix the seams yourself.
- If reality diverges from the plan, update the plan and say why.

## 5. Gates

Run the project's test, lint, typecheck, and build commands. Fix until green, or report the
failing output verbatim. Tick each AC in the plan with how it was checked.

Finish with what changed, AC status, and what remains for `/verify` (manual checks) and
`/ship`. Never commit.
