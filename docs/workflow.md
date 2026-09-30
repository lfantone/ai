# The workflow

One session does the work. Commands are the prompts you would otherwise retype; the few
agents exist only where a separate context pays for itself.

```text
/ticket ──► /verify ──► /ship ──► /pr-review ⇄ /pr-feedback ──► merge ──► /verify <env>
```

| Step                          | Command                    | What happens                                                                                                                                               |
| ----------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1–3 Ticket, investigate, plan | `/ticket <key\|url\|text>` | Brief via `ticket-context`, read-only investigation, dependencies and security surface raised, options when contested, plan saved — **stops for approval** |
| 4–5 Implement, unit tests     | (same session)             | Mirrors prior art, unit tests always, project gates; optional parallel `Machop`/`Machoke` workers for 3+ file-disjoint chunks                              |
| 5 Manual / integration checks | `/verify local`            | Scenarios from the ACs; API via `bruno-cli`, web via `Ditto`; PASS/FAIL per AC                                                                             |
| 6 Commit and PR               | `/ship`                    | Branch, Conventional Commit, push, PR linked to the ticket — each step confirmed                                                                           |
| 7 Review                      | `/pr-review [PR]`          | `Mewtwo` in a fresh context: coverage, correctness, security; incremental on reruns; publishing confirmed                                                  |
| 8–9 Iterate                   | `/pr-feedback <PR>`        | Judge each unresolved thread at head, fix valid ones, draft replies; replies and resolutions confirmed                                                     |
| 10 Merge                      | —                          | Yours                                                                                                                                                      |
| 11 Verify in an environment   | `/verify <env URL>`        | Same scenarios against a shared environment; non-mutating unless allowed                                                                                   |

## Why this shape

The earlier plan → implement → verify orchestrators relayed briefs and exact edit
contracts between 17 agents. Measured on real runs, the orchestrator's own context cost far
more than the workers saved (39.7M vs 0.4M tokens in one planning run), retries dominated
(16 Sonnet retries vs 7 Haiku runs on one ticket), and about half the agents scored no
better than an unguided model in ablation evals. Plain plan mode kept winning because one
model holds the investigation, design, and code together.

So an agent is added only when isolation pays:

- **Fresh perspective:** Mewtwo reviews without the implementer's reasoning in its context.
- **Bulky output:** Ditto keeps browser snapshots out of the main session.
- **Parallel work:** Machop (Haiku) and Machoke (Sonnet) take file-disjoint chunks.

## State

Per project, in `.agents/work/` (added to `.git/info/exclude`):

- `<slug>/plan.md`: brief, approved plan, AC ticks, verification log.
- `<slug>/bruno/`: the API scenarios as a re-runnable Bruno collection.
- `pr-<index>/review.md`: `reviewed_sha` and findings, which drive incremental re-review.

Coding standards come from each project's own `AGENTS.md` / `CLAUDE.md`. Personal defaults
come from the global instructions block (`instructions/AGENTS.md`).
