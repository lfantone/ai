# Implementation execution (`/implement-orchestrator`)

Executes an approved plan wave by wave. The plan selects the cheapest capable executor per
contract instead of applying one model tier to the whole change.

## Usage

```text
/implement-orchestrator IE-1234
/implement-orchestrator 87        # apply findings from review #87
```

Execution happens on the current branch and starts only after an explicit checkpoint.

## Routing

| Contract                   | Executor         | Behavior                                                             |
| -------------------------- | ---------------- | -------------------------------------------------------------------- |
| `exact`                    | Machop / Haiku   | Validates complete preconditions, applies typed operations exactly   |
| `guided`                   | Machoke / Sonnet | Follows bounded instructions and prior art to reach the target state |
| failed, bounded adaptation | Machamp / Opus   | User-approved last resort                                            |

Guided execution is an expected cost of `--fast` planning, not an escalation. Exact retries,
Machamp, re-specification, and replanning remain user-gated.

## Applicability and safety

The plan header's `head` records provenance but is not the applicability decision. Before its
first edit, each executor validates every current contract precondition against the working
tree. Exact steps compare the complete Before/anchor block, never only its first line. If any
precondition is absent or ambiguous, that contract edits nothing.

This handles committed drift, dirty worktrees, and interrupted runs without a separate
Magneton anchor pass. Magneton is used only to keep the plan structurally consistent after a
contract is re-specified.

## Execution flow

1. Load lifecycle state and skip ticked contracts.
2. Show branch, plan mode, exact/guided counts, waves, files, and repository gates.
3. Run file-disjoint contracts concurrently within each wave, capped at five.
4. Tick each contract only after its own verification succeeds.
5. Run repository tests, lint, typecheck, and build.
6. Save the execution log and lifecycle status.

## Lifecycle statuses

| Status                  | Meaning                                                 |
| ----------------------- | ------------------------------------------------------- |
| `implemented`           | All contracts and repository gates passed               |
| `partially-implemented` | One or more contracts were skipped or unresolved        |
| `implementation-failed` | Contracts completed but a repository gate failed        |
| `verification-failed`   | Runtime QA failed; Verify still owns final adjudication |

`implementation-failed` re-enters gate-remediation mode on the next run. Verify refuses to
grant `verified` until implementation gates pass.

## Review mode

Review findings with exact anchors and suggestion replacements convert into exact contracts,
grouped by file in one parallel wave. Sketch findings must be re-specified by Mew or returned
to planning. Applied findings remain open until a new review confirms and resolves them.

## Failure routing

| Failure                          | Route                                                 |
| -------------------------------- | ----------------------------------------------------- |
| Exact precondition drift         | User-approved Machoke retry                           |
| Locally wrong contract           | Mew exact re-spec → Magneton structure check → Machop |
| Guided instructions insufficient | Precise re-spec or full planning                      |
| Bounded judgment required        | User-approved Machamp                                 |
| Design/scope/dependency gap      | Plan revision                                         |

The plan checklist and Execution log make interrupted runs resumable. Commit, push, and PR
creation remain separately gated.
