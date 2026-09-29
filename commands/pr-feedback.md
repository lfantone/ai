---
description: Work a PR's unresolved review comments — judge each against the code at head, fix the valid ones, draft replies; nothing posted without a yes.
argument-hint: "<PR url | index>"
---

PR: $ARGUMENTS — ask once if empty. Resolve forge and coordinates as `/pr-review` does; HEAD
must equal the PR head.

1. **Fetch** unresolved threads with their full comment chains via the forge skill (github:
   GraphQL `reviewThreads` with `isResolved` false; gitea: review comments with
   `resolver == null`). None → say so and stop. Threads listed in
   `.agents/work/pr-<index>/review.md` are ours.
2. **Judge** each thread: one line on what the reviewer means, then check that concern
   against the code at head.
   - A moved or rewritten line never means addressed; re-locate the concern first.
   - Verdicts: `valid` (severity + fix) · `addressed` (positive evidence: file:line or sha) ·
     `disagree` (grounded in code, conventions, or the ticket — never taste) · `question`
     (draft answer) · `owner-decision` (the decision and its options).
   - Draft a reply for each: specific and short, no filler; for `disagree`, acknowledge the
     concern before the rationale.
3. **Checkpoint — HARD STOP** — table: thread, path:line, author, verdict, one-line
   rationale, proposed action. The user may flip any verdict.
4. **Fix** the approved `valid` threads in this session (fan out as in `/ticket` when large),
   run the project's gates, then offer a Conventional Commit and the push — each on yes.
5. **Reply and resolve — HARD STOP** — show every reply verbatim and the threads to resolve;
   post on yes (partial approval is fine). Resolve only `addressed` threads and `valid` ones
   whose fix is pushed. Never resolve `disagree`, `question`, `owner-decision`, or unpushed
   fixes; leave our own threads to `/pr-review`'s re-review.

Then suggest `/pr-review <index>` for the incremental pass.
