---
description: Review the change — repo standards, security, plan deviations, PR threads. Stored; postable.
argument-hint: "[PR url | index] [lenses…]"
---

$ARGUMENTS: an optional PR, then extra lenses (e.g. performance, accessibility).

1. **Target** — the given PR, else the branch's PR (forge skill), else the local change. For a
   PR, HEAD must equal its head SHA; otherwise stop and offer to check the PR out.
2. **State** — work dir `<work root>/<slug>/`, with the work root:

   ```bash
   W=~/.agents/work$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')
   ```

   Slug: the one in the branch name, else `pr-<index>` for a PR, or the newest folder in the
   work root. If a PR's head equals `reviewed_sha` in its `review.md`, show the stored
   findings; skip to step 5.

3. **Diff** — write it to the work dir's `review.diff`, never into context. PR:
   `git diff <reviewed_sha>..HEAD` when that is an ancestor, else the PR's diff via the
   forge skill. Local: `git diff $(git merge-base origin/HEAD HEAD)` plus
   `git diff --no-index /dev/null <file>` per untracked file.
4. **Review** — spawn `Mewtwo` with the diff path, the work dir (lacking `ticket.md` /
   `plan.md`: the criteria and security surface from `ticket-context` or the PR
   description), the guidance files (root `REVIEW.md`; per touched path, the nearest
   `AGENTS.md` and matching `.github/instructions/*.instructions.md`), the lenses, and
   prior findings. Present its output as-is, then a verdict:
   approve / approve-with-nits / request-changes (any must-fix or MISSING forces it).
5. **Threads** (PR only) — fetch unresolved threads via the forge skill; judge each one not
   in `review.md`, or with newer comments from others, against the code at head. A moved
   line never means addressed. Verdicts: `valid` (a finding block like Mewtwo's) ·
   `addressed` (evidence: file:line or sha) · `disagree` (grounded in code, conventions, or
   the ticket — never taste) · `question` (an answer). Draft a short reply for each; for
   `disagree`, acknowledge the concern first.
6. **Save** — `review.md`: `reviewed_sha`, the PR, each judged thread (verdict, last comment
   id), and per finding its block verbatim, id, source, status, and comment or thread id.
   Status: `open`, `fixed`, `resolved`, `wontfix`; Mewtwo's `still-outstanding` /
   `partially-addressed` reopen it. The user may flip verdicts or mark findings
   `wontfix`.
7. **Publish — HARD STOP** (PR only) — ask: all / must-fix only / summary-only / no. Post
   findings without a comment id as one review with the forge skill's inline-suggestion
   payload, `commit_id` = head; those it can't anchor inline go in the summary body. Show
   every thread reply verbatim, plus "fixed in `<sha>`" for threads whose finding is now
   `resolved`, and post on yes. Resolve, on yes, those threads and human threads judged
   `addressed`. Never resolve `disagree` or `question` threads.

Open findings → `/implement <slug>` in a fresh session, `/ship`, then `/review` again.
