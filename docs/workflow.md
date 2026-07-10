# The workflow

Three commands move one plan artifact through delivery; review is independent:

```text
/plan-orchestrator → /implement-orchestrator → /verify-orchestrator
       │                       │                         │
       └────────── <cache>/plan-<ticket>.md ────────────┘

/review-orchestrator → reviews a PR and may feed review mode
```

## Design premise

Spend judgment in planning, then route each implementation contract to the cheapest capable
executor:

- Precise plans contain exact contracts for Haiku/GPT-mini.
- Fast plans may contain guided contracts for Sonnet.
- Complete preconditions are checked during authoring and immediately before editing.
- Structural plan verification is separate from PR line-anchor verification.

No runtime scripts or patch applicators are shipped. The installed agents use their harness's
native read/edit/shell tools under the plan's explicit boundaries.

## Recommended cycle

### 1. Plan

Use `/plan-orchestrator <ticket>` for the default precise path or add `--fast` for shorter,
more adaptive planning. Requirements are normalized before code mapping. You approve the
complete structurally valid plan; there is no intermediate direction-approval stop.

### 2. Implement

`/implement-orchestrator <ticket>` shows exact/guided costs, executes file-disjoint waves,
and runs repository gates. Exact contracts route to Machop; guided contracts route to
Machoke. Preconditions, not the saved HEAD alone, decide whether a contract applies.

### 3. Verify

`/verify-orchestrator <ticket>` derives runtime scenarios from acceptance criteria and checks
the running UI/API/CLI. It proceeds normally only from `implemented`; repository-gate failures
return to implementation remediation.

### 4. Review

`/review-orchestrator <PR>` fetches the active diff once, shares the temporary file between
both reviewers, persists findings, then deletes the raw diff. Re-reviews validate profile
freshness before reuse and review only the new delta.

## Artifact lifecycle

```text
draft → approved
          ├─→ partially-implemented
          ├─→ implementation-failed → implemented
          └─→ implemented → verified | verification-failed
```

Only Implement grants `implemented`; only Verify grants `verified`. A verification fix keeps
`verification-failed` until runtime scenarios are rerun.

## Failure routes

| Symptom                          | Route                                    |
| -------------------------------- | ---------------------------------------- |
| Exact precondition drift         | Machoke retry or exact re-spec           |
| Guided contract lacks a decision | Exact re-spec or plan revision           |
| Contract is wrong locally        | Mew → Magneton structural check → Machop |
| Design/scope is wrong            | Plan revision                            |
| Repository gate fails            | `implementation-failed` remediation      |
| Runtime scenario fails           | Verify fix loop or plan revision         |

## Durable and temporary state

Durable cache files include profiles, plans/ledgers, review findings, Bruno collections, and
`learnings.md`. Raw review/planning diffs live only under `$CACHE/tmp` during the active run;
they are deleted after durable state is written and cleaned on the next run after interruption.

Outward actions remain gated: ticket/PR posting, commits, pushes, and PR creation each require
explicit approval.
