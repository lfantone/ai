# The workflow

Five phases, one command each, plus `/ship`. Every phase reads its inputs from disk and writes
one artifact, so each can start in a fresh session: the cheapest context is the one you don't
carry.

```text
/investigate ──► /plan ──► /implement ──► /verify ──► /ship ──► /review
                               ▲             │                     │
                               └─ failures ──┴── open findings ◄───┘
```

| Phase       | Command                         | Model           | Writes                                                                             | Stops for you                        |
| ----------- | ------------------------------- | --------------- | ---------------------------------------------------------------------------------- | ------------------------------------ |
| Investigate | `/investigate <key\|url\|text>` | Opus · xhigh    | `ticket.md`: why, what, acceptance criteria, scope, how to drive it                | approve the ticket; publish it       |
| Plan        | `/plan`                         | Opus · high     | `plan.md`: decisions, design, work units, test plan, security surface              | approve the plan                     |
| Implement   | `/implement`                    | Sonnet · medium | code and unit tests; ticks units, logs deviations; parallel `Machop` (Haiku) units | a decision or criterion would change |
| Verify      | `/verify [local\|env URL]`      | session         | `verify.md` + `bruno/`: scenarios, PASS/FAIL per criterion; web via `Ditto`        | environment; scenarios               |
| Ship        | `/ship`                         | session         | commit, push, PR with what, how, and how to test                                   | each outward step                    |
| Review      | `/review [PR] [lenses]`         | session         | `review.md`: `Mewtwo` findings, PR-thread verdicts, `reviewed_sha`                 | publishing, replies, resolutions     |

The loop: verify failures and open review findings (including valid human PR threads) go back
to `/implement`; `/ship` then pushes to the open PR and `/review` re-reviews only the new
delta, replying to and resolving threads on a yes. Merging stays yours.

## Why this shape

The earlier plan → implement → verify orchestrators relayed briefs and exact edit
contracts between 17 agents. Measured on real runs, the orchestrator's own context cost far
more than the workers saved (39.7M vs 0.4M tokens in one planning run), retries dominated
(16 Sonnet retries vs 7 Haiku runs on one ticket), and about half the agents scored no
better than an unguided model in ablation evals. Plain plan mode kept winning because one
model holds the investigation, design, and code together.

So effort goes where the decisions are: investigation and planning get the strongest model,
and a precise plan lets a cheaper one implement. An agent is added only when isolation pays:

- **Fresh perspective:** Mewtwo reviews without the implementer's reasoning in its context.
- **Bulky output:** Ditto keeps browser snapshots out of the main session.
- **Cheaper work:** Machop (Haiku) takes the plan's mechanical units off the Sonnet session,
  in parallel when their files are disjoint.

## State

One folder per repository, outside it and shared by every worktree:
`~/.agents/work/<repo>/<slug>/`, where `<repo>` is the main checkout's path. Every command
resolves it with the same line, so a phase started in another worktree or a fresh session finds
the previous phase's files:

```bash
W=~/.agents/work$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')
```

- `ticket.md`: the investigated ticket; `Status: approved` unlocks `/plan`.
- `plan.md`: the plan; `Status: approved` unlocks `/implement`, which ticks units and logs
  deviations here.
- `verify.md` + `bruno/`: scenarios and dated runs; the API collection reruns with one `bru run`.
- `review.md` + `review.diff`: `reviewed_sha`, findings with status, thread verdicts.

The slug is the Jira key, `gh-<n>`, or a kebab-case title, and each command ends by naming the
next one with it (`/plan IE-123`). Without it, commands read the slug from the branch name, else
take the newest folder, and say which.

No place inside the repo works everywhere: Claude Code blocks worktree sessions from writing to
the main checkout and prompts on every `.git` write, and Codex keeps `.git` and `.agents`
read-only. So allow the folder once in each harness you use:
[Claude Code](./claude-code.md#state-folder) · [OpenCode](./opencode.md#state-folder) ·
[Codex](./codex.md#state-folder) · [Copilot](./copilot.md#state-folder).

Coming from the old per-worktree `.agents/work/`? Run this in each checkout that has one:

```bash
W=~/.agents/work$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')
mkdir -p "$W" && mv .agents/work/* "$W"/ && rmdir .agents/work
```

Coding standards come from each project's own `AGENTS.md` / `CLAUDE.md`. Personal defaults
come from the global instructions block (`instructions/AGENTS.md`).

## Harness setup

Install, model pins, command names, and the state-folder allowance:
[Claude Code](./claude-code.md) · [OpenCode](./opencode.md) · [Codex](./codex.md) ·
[Copilot](./copilot.md).
