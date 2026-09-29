---
description: Review a PR, or the local diff, for correctness, ticket coverage, and security — incremental on reruns; publishing is confirmed.
argument-hint: "[PR url | index] [ticket]"
---

Target: $ARGUMENTS. Empty → review the local diff against the base branch (self-review
before `/ship`).

1. **Coordinates** — forge from the PR URL host or `git remote get-url origin` (github.com →
   github, else gitea); owner, repo, index, and head SHA via the forge skill. For a PR, HEAD
   must equal its head SHA; otherwise stop and offer `gh pr checkout <index>` /
   `tea pr checkout <index>`.
2. **Criteria** — the plan's ACs (`.agents/work/<slug>/plan.md`), else the ticket via
   `ticket-context`, else the PR description.
3. **State** — `.agents/work/pr-<index>/review.md`: `reviewed_sha` differs from head →
   re-review; equals head → show the stored report and offer only publishing.
4. **Review** — spawn `Mewtwo` with forge, owner/repo, index (or base branch), the criteria,
   and on re-review `reviewed_sha` plus prior findings. Present its output as-is, then a
   verdict: approve / approve-with-nits / request-changes (any must-fix or MISSING forces
   request-changes). On re-review group findings as Resolved, Still outstanding, New.
5. **Save** — write `review.md`: `reviewed_sha`, and per finding its id, severity, file,
   anchor text, status, and comment id once posted.
6. **Publish — HARD STOP** — ask: all / must-fix only / summary-only / no. Post one review
   with the forge skill's inline-suggestion payload, `commit_id` = head. Findings without an
   inline anchor, and multi-line fixes on gitea, go in the summary body. On re-review, offer
   to resolve our own threads whose findings are now resolved — never human threads.
