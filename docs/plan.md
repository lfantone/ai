# Implementation planning (`/plan-orchestrator`)

An orchestrated, context-rich planning flow for a ticket or feature. Cheap agents map the
repo and the requirement in parallel, you refine intent in a short interview, and a
heavyweight author produces a standardized, verifiable implementation plan grounded in the
repo's own patterns.

This is **step 1 of a Plan → Implement → Verify flow**: the output is a plan artifact, not
code changes. The [Implement step](./implement.md) executes the saved plan — and because
every step is specified down to exact, anchored edits, execution runs on small
(Haiku-level) models. The [Verify step](./verify.md) then QAs the result end-to-end
against the plan's acceptance criteria.

## Usage

```
/plan-orchestrator [ticket id/description]
```

Examples:

```
/plan-orchestrator IE-1234
/plan-orchestrator "add rate limiting to the login endpoint"
```

If you pass nothing, it asks once what to plan. If a plan for the ticket already exists,
the run becomes a **revision** of it rather than starting cold.

## What it does

1. **Checks what it can reuse** — repo and security profiles cached by earlier runs (shared
   with [code review](./code-review.md)) are reused when fresh.
2. **Gathers context in parallel** — cheap agents brief the requirement (goal, acceptance
   criteria, constraints), the repo conventions, and the code map: where the change lands,
   prior art to mirror, seams to plug into.
3. **Interviews you** — shows what it understood, then asks the 3–7 questions that would
   most change the design. **Mandatory by default**; say "skip the interview" to opt out.
4. **Confirms the direction** — presents the learnings and the intended shape of the
   solution, and waits for your approval before the expensive authoring pass.
5. **Authors the plan** — an Opus agent writes the standardized plan: exact files, verbatim
   anchors, ready-to-apply before→after edits (no design decisions left), trade-offs, and
   steps decomposed into parallel **waves** with an explicit dependency graph.
6. **Verifies it** — a mechanical pass checks every cited `file:symbol` exists, every edit
   anchor matches exactly once, and the dependency graph is sound (acyclic, consistent ids,
   file-disjoint waves).
7. **Iterates until you approve** — review the plan, request revisions round after round,
   then the approved artifact is saved.

## The stops

The command pauses and waits for you at these points — it never proceeds on its own:

- **Interview** — after context gathering (skippable only on explicit request).
- **Direction approval** — before authoring: `yes / adjust / no`.
- **Plan acceptance** — after verification: `approve / revise: <what> / no`.
- **Posting to the ticket** — optional at the end, only on explicit `yes`.

## Output

A standardized plan saved to `.agents/cache/plan-<ticket>.md` (`status: draft` during
iteration, `approved` when finalized). It always contains, in order: objective, context &
constraints, design overview with trade-offs, a change map, a task checklist, an execution
plan (parallel waves + dependency DAG + critical path), detailed steps with exact anchored
edits, data/schema changes, testing plan, rollout, future-proofing, and risks/open
questions.

Step ids (`S1`, `S2`, …) are stable across the checklist, waves, and step details — the
Implement step relies on them.

## What's under the hood

The command is a thin orchestrator (**Slowbro**). The work is done by agents in
[`agents/`](../agents) — three shared with code review, three specific to planning:

| Agent       | Model  | Job                                              |
| ----------- | ------ | ------------------------------------------------ |
| `Slowpoke`  | Haiku  | Requirement brief _(shared)_                     |
| `Eevee`     | Sonnet | Repository conventions & patterns _(shared)_     |
| `Growlithe` | Sonnet | Security profile _(shared; only when stale)_     |
| `Dugtrio`   | Sonnet | Code cartographer — where the change lands       |
| `Mew`       | Opus   | Plan author                                      |
| `Magneton`  | Sonnet | Plan verifier — `file:symbol` + dependency graph |

## Caching

Plans and profiles live in `.agents/cache/` inside the target project (see the README's
Installation section):

| File                  | Holds                                    | Owner        |
| --------------------- | ---------------------------------------- | ------------ |
| `repo-profile.md`     | Stack & conventions _(shared)_           | `Eevee`      |
| `security-profile.md` | Threat surface _(shared)_                | `Growlithe`  |
| `plan-<ticket>.md`    | The plan artifact (draft, then approved) | orchestrator |

The profiles are shared with the review orchestrator — whichever command refreshes them,
the other benefits. Re-running the command for the same ticket revises the existing plan.

## Requirements

- A Jira tool available (for ticket briefs by reference) — or paste the ticket text.
- The forge CLI ([`tea`](../skills/tea-cli) for Gitea, [`gh`](../skills/gh-cli) for
  GitHub), if related PRs/issues are referenced.
- The agents and skill installed where your harness can find them (see
  [AGENTS.md](../AGENTS.md)).
