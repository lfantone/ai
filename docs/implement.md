# Implementation execution (`/implement-orchestrator`)

Executes an approved implementation plan, wave by wave, with small parallel executors.
Because the [plan](./plan.md) specifies every step down to exact files, verbatim anchors,
and ready-to-apply edits, the default executor is **Haiku** — the plan is the
intelligence, the executors are the hands.

This is **step 2 of the Plan → Implement → Verify flow**. Run `/plan-orchestrator` first;
follow with [`/verify-orchestrator`](./verify.md) for end-to-end QA.

## Usage

```
/implement-orchestrator IE-1234
```

Pass the ticket whose plan to execute; with no argument it lists the plans in
`.agents/cache/` and asks. If no plan exists for the ticket, it stops and asks you to run
`/plan-orchestrator <ticket>` first — it never improvises a plan. Execution happens on the
**current branch** — switch first if you want it elsewhere.

## What it does

1. **Loads the plan** from `.agents/cache/plan-<ticket>.md` and checks it's still
   applicable — if the repo moved since planning, a mechanical pass re-verifies every
   anchor before anything is edited.
2. **Checkpoint** — shows the branch, the steps/waves/files, and the verification gates it
   found, then **stops** for your go-ahead.
3. **Executes wave by wave** — one Haiku executor per step, in parallel within a wave
   (waves touch disjoint files by construction). Each step is ticked off in the plan — and
   in a live task list — **only when it succeeds**.
4. **Verifies** — runs the repository's own gates (tests, lint, typecheck, build).
5. **Wraps up** — updates the plan into an execution ledger and, only on explicit yes,
   commits.

## Escalation — you stay in control

Executors never improvise: a step that doesn't apply cleanly **fails fast** with a precise
reason, and the command **asks you** what to do — it never auto-escalates:

| Choice            | When                                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| Retry with Sonnet | Mechanical failure — anchor drift, formatting                                                         |
| Escalate to Opus  | The spec is right but execution needs judgment                                                        |
| Hot-fix the spec  | The spec is wrong but **locally** — one step is re-specified in place and re-verified, no full replan |
| Back to planning  | The spec is wrong **structurally** — no executor or hot-fix can rescue a bad design                   |
| Skip              | Leave the step (dependents are blocked and reported)                                                  |

Sonnet/Opus retries report every **deviation** from the written edit, and hot-fixes leave
a revision note in the plan — both feed the next plan revision.

## The stops

- **Execution checkpoint** — before any edit: `yes / no`.
- **Every escalation** — per failed step, your choice.
- **Verification failures** — fix via targeted retry, back to planning, or leave as-is.
- **Commit / push / PR** — each only on a separate explicit yes.

## Resumability

The plan's task checklist is the ledger: steps are ticked `[x]` as they complete, so an
interrupted run resumes from the unchecked steps. At the end the artifact gets
`status: implemented` and an `## Execution log` (executor used, retries, deviations,
verification results).

## What's under the hood

| Agent      | Model  | Job                                              |
| ---------- | ------ | ------------------------------------------------ |
| `Magneton` | Sonnet | Re-verifies plan anchors if the repo moved       |
| `Machop`   | Haiku  | Default step executor — mechanical, fails fast   |
| `Machoke`  | Sonnet | Retry executor — tolerates anchor drift          |
| `Machamp`  | Opus   | Last resort — judgment within the step's scope   |
| `Mew`      | Opus   | Hot-fix: re-specifies one wrongly-specified step |

## Requirements

- An approved plan in `.agents/cache/plan-<ticket>.md` (from
  [`/plan-orchestrator`](./plan.md)).
- The agents installed where your harness can find them (see [AGENTS.md](../AGENTS.md)).
