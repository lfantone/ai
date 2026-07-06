# The workflow â how the commands fit together

Four commands cover the life of a change. Three form a pipeline around one artifact; the
fourth reviews any PR, yours or a teammate's:

```
 /plan-orchestrator âââº /implement-orchestrator âââº /verify-orchestrator
        â                        â                          â
        âââââââââââ all write to <cache>/plan-<ticket>.md ââââââââââ
                     (plan â execution log â verification log)

 /review-orchestrator âââº reviews a PR (independent of the pipeline)
```

The design premise: **spend intelligence once, at plan time** â the plan specifies every
step down to exact files, verbatim anchors, and ready-to-apply edits, so implementation
runs on cheap parallel Haiku executors and verification checks the running software
against the plan's own acceptance criteria.

## The recommended cycle

### 1. Plan â `/plan-orchestrator IE-1234`

Cheap agents map the requirement, the repo conventions, and where the change lands; you
refine intent in a short **interview** (don't skip it â it's where ambiguity dies
cheaply); you approve the direction; an Opus author writes the plan; a mechanical pass
verifies every anchor. You iterate until you approve.

> Write acceptance criteria as **observable behavior** â they become the QA scenarios in
> step 3 verbatim.

### 2. Implement â `/implement-orchestrator IE-1234`

Switch to the branch you want first (the command executes on the current branch â you own
branching). It re-checks the plan still matches the code, shows you a checkpoint, then
executes the plan **wave by wave** with parallel Haiku executors, runs the repository's
own gates (tests/lint/build), and offers a gated commit.

Failures never auto-escalate: per failed step you choose â retry with a bigger model,
hot-fix the spec in place, go back to planning, or skip. Interrupted runs **resume** from
the unchecked steps.

### 3. Verify â `/verify-orchestrator IE-1234`

End-to-end QA against the **running software**: you pick the environment (local dev â
reusing or starting the server â or a URL you provide), approve the scenario list, and a
real browser + API probes execute it. The verdict is PASS/FAIL **per acceptance
criterion**, and `verified` requires _your_ acceptance â a green scenario you contest is
not a pass.

### 4. Review â `/review-orchestrator <PR url>`

Independent of the pipeline: reviews any PR (Gitea or GitHub) against its ticket, repo
conventions, and security surface, producing paste-ready `suggestion` blocks and a gated
publish. Re-running after a push reviews **only the new commits**. Use it on your own
pipeline output before merging, or on anyone else's PR.

## One artifact, one status

`plan-<ticket>.md` is the ticket's complete record â plan, execution log, verification
log, fix rounds â moved through a single lifecycle:

```
draft â approved â implemented | partially-implemented â verified | verification-failed
```

Each command owns its transitions; only Verify can grant `verified`. Re-running any
command against any status does the right thing (resume, fix mode, revision, or "nothing
to do").

## When things go wrong

The system routes failures to the cheapest layer that can actually fix them:

| Symptom                             | Route                                                                   |
| ----------------------------------- | ----------------------------------------------------------------------- |
| A step doesn't apply (anchor drift) | Retry ladder: Machop â Machoke â Machamp (you approve each)             |
| The spec is wrong, but locally      | **Hot-fix**: one step re-specced, verified, re-executed                 |
| The spec is wrong structurally      | Back to `/plan-orchestrator` (revision keeps the ledger)                |
| A verification scenario fails       | Verify's **fix loop**: diagnose â repair â re-verify + regression guard |
| A scenario passes but you disagree  | Contest it â the scenario is strengthened and re-run                    |
| The criterion itself is wrong       | Plan revision â spec problems never go to executors                     |

Two rounds of failed fixing always stops and recommends a deeper route â repeated failure
means the problem isn't local.

## What makes re-runs cheap

Everything durable lives in one auto-detected **cache dir** in the target project — `.opencode/cache/`, `.claude/cache/`, or `.agents/cache/`, matching your harness (an existing cache always wins, so state never forks):

- **Profiles** (`repo-profile.md`, `security-profile.md`) â regenerated only when the repo
  materially changes; shared by all commands.
- **Plan artifacts** â the per-ticket record and execution ledger.
- **Bruno collections** (`bruno/<ticket>/`) â API scenarios as re-runnable files; a
  re-verification is one `bru run`. Promote them into the repo for CI.
- **`learnings.md`** â the cross-ticket memory (see the `repo-learnings` skill): gotchas,
  deviation patterns, and environment quirks each flow distills at wrap-up and every
  later flow reads. Ticket N's pain makes ticket N+1 cheaper.

## Ground rules the commands never break

- **Hard stops are real** â no command authors, edits, publishes, commits, or escalates
  without your explicit reply. A recommendation is never permission.
- **Outward actions are individually gated** â publishing to a PR, posting to a ticket,
  committing, pushing: each needs its own yes.
- **Failures are reported honestly** â including warnings when everything passed, and
  degraded coverage when a tool was unavailable.

## Practical tips

- Small tickets plan better â if Mew's plan exceeds ~10 steps, consider splitting the
  ticket.
- Answer the interview properly once; confirmed constraints land in `learnings.md` and
  won't be asked again.
- Run `/review-orchestrator` on the PR even after `verified` â review checks code
  quality/security, verify checks behavior; they overlap less than they seem.
- Keep one catalog clone per project (see the README's Installation notes) so caches and
  learnings stay project-specific.
