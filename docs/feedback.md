# Feedback (`/feedback-orchestrator`)

Works a PR's unresolved review comments end to end: fetch every open thread, judge each
comment's **underlying concern** against the code at head, build an action plan, apply
the straightforward fixes inline, and reply to / resolve threads — every outward word
gated on your approval. The inbound counterpart to
[`/review-orchestrator`](./code-review.md).

## Usage

```
/feedback-orchestrator https://github.com/acme/app/pull/87
/feedback-orchestrator 87
```

Works on GitHub and Gitea (forge auto-detected). Re-running resumes: threads already
replied/resolved/fixed are skipped.

## What it does

1. **Harvests** every unresolved thread (full comment chains) plus the implementation
   brief — threads posted by our own review flow are tagged `ours` and left to its
   re-review machinery by default.
2. **Judges** each thread (Hypno): first _what the reviewer actually means_, then the
   concern verified against head. **A changed line never auto-invalidates a concern** —
   `addressed` requires positive evidence, not drift.
3. **Checkpoint** — the triage table with per-thread verdicts and recommendations; you
   override anything, and split `valid` fixes into _inline now_ vs _defer_.
4. **Applies** the selected inline fixes: anchors verified, one exact contract per fix,
   executed by the Haiku executor (Sonnet retry gated), repo gates run, commit + push
   each individually gated.
5. **Replies & resolves** — drafts shown verbatim, then posted on your yes; resolution
   follows hard etiquette rules.

## Verdicts

| Verdict          | Meaning                             | Action                                             |
| ---------------- | ----------------------------------- | -------------------------------------------------- |
| `valid`          | Concern holds against head          | Step-shaped fix → inline or deferred to implement  |
| `addressed`      | Concern satisfied — with evidence   | Evidence reply + resolve                           |
| `disagree`       | Concern doesn't hold — grounded why | Respectful reply — **never resolved by the agent** |
| `question`       | Needs an answer, not a change       | Drafted answer — left open                         |
| `owner-decision` | A product/design call               | Surfaced to you; your answer becomes the reply     |

## Resolution etiquette (hard rules)

- Resolve only what's demonstrably done: `addressed` with evidence, or `valid` whose fix
  is applied **and pushed**.
- Never resolve a `disagree` — the commenter (or you, manually) closes it. An agent
  closing a human's objection is how trust dies.
- Deferred fixes leave their threads open, with a reply saying what's planned.

## Where fixes go

- **Inline** (single file, exact anchor + replacement, zero design decisions) — applied
  by this command.
- **Deferred** — appended to the review cache as open findings, so
  [`/implement-orchestrator <index>`](./implement.md) review mode executes them; design-
  level concerns route to [`/plan-orchestrator`](./plan.md).

## What's under the hood

| Agent              | Model        | Job                                               |
| ------------------ | ------------ | ------------------------------------------------- |
| `Kadabra`          | Sonnet       | Threads mode — unresolved threads + impl brief    |
| `Eevee`            | Sonnet       | Repo profile _(cached; only when stale)_          |
| `Slowpoke`         | Haiku        | Ticket brief _(only when a ticket is referenced)_ |
| `Hypno`            | Opus         | The judge — verdicts + draft replies              |
| `Machop`/`Machoke` | Haiku/Sonnet | Execute inline fixes as exact contracts           |

State lives in `$CACHE/feedback-<index>.md` (per-thread verdict/status/reply id). Before an
inline edit, the orchestrator reads the selected target lines from the current head and defers
any fix whose target text no longer matches.

## Requirements

- The forge CLI, authenticated: [`tea`](../skills/tea-cli) (Gitea) or
  [`gh`](../skills/gh-cli) (GitHub).
- The PR checked out locally (the command verifies HEAD and asks otherwise).
