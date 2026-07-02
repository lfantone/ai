# Code review (`/review-orchestrator`)

An orchestrated, context-rich review for a PR and/or ticket. Cheap agents gather context
in parallel, heavyweight agents do the reviewing, and you get paste-ready
`suggestion` blocks — without one model reading everything into a single bloated context.

## Usage

```
/review-orchestrator [ticket id/description] [PR url or index]
```

Examples:

```
/review-orchestrator IE-1234 https://gitea.example.com/acme/app/pulls/87
/review-orchestrator 87
/review-orchestrator "add rate limiting to the login endpoint"
```

If you pass nothing, it asks once what to review. Outside the repo directory, give the PR
URL (or the command falls back to `--repo <owner>/<repo>`).

## What it does

1. **Gathers context in parallel** — four cheap agents each return a short brief: the
   ticket goal, the implementation (changed files + risky hunks), the repo conventions, and
   the security surface.
2. **Checkpoint** — shows you what it understood and how confident it is, then **stops** so
   you can refine or continue.
3. **Reviews** — two Opus agents review in parallel: one for correctness/quality against
   ticket intent and conventions, one for security on the diff.
4. **Verifies line numbers** — a mechanical pass confirms every suggestion lands on the
   right line.
5. **Publishes (optional)** — after you approve, posts inline suggestions to the PR.

## The two stops

The command pauses and waits for you at two points — it never proceeds on its own:

- **After gathering context** — pick refine `(a)` or continue `(b)`.
- **Before publishing** — choose `all` / `must-fix only` / `summary-only` / `no`.

## Output

A single report:

- **Code review** — correctness, conventions, reuse, missing tests, edge cases.
- **Security** — issues the PR introduces, touches, or worsens.
- **Verdict** — approve / approve-with-nits / request-changes (any must-fix security issue
  forces request-changes).

Each finding has a severity (`must-fix` / `recommended` / `cosmetic`) and a paste-ready
`suggestion` block.

## Re-reviews are incremental

Run it again after a new push and it spends tokens only on what changed: it reuses cached
context, reviews just the new commits, tells you which prior findings are now resolved, and
skips reposting comments that already exist.

## What's under the hood

The command is a thin orchestrator (**Slowking**). The actual work is done by agents in
[`agents/`](../agents), each pinned to the cheapest model that fits its job:

| Agent       | Model  | Job                                    |
| ----------- | ------ | -------------------------------------- |
| `slowpoke`  | Haiku  | Ticket brief                           |
| `kadabra`   | Sonnet | Implementation brief (what changed)    |
| `espeon`    | Sonnet | Repository profile (conventions)       |
| `growlithe` | Sonnet | Security-surface scout                 |
| `mewtwo`    | Opus   | General reviewer                       |
| `alakazam`  | Opus   | Security reviewer                      |
| `porygon`   | Haiku  | Verifies each suggestion's line number |

Gitea access goes through the [`tea-cli`](../skills/tea-cli) skill.

## Caching

To keep re-reviews cheap, the agents cache context in `.agents/cache/` — i.e. inside the
deployed catalog at the root of the **project being reviewed** (see the README's
Installation section):

| File                          | Holds                                  | Owner        |
| ----------------------------- | -------------------------------------- | ------------ |
| `repo-profile.md`             | Stack & conventions                    | `espeon`     |
| `security-profile.md`         | Threat surface                         | `growlithe`  |
| `impl-brief-<index>-<sha>.md` | What a PR changed (per head commit)    | `kadabra`    |
| `review-<index>.md`           | Review state for incremental re-review | orchestrator |

These are generated files. The catalog ignores `cache/` itself, and the target project
should ignore the whole `.agents/` directory.

**Changing the location:** `.agents/cache/` is just the default path the command and
agents use. To store caches elsewhere, replace `.agents/cache/` in
[`commands/review-orchestrator.md`](../commands/review-orchestrator.md) and the agents that
reference it (`espeon`, `growlithe`, `kadabra`) with your preferred folder.

## Requirements

- The [`tea`](../skills/tea-cli) CLI, configured for your Gitea server.
- A Jira tool available (for ticket briefs by reference).
- The agents and skill installed where your harness can find them (see
  [AGENTS.md](../AGENTS.md)).
