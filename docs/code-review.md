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
/review-orchestrator https://github.com/acme/app/pull/87
/review-orchestrator 87
/review-orchestrator "add rate limiting to the login endpoint"
```

Works on **Gitea** (via `tea`) and **GitHub** (via `gh`) — the forge is detected from the
PR URL or the git remote.

If you pass nothing, it asks once what to review. Outside the repo directory, give the PR
URL (or the command falls back to `--repo <owner>/<repo>`).

## What it does

1. **Gathers context in parallel** — four cheap agents each return a short brief: the
   ticket goal, the implementation (changed files + risky hunks), the repo conventions, and
   the security surface.
2. **Checkpoint** — shows you what it understood and how confident it is, then **stops** so
   you can refine or continue.
3. **Reviews** — two Opus agents review in parallel: one for correctness/quality against
   ticket intent and conventions, one for security. **Both are strictly scoped to the PR
   delta** — unchanged code is context for judging the change, never a review target.
   The one exception: **what the PR fails to do is always in scope** — every acceptance
   criterion is mapped to `covered / partial / MISSING`, and a missing criterion is a
   must-fix that forces request-changes.

   Want a **full-repository audit** instead? Say so (in the request or at the
   checkpoint) — `scope: repo` sweeps the whole codebase through the same lenses.
   It's opt-in because it's noticeably more expensive; the default never widens
   silently.

4. **Verifies line numbers** — a mechanical pass confirms every suggestion lands on the
   right line.
5. **Publishes (optional)** — after you approve, posts inline suggestions to the PR.

## The two stops

The command pauses and waits for you at two points — it never proceeds on its own:

- **After gathering context** — pick refine `(a)` or continue `(b)`.
- **Before publishing** — choose `all` / `must-fix only` / `summary-only` / `no`.

## Output

A single report:

- **Ticket coverage** — first thing: every acceptance criterion marked
  `covered / partial / MISSING / descoped`.
- **Code review** — correctness, conventions, reuse, missing tests, edge cases.
- **Security** — issues the PR introduces, touches, or worsens (plus controls the change
  _should_ have added but didn't).
- **Verdict** — approve / approve-with-nits / request-changes (any must-fix security
  issue or MISSING criterion forces request-changes).

Each finding has a severity (`must-fix` / `recommended` / `cosmetic`) and a paste-ready
`suggestion` block.

## Re-reviews are incremental

Run it again after a new push and it spends tokens only on what changed: it reuses cached
context, reviews just the new commits, tells you which prior findings are now resolved, and
skips reposting comments that already exist. Review state is saved even if you choose not
to publish — and re-running on the same commit replays the cached report instead of
re-reviewing.

## Applying the findings

Findings aren't just comments — they're executable.
[`/implement-orchestrator <index>`](./implement.md#from-a-review-instead-of-a-plan) runs
in **review mode**: it converts the review's findings (anchor + exact suggestion) into a
fix plan and applies your selection with the executor ladder. Push, re-review, and the
fixed threads auto-resolve.

## What's under the hood

The command is a thin orchestrator (**Slowbro**). The actual work is done by agents in
[`agents/`](../agents), each pinned to the cheapest model that fits its job:

| Agent       | Model  | Job                                    |
| ----------- | ------ | -------------------------------------- |
| `Slowpoke`  | Haiku  | Ticket brief                           |
| `Kadabra`   | Sonnet | Implementation brief (what changed)    |
| `Eevee`     | Sonnet | Repository profile (conventions)       |
| `Growlithe` | Sonnet | Security-surface scout                 |
| `Mewtwo`    | Opus   | General reviewer                       |
| `Alakazam`  | Opus   | Security reviewer                      |
| `Porygon`   | Haiku  | Verifies each suggestion's line number |

Forge access goes through the [`tea-cli`](../skills/tea-cli) (Gitea) or
[`gh-cli`](../skills/gh-cli) (GitHub) skill — the orchestrator detects the forge from the
PR URL or the git remote and picks the right one.

## Caching

To keep re-reviews cheap, the agents cache context in the reviewed project's **cache
dir** — auto-detected per harness: `.opencode/cache/` (OpenCode), `.claude/cache/`
(Claude Code), else `.agents/cache/`; an existing cache always wins:

| File                          | Holds                                  | Owner         |
| ----------------------------- | -------------------------------------- | ------------- |
| `repo-profile.md`             | Stack & conventions                    | `Eevee`       |
| `security-profile.md`         | Threat surface                         | `Growlithe`   |
| `impl-brief-<index>-<sha>.md` | What a PR changed (per head commit)    | `Kadabra`     |
| `review-<index>.md`           | Review state for incremental re-review | orchestrator  |
| `learnings.md`                | Cross-ticket repo learnings (shared)   | orchestrators |

These are generated files. The catalog ignores `cache/` itself, and the target project
should ignore the whole `.agents/` directory.

**Location:** resolved automatically by each command (see the "Cache location" section
in the command files) — no configuration needed. The detection prefers an existing
cache, so adding a new harness dir later never forks accumulated state.

## Requirements

- The forge CLI, authenticated: [`tea`](../skills/tea-cli) for Gitea or
  [`gh`](../skills/gh-cli) for GitHub.
- A Jira tool available (for ticket briefs by reference).
- The agents and skill installed where your harness can find them (see
  [AGENTS.md](../AGENTS.md)).
